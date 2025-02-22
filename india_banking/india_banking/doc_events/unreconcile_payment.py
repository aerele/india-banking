import frappe

from india_banking.utils import get_payment_order_summary, unlink_bank_payment


def on_submit(doc, method=None):
	if doc.voucher_type != "Payment Entry":
		return

	if (
		frappe.db.get_value("Payment Entry", doc.voucher_no, "source_doctype")
		!= "Payment Request"
	):
		return

	payment_order_summary = get_payment_order_summary(doc.voucher_no)

	unlink_bank_payment(payment_order_summary)
