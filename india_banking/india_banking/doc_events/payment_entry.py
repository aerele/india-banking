import frappe
from frappe import _


def validate(doc, method=None):
	if doc.source_doctype == "Payment Request":
		return

	# Check payment request existence for purchase invoices or purchase orders
	for reference in doc.references:
		if reference.reference_doctype in ["Purchase Invoice", "Puchase Order"]:
			if payment_request := frappe.db.exists(
				"Payment Request",
				{
					"reference_doctype": reference.reference_doctype,
					"reference_name": reference.reference_name,
					"docstatus": ["!=", 2],
				},
			):
				frappe.throw(
					_("Payment Request - {0} already exists for {1} {2}").format(
						frappe.bold(payment_request),
						frappe.bold(reference.reference_doctype),
						frappe.bold(reference.reference_name),
					)
				)
