import frappe

from india_banking.india_banking.doc_events.payment_order import get_payment_status


def daily():
	orders = frappe.get_all(
		"Payment Order Summary",
		{"docstatus": 1, "payment_status": "Initiated"},
		pluck="parent",
		distinct="parent",
	)

	for order in orders:
		try:
			frappe.enqueue(get_payment_status, docname=order, queue="short")
		except:
			frappe.log_error(
				title="Error in Payment Order Status Cron",
				message=frappe.get_traceback(),
			)
