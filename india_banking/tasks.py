import frappe
from india_banking.india_banking.doc_events.payment_order import get_payment_status
from frappe.utils import add_to_date, getdate


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


def clear_india_banking_request_log(days=7):
	"""Clear India Banking Request Logs"""
	settings = frappe.get_single("India Banking Settings")
	if not settings.clear_india_banking_request_log:
		return

	stale_days = settings.stale_days or 30  # Default to 30 days if not set
	try:
		count = frappe.db.count(
			"India Banking Request Log",
			{
				"creation": ["<", add_to_date(getdate(), days=-stale_days)],
			},
		)
		if count > 50000:
			end = add_to_date(getdate(), days=-stale_days)
			start = add_to_date(end, days=-(days + 7))  # Delete in batches of 7 days
			frappe.db.delete(
				"India Banking Request Log",
				{
					"creation": ["between", [start, end]],
				},
			)
			count = frappe.db.count(
				"India Banking Request Log",
				{
					"creation": ["<", add_to_date(getdate(), days=-stale_days)],
				},
			)
			if count > 50000:
				frappe.enqueue(
					clear_india_banking_request_log, days=days + 7
				)  # Enqueue next batch
		else:
			frappe.db.delete(
				"India Banking Request Log",
				{
					"creation": ["<", add_to_date(getdate(), days=-stale_days)],
				},
			)
	except Exception:
		frappe.log_error(title="Failed to clear Bank Request Log")
