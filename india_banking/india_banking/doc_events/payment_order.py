import frappe
import frappe.utils
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_accounting_dimensions,
)
from frappe import _, parse_json


@frappe.whitelist()
def cancel_pending_payments(data):
	if isinstance(data, str) or isinstance(data, dict):
		data = parse_json(data)

	success_count = 0
	for d in data:
		d = parse_json(d)
		if d.row_name:
			if d.status == "Failed":
				frappe.db.set_value(
					"Payment Order Summary",
					d.row_name,
					{"payment_status": "Failed", "payment_initiated": 1},
				)

				if d.payment_entry:
					payment_entry_doc = frappe.get_doc("Payment Entry", d.payment_entry)
					if payment_entry_doc.docstatus == 1:
						payment_entry_doc.cancel()

				process_payment_requests(d.row_name)

				success_count += 1
	if success_count:
		frappe.msgprint(_(f"{success_count} payment(s) updated"))


def process_payment_requests(payment_order_summary):
	pos = frappe.get_doc("Payment Order Summary", payment_order_summary)
	payment_order_doc = frappe.get_doc("Payment Order", pos.parent)

	summarise_field = [
		"party_type",
		"party",
		"bank_account",
		"account",
		"cost_center",
		"project",
		"tax_withholding_category",
		"reference_doctype",
		"reference_name",
		"payment_entry",
		"journal_entry_account",
	]
	if payment_order_doc.summarise_payment_based_on == "Party":
		summarise_field.remove("reference_name")

	summarise_field.extend(get_accounting_dimensions())
	key = tuple([pos.get(field, "") for field in summarise_field])

	failed_prs = []
	for ref in payment_order_doc.references:
		ref_key = tuple([(ref.get(field, "") or "") for field in summarise_field])

		if key == ref_key and ref.payment_request:
			failed_prs.append(ref.payment_request)

	for pr in failed_prs:
		pr_doc = frappe.get_doc("Payment Request", pr)
		if pr_doc.docstatus == 1:
			pr_doc.check_if_payment_entry_exists()
			pr_doc.set_as_cancelled()
			pr_doc.db_set("docstatus", 2)
