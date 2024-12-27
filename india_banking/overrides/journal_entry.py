import frappe
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_accounting_dimensions,
)
from frappe.query_builder import DocType
from frappe.utils import comma_sep


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

		journal_accounts = query.run(as_dict=True)

		target.payment_order_type = "Journal Entry"
		target.docstaus = 0
		target.status = "Pending"

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
			}
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
	search_condition = ""
	if filters and filters.get("docs"):
		filters.get("docs").append("")
		exist_account = str(tuple(filters.get("docs")))
		search_condition += f" AND je.name NOT IN {exist_account} "

	if filters and filters.get("company"):
		search_condition += f"AND je.company = '{filters.get('company')}'"
	if txt:
		search_condition += f"AND je.name LIKE '%{txt}%'"

	bank_entries = frappe.db.sql(
		f"""
		SELECT
			DISTINCT je.name, je.company, sum(jea.debit) as total, je.voucher_type
		FROM
			`tabJournal Entry`je
		JOIN
			`tabJournal Entry Account`jea
		ON
			je.name = jea.parent
		WHERE
	 		je.docstatus = 1 AND  jea.payment_status NOT IN ('Paid', 'Ordered') AND
			je.voucher_type = 'Bank Entry' AND jea.party_type= "Employee" {search_condition}
		GROUP BY
			je.name, je.company, je.voucher_type
	 """,
		as_dict=1,
	)

	return bank_entries
