import erpnext
import frappe
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_accounting_dimensions,
)
from frappe.utils import flt


def make_bank_entries(docname):
	payment_order = frappe.get_doc("Payment Order", docname)

	bank_entry = frappe.new_doc("Journal Entry")
	bank_entry.check_permission("write")
	bank_entry.voucher_type = "Bank Entry"
	bank_entry.company = payment_order.company
	bank_entry.posting_date = payment_order.posting_date

	precision = frappe.get_precision(
		"Journal Entry Account", "debit_in_account_currency"
	)

	bank_entry.append(
		"accounts",
		{
			"account": payment_order.account,
			"bank_account": payment_order.company_bank_account,
			"credit_in_account_currency": flt(payment_order.total, precision),
			"exchange_rate": 1.0,
			"cost_center": payment_order.cost_center,
			"project": payment_order.project,
		},
	)

	for reference in payment_order.references:
		bank_entry.append(
			"accounts",
			{
				"account": reference.account,
				"bank_account": reference.bank_account,
				"party_type": "Employee",
				"party": reference.party,
				"debit_in_account_currency": flt(reference.amount, precision),
				"reference_type": reference.reference_doctype,
				"reference_name": reference.reference_name,
				"exchange_rate": 1.0,
				"cost_center": reference.cost_center,
				"project": reference.project,
				**{
					dimention: reference.get(reference, "")
					for dimention in get_accounting_dimensions()
				},
			},
		)

	bank_entry.cheque_no = payment_order.name
	bank_entry.cheque_date = payment_order.posting_date

	bank_entry.save()
	bank_entry.submit()

	update_bank_entry_reference_in_payment_order(bank_entry)


def update_bank_entry_reference_in_payment_order(bank_entry, on_cancel=False):
	bank_entry.reload()
	for entry in bank_entry.accounts[1:]:
		filters = {
			"party_type": entry.party_type,
			"party": entry.party,
			"reference_doctype": entry.reference_type,
			"reference_name": entry.reference_name,
		}

		frappe.db.set_value(
			"Payment Order Reference",
			filters,
			"journal_entry_account",
			"" if on_cancel else entry.name,
		)
		frappe.db.set_value(
			"Payment Order Summary",
			filters,
			"journal_entry_account",
			"" if on_cancel else entry.name,
		)
		frappe.db.commit()
