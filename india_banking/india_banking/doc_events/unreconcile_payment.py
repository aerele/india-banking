import frappe
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_accounting_dimensions,
)
from frappe.utils import cstr

from india_banking.default import PAYMENT_SUMMARIES_FIELDS


def on_submit(doc, method=None):
	if doc.voucher_type != "Payment Entry":
		return

	if (
		frappe.db.get_value("Payment Entry", doc.voucher_no, "source_doctype")
		!= "Payment Request"
	):
		return

	payment_order_summary = get_payment_order_summary(doc.voucher_no)
	if not payment_order_summary:
		return

	payment_order = frappe.get_doc("Payment Order", payment_order_summary.parent)

	summarise_field = PAYMENT_SUMMARIES_FIELDS.copy()
	summarise_field.remove("payment_entry")
	summarise_field.extend(get_accounting_dimensions())
	if payment_order.summarise_payment_based_on == "Party":
		summarise_field.remove("reference_name")

	for reference in payment_order.references:
		if all(
			(
				cstr(reference.get(field, ""))
				== cstr(payment_order_summary.get(field, ""))
				for field in summarise_field
			)
		):
			frappe.db.set_value(
				"Payment Request",
				reference.bank_payment_request,
				{"reference_doctype": "", "reference_name": ""},
			)
			frappe.db.set_value(
				"Payment Order Reference",
				reference.name,
				{"reference_doctype": "", "reference_name": ""},
			)


def get_payment_order_summary(payment_entry):
	is_ammended = frappe.db.get_value("Payment Entry", payment_entry, "amended_from")
	payment_entry = (
		"-".join(payment_entry.split("-")[:-1]) if is_ammended else payment_entry
	)
	summary = frappe.db.get_value(
		"Payment Order Summary", {"payment_entry": payment_entry}, "name"
	)
	if summary:
		return frappe.get_doc("Payment Order Summary", summary)
