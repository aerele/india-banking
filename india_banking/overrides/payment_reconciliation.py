import frappe
from erpnext.accounts.doctype.payment_reconciliation.payment_reconciliation import (
	PaymentReconciliation,
)
from frappe import _
from frappe.utils import cstr, get_link_to_form


class BankPaymentReconciliation(PaymentReconciliation):
	"""
	Override the PaymentReconciliation class to add custom validation before reconcile.
	"""

	@frappe.whitelist()
	def reconcile(self):
		for allocation in self.allocation:
			if allocation.invoice_type == "Purchase Invoice":
				if payment_request := frappe.db.exists(
					"Payment Request",
					{
						"reference_doctype": allocation.invoice_type,
						"reference_name": allocation.invoice_number,
						"docstatus": ["!=", 2],
					},
				):
					link = get_link_to_form("Payment Request", payment_request)
					frappe.throw(
						title=_("Payment Request Already Exists"),
						msg=_(
							"Payment Request - {0} already exists for {1} {2} at #Row {3}"
						).format(
							frappe.bold(link),
							frappe.bold(allocation.invoice_type),
							frappe.bold(allocation.invoice_number),
							frappe.bold(cstr(allocation.idx)),
						),
					)
		else:
			super().reconcile()
