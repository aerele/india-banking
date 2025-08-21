import frappe
from frappe import _, bold
from frappe.utils import cstr, get_link_to_form


def validate(doc, method=None):
	if doc.docstatus != 1:
		return
	# Check payment request existence for purchase invoices or purchase orders
	for acc in doc.accounts:
		if (
			acc.party_type == "Supplier"
			and acc.reference_type in ["Purchase Order", "Purchase Invoice"]
			and acc.debit > 0
		):
			if payment_request := frappe.db.exists(
				"Payment Request",
				{
					"reference_doctype": acc.reference_type,
					"reference_name": acc.reference_name,
					"docstatus": ["!=", 2],
				},
			):
				link = get_link_to_form("Payment Request", payment_request)
				frappe.throw(
					title=_("Payment Request Already Exists"),
					msg=_(
						"Payment Request - {0} already exists for {1} {2} at #Row {3}"
					).format(
						bold(link),
						bold(acc.reference_type),
						bold(acc.reference_name),
						bold(cstr(acc.idx)),
					),
				)
