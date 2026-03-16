import time

import frappe
from frappe.query_builder import DocType
from frappe.utils import cstr, get_datetime, time_diff_in_seconds, today

from india_banking.india_banking.doctype.bank_connector.bank_connector import (
	get_bank_statement,
)
from india_banking.india_banking.doctype.india_banking_connector.india_banking_connector import (
	get_bank_connector,
	get_payment_status,
)
from india_banking.utils import get_connected_bank_accounts


def daily():
	for connector in get_connected_bank_accounts():
		update_payment_status(check_processed_payments=True, connector=connector)

	for statement_connector in frappe.get_all(
		"India Banking Connector", {"fetch_bank_statement": 1}, pluck="name"
	):
		date = today()
		get_bank_statement(statement_connector, date, date)


def job_twenty_minutes():
	for connector in get_connected_bank_accounts():
		if (
			frappe.db.get_value("India Banking Connector", connector, "status_check_at")
			== "Every 20 Minutes"
		):
			update_payment_date_as_posting_date(connector=connector)
			update_payment_status(connector=connector)


def job_one_hour():
	for connector in get_connected_bank_accounts():
		if (
			frappe.db.get_value("India Banking Connector", connector, "status_check_at")
			== "Every Hour"
		):
			update_payment_date_as_posting_date(connector=connector)
			update_payment_status(connector=connector)


def job_at_midnight():
	for connector in get_connected_bank_accounts():
		if (
			frappe.db.get_value("India Banking Connector", connector, "status_check_at")
			== "Every Day at Midnight"
		):
			update_payment_date_as_posting_date(connector=connector)
			update_payment_status(connector=connector)


def update_payment_status(check_processed_payments=False, connector=None):
	if connector and not frappe.db.get_value(
		"India Banking Connector", connector, "auto_update_payment_status"
	):
		return

	PaymentOrder = DocType("Payment Order")
	PaymentOrderSummary = DocType("Payment Order Summary")

	orders = (
		frappe.qb.from_(PaymentOrder)
		.join(PaymentOrderSummary)
		.on(PaymentOrder.name == PaymentOrderSummary.parent)
		.select(PaymentOrderSummary.parent)
		.where(
			(PaymentOrderSummary.docstatus == 1)
			& (PaymentOrderSummary.payment_status.isin(["Pending", "Initiated"]))
		)
		.distinct()
	).run(pluck=True)

	for order in orders:
		try:
			frappe.enqueue(
				get_payment_status,
				queue="short",
				payment_order=order,
				check_processed_payments=check_processed_payments,
			)
		except Exception:
			frappe.log_error(
				title="Error in Payment Order Status Cron",
				message=frappe.get_traceback(),
			)


def update_payment_date_as_posting_date(connector=False):
	"""Update Payment Entry posting dates based on Payment date in Payment Order Summary and repost accounting ledgers."""
	try:
		if connector and frappe.db.get_value(
			"India Banking Connector",
			connector,
			"auto_update_posting_date_as_payment_date",
		):
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


def process_payment_in_the_background(connector=None, force=False):
	"""Enqueue payment processing in the background."""
	connectors = []
	if connector:
		connectors = [connector]
	else:
		connectors = frappe.get_all(
			"India Banking Connector",
			{"auto_post_payments": 1},
			["name", "last_execution", "retry_interval_minutes", "batch_size"],
		)

	for connector in connectors:
		try:
			retry_interval_minutes = connector.retry_interval_minutes or 5
			if (
				force
				or not connector.last_execution
				or time_diff_in_seconds(
					cstr(get_datetime()).split(".")[0],
					cstr(connector.last_execution).split(".")[0],
				)
				/ 60
				> retry_interval_minutes
			):
				orders = get_pending_payments(connector.name).run(as_dict=True)
				payment_details = {}
				for order in orders:
					if order["payment_order"] not in payment_details:
						payment_details[order["payment_order"]] = [order["payment"]]
					else:
						payment_details[order["payment_order"]].append(order["payment"])

				process_batch_payment(payment_details, connector.batch_size)
				frappe.db.set_value(
					"India Banking Connector",
					connector.name,
					"last_execution",
					get_datetime(),
				)
		except Exception:
			frappe.log_error(
				"Background Payment failed!", frappe.get_traceback(with_context=1)
			)


def get_pending_payments(company_bank_account):
	PO = DocType("Payment Order")
	POS = DocType("Payment Order Summary")
	return (
		frappe.qb.from_(PO)
		.join(POS)
		.on(PO.name == POS.parent)
		.select(PO.name.as_("payment_order"), POS.name.as_("payment"))
		.where(
			(POS.payment_status.isin(["Pending"]))
			& (POS.payment_initiated == 0)
			& (PO.enqueue_status.isin(["Queued", "In Progress"]))
			& (PO.docstatus == 1)
			& (PO.company_bank_account == company_bank_account)
		)
	)


def process_batch_payment(payment_details, batch_size):
	start_time = time.time()
	enqueue_count = 0

	for payment_order, summary in payment_details.items():
		payment_order_doc = frappe.get_doc("Payment Order", payment_order)
		payment_order_doc.db_set("enqueue_status", "In Progress", update_modified=False)
		bank_connector = get_bank_connector(
			payment_order_doc.company_bank_account, payment_order_doc.company
		)
		last_call = None
		payment_delay = bank_connector.payment_call_interval or 10  # default 10 sec
		for summary_row in payment_order_doc.summary:
			if not last_call:
				last_call = time.time()
			else:
				last_call = bank_connector.check_payment_delay(last_call)

			# Stop processing to avoid background job timeout (Default - 5 min)
			if (time.time() - start_time) > (300 - payment_delay):
				break
			if batch_size and enqueue_count > batch_size:
				break

			if summary_row.name in summary:
				try:
					summary_doc = frappe.get_doc(
						"Payment Order Summary", summary_row.name
					)
					bank_connector.action = "initiate_payment"
					bank_connector.make_single_request(payment_order_doc, summary_doc)
					enqueue_count += 1
				except Exception:
					frappe.log_error(
						title="Error processing payment - {0}".format(summary_row.name),
						message=frappe.get_traceback(with_context=True),
					)
				else:
					# Force commit to avoid success request data loss
					frappe.db.commit()

		payment_order_doc.load_from_db()
		is_pending = all(
			summary.payment_status == "Pending" or summary.payment_initiated == 0
			for summary in payment_order_doc.summary
		)

		if is_pending:
			payment_order_doc.db_set("enqueue_status", "Queued", update_modified=False)
		else:
			payment_order_doc.db_set(
				"enqueue_status", "Completed", update_modified=False
			)

		# Stop processing to avoid background job timeout (Default - 5 min)
		if (time.time() - start_time) > (300 - payment_delay):
			break
		if batch_size and enqueue_count > batch_size:
			break
