import frappe
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_accounting_dimensions,
)
from frappe import _
from frappe.query_builder import DocType
from frappe.query_builder.functions import Coalesce, Sum
from frappe.utils import get_url_to_form


@frappe.whitelist()
def make_payment_order(source_name, target_doc=None, args=None):
	from frappe.model.mapper import get_mapped_doc

	def validate_party_bank_account(bank_entry=None):
		if not bank_entry:
			return

		JournalEntryAccount = DocType("Journal Entry Account")

		bank_account_query = (
			frappe.qb.from_(JournalEntryAccount)
			.select(JournalEntryAccount.party_type, JournalEntryAccount.party)
			.where(
				(JournalEntryAccount.parent == bank_entry)
				& (Coalesce(JournalEntryAccount.bank_account, "").eq(""))
				& (Coalesce(JournalEntryAccount.party_type, "").ne(""))
				& (Coalesce(JournalEntryAccount.party, "").ne(""))
				& (
					JournalEntryAccount.payment_status.notin(
						["Paid", "Ordered", "Payment Ordered"]
					)
				)
			)
			.groupby(JournalEntryAccount.party)
		)

		non_bank_account_party = bank_account_query.run(as_dict=1)

		msg = ""
		for party_details in non_bank_account_party:
			if (
				party_details
				and (party_type := party_details.get("party_type"))
				and (party := party_details.get("party"))
			):
				msg += f"<b>{party_type}-{party}</b> does not have a bank account.<br>"

		if msg:
			frappe.msgprint(
				_(
					"Some bank entries are missing bank account details and have been excluded from processing. Please update the bank account information and try again.</br></br><p style='color:red'><b>Missing Details are below</b></p>"
					+ msg
				),
				title=_("Missing Bank Account"),
				indicator="orange",
			)

	def update_bank_entry(source, target):
		JournalEntryAccount = DocType("Journal Entry Account")

		select_field = [
			"name",
			"account",
			"cost_center",
			"project",
			"debit as amount",
			"party",
			"party_type",
			"parent as journal",
			"bank_account",
		]
		select_field.extend(get_accounting_dimensions())

		# Validate party does NOT have a valid Bank Account
		validate_party_bank_account(source.name)

		# Build the query
		query = (
			frappe.qb.from_(JournalEntryAccount)
			.select(
				*[
					(
						getattr(JournalEntryAccount, field.split(" as ")[0]).as_(
							field.split(" as ")[1]
						)
						if " as " in field
						else getattr(JournalEntryAccount, field)
					)
					for field in select_field
				],
			)
			.where(
				(JournalEntryAccount.parent == source.name)
				& (Coalesce(JournalEntryAccount.bank_account, "").ne(""))
				& (Coalesce(JournalEntryAccount.party_type, "").ne(""))
				& (Coalesce(JournalEntryAccount.party, "").ne(""))
				& (JournalEntryAccount.debit > 0)
				& (
					JournalEntryAccount.payment_status.notin(
						["Paid", "Ordered", "Payment Ordered"]
					)
				)
			)
			.groupby(JournalEntryAccount.name)
		)

		journal_accounts = query.run(as_dict=True)

		target.payment_order_type = "Journal Entry"
		target.docstaus = 0
		target.status = "Pending"

		def _update_dimensions(source):
			return {
				dimension: source.get(dimension, "")
				for dimension in get_accounting_dimensions()
			}

		for journal_account in journal_accounts:
			bank_account = frappe.get_doc("Bank Account", journal_account.bank_account)
			if frappe.db.get_single_value(
				"India Banking Settings", "enable_bank_account_workflow"
			):
				if bank_account.workflow_state != "Approved":
					frappe.throw(
						title=_("Cannot proceed with un-approved bank account"),
						msg=_(
							"{}-{}- Bank Account <a href='{}'>{}</a>".format(
								journal_account.party_type,
								journal_account.party,
								get_url_to_form(
									"Bank Account", journal_account.bank_account
								),
								frappe.bold(journal_account.bank_account),
							)
						),
					)

			if bank_account.currency != "INR":
				frappe.throw(
					title=_("The party bank account currency should be in INR."),
					msg=_(
						"{}-{}- Bank Account <a href='{}'>{}</a>".format(
							journal_account.party_type,
							journal_account.party,
							get_url_to_form(
								"Bank Account", journal_account.bank_account
							),
							frappe.bold(journal_account.bank_account),
						)
					),
				)

			journal_account = frappe._dict(journal_account)
			details = {
				"reference_doctype": "Journal Entry",
				"reference_name": journal_account.journal,
				"journal_entry_account": journal_account.name,
				"amount": journal_account.amount,
				"party_type": journal_account.party_type,
				"party": journal_account.party,
				"mode_of_payment": "",
				"bank_account": journal_account.bank_account,
				"account": journal_account.account,
				"project": journal_account.project,
				"cost_center": journal_account.cost_center,
			}
			details.update(_update_dimensions(journal_account))

			target.append("references", details)

	doclist = get_mapped_doc(
		"Journal Entry",
		source_name,
		{
			"Journal Entry": {
				"doctype": "Payment Order",
			}
		},
		target_doc,
		update_bank_entry,
	)

	return doclist


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_bank_entry(doctype, txt, searchfield, start, page_len, filters, as_dict):
	filters = frappe._dict(filters)
	JournalEntry = DocType("Journal Entry")
	JournalEntryAccount = DocType("Journal Entry Account")

	query = (
		frappe.qb.from_(JournalEntry)
		.join(JournalEntryAccount)
		.on(JournalEntry.name == JournalEntryAccount.parent)
		.where(
			(JournalEntry.docstatus == 1)
			& (
				JournalEntryAccount.payment_status.notin(
					["Paid", "Ordered", "Payment Ordered"]
				)
			)
			& (JournalEntry.voucher_type == "Bank Entry")
			& (JournalEntryAccount.against_account == filters.company_account)
		)
		.groupby(JournalEntry.name, JournalEntry.company, JournalEntry.voucher_type)
		.select(
			JournalEntry.name,
			JournalEntry.company,
			Sum(JournalEntryAccount.debit).as_("total"),
			JournalEntry.voucher_type,
		)
	)

	if filters:
		if filters.docs:
			existing_entries = tuple(filters.docs or [])
			query = query.where(JournalEntry.name.notin(existing_entries))
		if filters.company:
			query = query.where(JournalEntry.company == filters.company)

	if txt:
		query = query.where(JournalEntry.name.like(f"%{txt}%"))

	bank_entries = query.run(as_dict=as_dict)

	return bank_entries


def update_party_bank(self, method):
	if self.voucher_type != "Bank Entry":
		return

	for row in self.accounts:
		if row.party_type and row.party and not row.bank_account:
			account_type = frappe.get_cached_value(
				"Account", row.account, "account_type"
			)

			if account_type in ["Receivable", "Payable"]:
				bank_account = frappe.db.get_value(
					"Bank Account",
					{"party_type": row.party_type, "party": row.party},
					order_by="is_default desc, modified desc",
				)
				if bank_account:
					row.bank_account = bank_account
