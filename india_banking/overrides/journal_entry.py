import frappe
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_accounting_dimensions,
)
from frappe.query_builder import DocType
from frappe.query_builder.functions import Sum


@frappe.whitelist()
def make_payment_order(source_name, target_doc=None, args=None):
	from frappe.model.mapper import get_mapped_doc

	def update_bank_entry(source, target):
		JournalEntryAccount = DocType("Journal Entry Account")
		BankAccount = DocType("Bank Account")

		select_field = [
			"name",
			"account",
			"cost_center",
			"project",
			"debit as amount",
			"party as employee",
			"party_type",
			"parent as journal",
		]
		select_field.extend(get_accounting_dimensions())

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
				& (JournalEntryAccount.party_type == "Employee")
				& (JournalEntryAccount.payment_status.notin(["Paid", "Ordered"]))
				& (BankAccount.disabled == 0)
				& (BankAccount.is_default == 1)
			)
		)

		journal_accounts = query.run(as_dict=True, debug=1)

		target.payment_order_type = "Journal Entry"
		target.docstaus = 0
		target.status = "Pending"

		def _update_dimensions(source):
			return {
				dimension: source.get(dimension, "")
				for dimension in get_accounting_dimensions()
			}

		for journal_account in journal_accounts:
			journal_account = frappe._dict(journal_account)
			details = {
				"reference_doctype": "Journal Entry",
				"reference_name": journal_account.journal,
				"journal_entry_account": journal_account.name,
				"amount": journal_account.amount,
				"party_type": "Employee",
				"party": journal_account.employee,
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
			& (JournalEntryAccount.payment_status.notin(["Paid", "Ordered"]))
			& (JournalEntry.voucher_type == "Bank Entry")
			& (JournalEntryAccount.party_type == "Employee")
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
