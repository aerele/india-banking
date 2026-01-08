import frappe
from frappe.query_builder import DocType
from frappe.utils import add_to_date, getdate

from india_banking.india_banking.doctype.bank_connector.bank_connector import (
	get_bank_connector,
	get_payment_status,
)


def daily():
	update_payment_status_for_processed_payment()


def job_twenty_minutes():
	if frappe.get_single("India Banking Settings").status_check == "Every 20 Minutes":
		update_payment_date_as_posting_date()
		update_payment_status()


def job_one_hour():
	if frappe.get_single("India Banking Settings").status_check == "Every Hour":
		update_payment_date_as_posting_date()
		update_payment_status()


def job_at_midnight():
	if (
		frappe.get_single("India Banking Settings").status_check
		== "Every Day at Midnight"
	):
		update_payment_date_as_posting_date()
		update_payment_status()


def update_payment_status_for_processed_payment():
	statuses = ["Processed"]
	retry_period = frappe.get_single("India Banking Settings").update_payment_status

	PaymentOrderSummary = DocType("Payment Order Summary")
	payment_orders = (
		frappe.qb.from_(PaymentOrderSummary)
		.select(PaymentOrderSummary.parent)
		.where(
			(PaymentOrderSummary.docstatus == 1)
			& (PaymentOrderSummary.payment_status.isin(statuses))
			& (
				PaymentOrderSummary.payment_date
				>= frappe.utils.add_days(frappe.utils.nowdate(), -(retry_period))
			)
			& (PaymentOrderSummary.payment_date.isnotnull())
		)
		.distinct()
	).run(pluck=True)

	for payment_order in payment_orders:
		payment_order = frappe.get_doc("Payment Order", payment_order)
		bank_connector = get_bank_connector(
			payment_order.company_bank_account, payment_order.company
		)
		bank_connector.action = "get_payment_status"
		bank_connector.add_payment_in_the_background(
			payment_order=payment_order, statuses=statuses
		)


def update_payment_status():
	if not frappe.get_single("India Banking Settings").update_payment_status:
		return

	PaymentOrderSummary = DocType("Payment Order Summary")
	orders = (
		frappe.qb.from_(PaymentOrderSummary)
		.select(PaymentOrderSummary.parent)
		.where(
			(PaymentOrderSummary.docstatus == 1)
			& (PaymentOrderSummary.payment_status.isin(["Pending", "Initiated"]))
		)
		.distinct()
	).run(pluck=True)

	for order in orders:
		try:
			frappe.enqueue(get_payment_status, payment_order=order, queue="short")
		except Exception:
			frappe.log_error(
				title="Error in Payment Order Status Cron",
				message=frappe.get_traceback(),
			)


def update_payment_date_as_posting_date():
	"""Update Payment Entry posting dates based on Payment date in Payment Order Summary and repost accounting ledgers."""
	try:
		if not frappe.get_single(
			"India Banking Settings"
		).update_posting_date_as_payment_date:
			return

		PaymentEntry = DocType("Payment Entry")
		PaymentOrderSummary = DocType("Payment Order Summary")

		reposting_entries = (
			frappe.qb.from_(PaymentOrderSummary)
			.join(PaymentEntry)
			.on(PaymentOrderSummary.payment_entry == PaymentEntry.name)
			.select(PaymentOrderSummary.payment_entry)
			.where(
				(PaymentEntry.docstatus == 1)
				& (PaymentOrderSummary.payment_date.isnotnull())
				& (PaymentOrderSummary.payment_date != PaymentEntry.posting_date)
			)
			.groupby(PaymentEntry.name)
		).run(as_dict=True)

		if reposting_entries:
			# Update mismatched posting dates
			(
				frappe.qb.update(PaymentEntry)
				.join(PaymentOrderSummary)
				.on(PaymentOrderSummary.payment_entry == PaymentEntry.name)
				.set(PaymentEntry.posting_date, PaymentOrderSummary.payment_date)
				.where(
					(PaymentEntry.docstatus == 1)
					& (PaymentOrderSummary.payment_date.isnotnull())
					& (PaymentOrderSummary.payment_date != PaymentEntry.posting_date)
				)
			).run()
			frappe.db.commit()
			# Repost accounting ledger entries for updated Payment Entries
			reposting_doc = frappe.new_doc("Repost Accounting Ledger")
			for entry in reposting_entries:
				reposting_doc.append(
					"vouchers",
					{
						"voucher_type": "Payment Entry",
						"voucher_no": entry["payment_entry"],
					},
				)

			reposting_doc.save()
			reposting_doc.submit()
	except Exception:
		frappe.log_error(
			title="Error in Payment Date Update Cron",
			message=frappe.get_traceback(),
		)


def clear_india_banking_request_log(days=7):
	"""Clear India Banking Request Logs"""
	settings = frappe.get_single("India Banking Settings")
	if not settings.clear_india_banking_request_log:
		return

	stale_days = settings.stale_days or 15  # Default to 15 days if not set
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
