import frappe
from india_banking.india_banking.doc_events.payment_order import get_payment_status
def daily():
	pass

def job_twenty_minutes():
	if frappe.get_single("India Banking Settings").status_check == "Every 20 Minutes":
		update_payment_status()

def job_one_hour():
	if frappe.get_single("India Banking Settings").status_check == "Every Hour":
		update_payment_status()

def job_at_midnight():
	if frappe.get_single("India Banking Settings").status_check == "Every Day at Midnight":
		update_payment_status()

def update_payment_status():
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