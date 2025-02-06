import frappe
from frappe.query_builder import DocType
from india_banking.india_banking.doc_events.payment_order import get_bank_info
import json
import requests
from frappe.utils import getdate

def daily():
	"""Daily task to update payment dates and repost ledger entries."""
	update_processed_payment_date()
	update_payment_date_as_posting_date()

def update_payment_date_as_posting_date():
	"""Update Payment Entry posting dates based on Payment Order Summary and repost accounting ledgers."""

	#check settings enabled
	if not frappe.get_single("India Banking Settings").update_posting_date_as_payment_date:
		return
	
	# Define DocTypes for query builder
	PaymentEntry = DocType("Payment Entry")
	PaymentOrderSummary = DocType("Payment Order Summary")

	# Fetch payment entries with mismatched posting dates
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
			reposting_doc.append("vouchers", {
				"voucher_type": "Payment Entry",
				"voucher_no": entry['payment_entry']
			})

		# Save and submit the Repost Accounting Ledger document
		reposting_doc.save()
		reposting_doc.submit()

def update_processed_payment_date():
	PaymentOrder = DocType("Payment Order")
	PaymentOrderSummary = DocType("Payment Order Summary")

	payment_orders = (
		frappe.qb.from_(PaymentOrder)
		.join(PaymentOrderSummary)
		.on(PaymentOrder.name == PaymentOrderSummary.parent)
		.select(PaymentOrder.name.as_("payment_order"), PaymentOrder.company_bank_account, PaymentOrderSummary.name.as_("payment_id"))
		.where(
			PaymentOrderSummary.payment_date.isnull()
			& (PaymentOrderSummary.payment_status == 'Processed')
		)
		.groupby(PaymentOrderSummary.name)
	).run(as_dict=True)

	for order in payment_orders:
		update_payment_date(
			order.get('company_bank_account'),
			order.get('payment_order'),
			order.get('payment_id')
		)


def update_payment_date(bank_account, payment_order, payment_id):
	bank_doc = frappe.get_doc("Bank Account", bank_account)

	bank_connector_exists = frappe.db.exists("Bank Connector", {"company": bank_doc.company, "bank": bank_doc.bank})

	if not bank_connector_exists:
		return

	bank_connector = frappe.get_doc("Bank Connector", bank_connector_exists)

	app_name = frappe._dict(get_bank_info(bank_doc.bank)).app_name

	if bank_connector.bank == "ICICI Bank" and not bank_connector.bulk_transaction:
		app_name += "_composite"

	url = f"{bank_connector.url}/api/method/{app_name}.{app_name}.doctype.bank_request_log.bank_request_log.get_payment_date"

	api_key = bank_connector.api_key
	api_secret = bank_connector.get_password("api_secret")
	headers = {
		"Authorization": f"token {api_key}:{api_secret}",
		"Content-Type": "application/json",
	}

	payload = {
		"payment_order": payment_order,
		"payment_id": payment_id
	}

	response = requests.request("POST", url, headers=headers, data= json.dumps({"payload": payload}))

	if response.status_code == 200:
		response = json.loads(response.text)
		response_data = frappe._dict((response.get('message') or {}))
		if response_data.get('server_status') == "Success":
			if response_data.payment_date:
				frappe.db.set_value("Payment Order Summary", payment_id, {
					"payment_date": getdate(response_data.payment_date),
					"payment_initiated": 1
				})
	else:
		frappe.log_error(title= "API Failed", message="Payment Date Fetched failed")
