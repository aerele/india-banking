import frappe
from india_banking.india_banking.doc_events.payment_order import get_payment_status

def daily():
	orders = frappe.get_all("Payment Order Summary", 
		{
			'docstatus': 1, 
			'payment_status': 'Initiated'
		},
		pluck= 'parent', distinct='parent')

	for order in orders:
		try:
			frappe.enqueue(
				get_payment_status, docname= order, queue="short"
			)
		except:
			frappe.log_error(title="Error in Payment Order Status Cron", message=frappe.get_traceback())


def update_payment_status_for_processed_payment():
	statuses = ["Processed"]
	retry_period = frappe.get_single("India Banking Settings").retry_period or 3
	payment_orders = frappe.db.sql(
		"""
		SELECT DISTINCT parent
		FROM `tabPayment Order Summary`
		WHERE docstatus = 1
		AND payment_status IN %(statuses)s
		AND payment_date IS NOT NULL
		AND DATE_ADD(payment_date, INTERVAL %(retry_period)s DAY) >= CURDATE()
		""",
		{
			"statuses": statuses,
			"retry_period": retry_period,
		},
		as_list=True
	)

	payment_orders = [order[0] for order in payment_orders if order]

	for payment_order in payment_orders:
		frappe.enqueue(get_payment_status,queue="long",enqueue_after_commit=True, docname= payment_order, statuses=statuses)
