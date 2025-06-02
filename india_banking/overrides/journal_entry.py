import frappe
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_accounting_dimensions,
)
from frappe import _
from frappe.query_builder import Case, DocType
from frappe.query_builder.functions import Sum
from frappe.utils import get_url_to_form
from pypika.terms import ExistsCriterion


@frappe.whitelist()
def make_payment_order(source_name, target_doc=None, args=None):
	from frappe.model.mapper import get_mapped_doc

	def validate_party_bank_account(journal=None, party_type=None, party=None):
		if not journal:
			return

		JournalEntryAccount = DocType("Journal Entry Account")
		BankAccount = DocType("Bank Account")

		bank_account_query = (
			frappe.qb.from_(JournalEntryAccount)
			.left_join(BankAccount)
			.on(JournalEntryAccount.party == BankAccount.party)
			.select(
				JournalEntryAccount.party_type,
				JournalEntryAccount.party,
				BankAccount.name.as_("bank_account"),
			)
			.where(
				(JournalEntryAccount.parent.eq(journal))
				& (JournalEntryAccount.party_type.eq(party_type))
				& (BankAccount.party.eq(party))
				& (
					(BankAccount.name.isnull())
					| (BankAccount.disabled.eq(1))
					| (BankAccount.is_default.eq(0))
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
				if not party_details.get("bank_account"):
					msg += (
						f"<b>{party_type}-{party}</b> does not have a bank account.<br>"
					)
				else:
					msg += (
						f"<b>{party_type}-{party}</b> has no default bank account.<br>"
					)
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
		JournalEntry = DocType("Journal Entry")
		JournalEntryAccount = DocType("Journal Entry Account")

		query = (
			frappe.qb.from_(JournalEntry)
			.join(JournalEntryAccount)
			.on(JournalEntry.name == JournalEntryAccount.parent)
			.select(
				JournalEntryAccount.name,
				JournalEntry.name.as_("journal"),
				JournalEntryAccount.party,
				JournalEntryAccount.party_type,
				JournalEntryAccount.account,
				JournalEntryAccount.cost_center,
				JournalEntryAccount.project,
				Sum(
					Case()
					.when(
						JournalEntryAccount.party.isnotnull(),
						JournalEntryAccount.credit,
					)
					.else_(0)
				).as_("credit_with_party"),
				Sum(
					Case()
					.when(
						JournalEntryAccount.party.isnotnull(), JournalEntryAccount.debit
					)
					.else_(0)
				).as_("debit_with_party"),
			)
			.where(
				(JournalEntry.docstatus == 1)
				& (JournalEntry.voucher_type.eq("Bank Entry"))
				& (
					JournalEntryAccount.account != target.account
				)  # Exclude company account rows
				& (JournalEntry.name == source_name)
			)
			.groupby(
				JournalEntryAccount.parent,
				JournalEntryAccount.party,
				JournalEntryAccount.account,
			)
			.orderby(JournalEntryAccount.idx)
		)

		data = query.run(as_dict=True)

		ordered_bank_entries = frappe.get_all(
			"Payment Order Reference",
			filters={
				"docstatus": ["in", [0, 1]],
				"reference_doctype": "Journal Entry",
				"parent": ["!=", target.name],
			},
			fields=["reference_doctype", "reference_name", "journal_entry_account"],
			order_by="idx",
			as_list=True,
		)

		new_data = []
		for entry in data:
			if (
				"Journal Entry",
				entry.journal,
				entry.name,
			) in ordered_bank_entries:
				continue

			entry["amount"] = entry["debit_with_party"] - entry["credit_with_party"]
			if entry["amount"] > 0:
				validate_party_bank_account(
					journal=entry.journal,
					party_type=entry.party_type,
					party=entry.party,
				)
				entry["party_bank_account"] = frappe.get_value(
					"Bank Account",
					{
						"party_type": entry.party_type,
						"party": entry.party,
						"is_default": 1,
						"disabled": 0,
					},
					"name",
				)
				if entry["party_bank_account"]:
					new_data.append(entry)

		journal_accounts = new_data

		target.payment_order_type = "Journal Entry"
		target.docstaus = 0
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
		.select(
			JournalEntryAccount.name.as_("journal_entry_account"),
			JournalEntry.company,
			Sum(JournalEntryAccount.debit).as_("total"),
			JournalEntry.voucher_type,
			JournalEntry.name,
			JournalEntryAccount.party,
			JournalEntryAccount.party_type,
			Sum(
				Case()
				.when(JournalEntryAccount.party.isnotnull(), JournalEntryAccount.credit)
				.else_(0)
			).as_("credit_with_party"),
			Sum(
				Case()
				.when(JournalEntryAccount.party.isnotnull(), JournalEntryAccount.debit)
				.else_(0)
			).as_("debit_with_party"),
		)
		.where(
			(JournalEntry.docstatus == 1)
			& (JournalEntry.voucher_type.eq("Bank Entry"))
			& (
				ExistsCriterion(
					frappe.qb.from_(JournalEntryAccount)
					.select("name")
					.where(
						(JournalEntryAccount.parent == JournalEntry.name)
						& (JournalEntryAccount.account == filters.company_account)
					)
				)
			)
			& (JournalEntryAccount.account != filters.company_account)
		)
		.groupby(
			JournalEntryAccount.parent,
			JournalEntryAccount.party,
			JournalEntryAccount.account,
		)
	)

	if searchfield:
		if searchfield == "name":
			query = query.where(JournalEntry.name.like(f"%{txt}%"))

	data = query.run(as_dict=as_dict)

	ordered_bank_entries = frappe.get_all(
		"Payment Order Reference",
		filters={
			"docstatus": ["in", [0, 1]],
			"reference_doctype": "Journal Entry",
			"parent": ["!=", filters.get("payment_order", "")],
		},
		fields=["reference_doctype", "reference_name", "journal_entry_account"],
		order_by="idx",
		as_list=True,
	)

	new_data = {}
	for entry in data:
		if (
			"Journal Entry",
			entry.name,
			entry.journal_entry_account,
		) not in ordered_bank_entries and (entry.name not in filters.docs):
			if entry.debit_with_party - entry.credit_with_party <= 0:
				continue

			if entry.name in new_data:
				new_data[entry.name]["total"] += (
					entry.debit_with_party - entry.credit_with_party
				)
			else:
				new_data[entry.name] = entry
				new_data[entry.name]["total"] = (
					entry.debit_with_party - entry.credit_with_party
				)

	return [values for entry, values in new_data.items() if values["total"] > 0]
