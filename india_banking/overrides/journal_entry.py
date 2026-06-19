import frappe
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_accounting_dimensions,
)
from frappe import _
from frappe.query_builder import DocType
from frappe.query_builder.functions import Sum
from frappe.utils import get_url_to_form


@frappe.whitelist()
def make_payment_order(source_name, target_doc=None, args=None):
	from frappe.model.mapper import get_mapped_doc

	def validate_party_bank_account(bank_entry=None):
		if not bank_entry:
			return

		JournalEntryAccount = DocType("Journal Entry Account")
		BankAccount = DocType("Bank Account")

		invalid_parties = (
			frappe.qb.from_(JournalEntryAccount)
			.left_join(BankAccount)
			.on(
				(JournalEntryAccount.party == BankAccount.party)
				& (JournalEntryAccount.party_type == BankAccount.party_type)
				& (BankAccount.disabled == 0)
				& (BankAccount.is_default == 1)
			)
			.select(
				JournalEntryAccount.party_type,
				JournalEntryAccount.party,
			)
			.where(
				(JournalEntryAccount.parent == bank_entry)
				& (
					JournalEntryAccount.payment_status.notin(
						["Paid", "Ordered", "Payment Ordered"]
					)
				)
				& BankAccount.name.isnull()
			)
			.groupby(JournalEntryAccount.party_type, JournalEntryAccount.party)
		).run(as_dict=1)

		if not invalid_parties:
			return

		# Determine which of those parties have any bank account
		party_names = [p.party for p in invalid_parties]
		parties_with_some_account = {
			(r.party_type, r.party)
			for r in (
				frappe.qb.from_(BankAccount)
				.select(BankAccount.party_type, BankAccount.party)
				.where(BankAccount.party.isin(party_names))
				.groupby(BankAccount.party_type, BankAccount.party)
			).run(as_dict=1)
		}

		msg = ""
		for p in invalid_parties:
			party_type = p.get("party_type")
			party = p.get("party")
			if not party_type or not party:
				continue
			if (party_type, party) in parties_with_some_account:
				msg += f"<b>{party_type}-{party}</b> has no default bank account.<br>"
			else:
				msg += f"<b>{party_type}-{party}</b> does not have a bank account.<br>"

		if msg:
			frappe.msgprint(
				_(
					"We can see Some bank entries are missing bank account details and have been ignored. Please update the bank account information and try again.</br></br><p style='color:red'><b>Missing Details are below</b></p>"
					+ msg
				),
				title=_("Missing Bank Account"),
				indicator="orange",
			)

	def update_bank_entry(source, target):
		JournalEntryAccount = DocType("Journal Entry Account")
		BankAccount = DocType("Bank Account")

		select_field = [
			"name",
			"account",
			"cost_center",
			"project",
			"debit as amount",
			"party",
			"party_type",
			"parent as journal",
		]
		select_field.extend(get_accounting_dimensions())

		# Validate party does NOT have a valid Bank Account
		validate_party_bank_account(source.name)

		# Build the query
		query = (
			frappe.qb.from_(JournalEntryAccount)
			.join(BankAccount)
			.on(JournalEntryAccount.party == BankAccount.party)
			.select(
				*[
					getattr(JournalEntryAccount, field.split(" as ")[0]).as_(
						field.split(" as ")[1]
					)
					if " as " in field
					else getattr(JournalEntryAccount, field)
					for field in select_field
				],
				BankAccount.name.as_("party_bank_account"),
			)
			.where(
				(JournalEntryAccount.parent == source.name)
				& (
					JournalEntryAccount.payment_status.notin(
						["Paid", "Ordered", "Payment Ordered"]
					)
				)
				& (BankAccount.disabled == 0)
				& (BankAccount.is_default == 1)
			)
			.groupby(JournalEntryAccount.name)
		)

		journal_accounts = query.run(as_dict=True)

		target.payment_order_type = "Journal Entry"
		target.docstatus = 0
		target.status = "Pending"

		def _update_dimensions(source):
			return {
				dimension: source.get(dimension, "")
				for dimension in get_accounting_dimensions()
			}

		for journal_account in journal_accounts:
			bank_account = frappe.get_doc(
				"Bank Account", journal_account.party_bank_account
			)
			if frappe.db.get_single_value(
				"India Banking Settings", "activate_workflow_on_bank_account"
			):
				if bank_account.workflow_state != "Approved":
					frappe.throw(
						title=_("Cannot proceed with un-approved bank account"),
						msg=_(
							"{}-{}- Bank Account <a href='{}'>{}</a>".format(
								journal_account.party_type,
								journal_account.party,
								get_url_to_form(
									"Bank Account", journal_account.party_bank_account
								),
								frappe.bold(journal_account.party_bank_account),
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
								"Bank Account", journal_account.party_bank_account
							),
							frappe.bold(journal_account.party_bank_account),
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
				"bank_account": journal_account.party_bank_account,
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
