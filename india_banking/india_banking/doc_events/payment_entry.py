from india_banking.utils import get_payment_order_summary, unlink_bank_payment


def on_cancel(doc, method=None):
	if doc.source_doctype == "Payment Request":
		payment_order_summary = get_payment_order_summary(doc.name)

		unlink_bank_payment(payment_order_summary)
