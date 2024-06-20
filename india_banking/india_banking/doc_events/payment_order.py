from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import get_accounting_dimensions
import frappe
from frappe.utils import nowdate, getdate, now
import json
import frappe.utils
from frappe.utils.data import comma_and, cstr
import uuid, requests
import random

from india_banking.india_banking.install import STD_BANK_LIST
from india_banking.india_banking.doctype.india_banking_request_log.india_banking_request_log import create_api_log

@frappe.whitelist()
def generate_payment_otp(docname):
	payment_order_doc = frappe.get_doc("Payment Order", docname)
	payment_order_doc.update_unique_and_file_reference_id(save=True)

	payment_order_doc.reload()

	# Fetch the connector information
	bank_connector_exists = frappe.db.exists("Bank Connector",
		{
			"company": payment_order_doc.company,
			"bank_account": payment_order_doc.company_bank_account
		}
	)

	if not bank_connector_exists:
		frappe.throw("Bank Connector is not initialized")
  
	bank_connector = frappe.get_doc("Bank Connector", bank_connector_exists)

	payment_payload = {}

	#payload reference to this payment.
	payment_payload['doc'] = payment_order_doc.as_dict(convert_dates_to_str=True)

	if not payment_order_doc.company_account_number:
		frappe.throw("Source bank account number is missing")

	app_name =  frappe._dict(get_bank_info(payment_order_doc.company_bank)).app_name

	url = f"{bank_connector.url}/api/method/{app_name}.{app_name}.doctype.bank_request_log.bank_request_log.generate_otp"

	api_key = bank_connector.api_key
	api_secret = bank_connector.get_password("api_secret")
	headers = {
		"Authorization": f"token {api_key}:{api_secret}",
		"Content-Type": "application/json"
	}
	response = requests.request("POST", url, headers=headers,data= json.dumps({'payload': payment_payload}))

	#create api response log
	create_api_log(response, 'Generate Otp' , payment_order_doc.doctype, payment_order_doc.name)

	if response.ok:
		response_details = response.json().get('message')
		if response_details.get('server_status') == 'success':
			frappe.msgprint(response_details.get('server_message'), alert=1, indicator='green')
		else:
			frappe.msgprint(response_details.get('server_message'), alert=1, indicator='red')
	else:
		frappe.throw('Invalid Request')

@frappe.whitelist()
def make_bank_payment(docname, otp=None):
	if not frappe.has_permission("Payment Order", "write"):
		frappe.throw("Not permitted", frappe.PermissionError)

	payment_order_doc = frappe.get_doc("Payment Order", docname)

	# Fetch the connector information
	bank_connector_exists = frappe.db.exists("Bank Connector",
		{
			"company": payment_order_doc.company,
			"bank_account": payment_order_doc.company_bank_account
		}
	)

	if not bank_connector_exists:
		frappe.throw("Bank Connector is not initialized")

	bank_connector = frappe.get_doc("Bank Connector", bank_connector_exists)

	if payment_order_doc.company_bank == 'ICICI Bank' and bank_connector.bulk_transaction and not otp:
		frappe.throw(title='Invalid OTP', msg='Cannot Initiate Payment without OTP')

	if payment_order_doc.company_bank == 'ICICI Bank'and bank_connector.bulk_transaction:
		payment_response = process_bulk_payment(payment_order_doc, otp)

		if payment_response.get('server_status') == 'success':
			frappe.db.set_value("Payment Order", docname, "status", "Initiated")
			frappe.db.set_value("Payment Order", docname, "file_sequence_number", payment_response.get('file_sequence_number'))

			for row in payment_order_doc.summary:
				frappe.db.set_value("Payment Order Summary", row.name, "payment_initiated", 1)
				frappe.db.set_value("Payment Order Summary", row.name, "payment_status", "Initiated")
				frappe.db.set_value("Payment Order Summary", row.name, "payment_date", nowdate())

		if payment_response.get('server_status') == 'failed':
			return {"message": "Failed - "+ cstr(payment_response.get('server_message'))}

		return {"message": "Payment Initiated"}

	else:
		count = 0
		for i in payment_order_doc.summary:
			if not i.payment_initiated and i.payment_status == "Pending":
				payment_response = process_payment(
					i, payment_order_doc
				)

				if payment_response and "payment_status" in payment_response and payment_response["payment_status"] == "Initiated":
					frappe.db.set_value("Payment Order Summary", i.name, "payment_initiated", 1)
					frappe.db.set_value("Payment Order Summary", i.name, "payment_status", "Initiated")
					frappe.db.set_value("Payment Order Summary", i.name, "payment_date", nowdate())
					count += 1
				elif payment_response and "payment_status" in payment_response and payment_response["payment_status"] == "":
					if "message" in payment_response:
						frappe.db.set_value("Payment Order Summary", i.name, "message", payment_response["message"])
				else:
					frappe.db.set_value("Payment Order Summary", i.name, "payment_status", "Failed")
					payment_entry_doc = frappe.get_doc("Payment Entry", i.payment_entry)
					if payment_entry_doc.docstatus == 1:
						payment_entry_doc.cancel()
		
					process_bank_payment_requests(i.name)

					if payment_response and "message" in payment_response:
						frappe.db.set_value("Payment Order Summary", i.name, "message", payment_response["message"])

		payment_order_doc.reload()
		processed_count = 0
		for i in payment_order_doc.summary:
			if i.payment_initiated:
				processed_count += 1
		
		if processed_count == len(payment_order_doc.summary):
			frappe.db.set_value("Payment Order", docname, "status", "Initiated")

		return {"message": f"{count} payments initiated"}

def process_bulk_payment(payment_order_doc, otp):
	# Fetch the connector information
	bank_connector_exists = frappe.db.exists("Bank Connector",
		{
			"company": payment_order_doc.company, 
			"bank_account": payment_order_doc.company_bank_account
		}
	)

	if not bank_connector_exists:
		frappe.throw("Bank Connector is not initialized")
  
	bank_connector = frappe.get_doc("Bank Connector", bank_connector_exists)
	
	payment_payload = {}

	#payment payload.
	payment_payload['doc'] = payment_order_doc.as_dict(convert_dates_to_str=True)
	payment_payload['otp'] = otp

	payment_account_list = []

	#Lei number validation
	for ref in payment_order_doc.summary:
		if ref.mode_of_transfer == "RTGS" and ref.amount >= 500000000:
			lei_number = frappe.db.get_value(ref.party_type, ref.party, "lei_number")
			payment_account_list.append(ref.account_name + '-' + lei_number)
			if not lei_number:
				frappe.throw("LEI Number required for payment > 50 Cr")
		else:
			payment_account_list.append(ref.account_name + '-' + ref.bank_account_no)

	payment_payload['desc'] = f"Payment to {comma_and(payment_account_list)} via {payment_order_doc.name}"

	if not payment_order_doc.company_account_number:
		frappe.throw("Source bank account number is missing")
 
	app_name = frappe._dict(get_bank_info(payment_order_doc.company_bank)).app_name

	if bank_connector.bank == "ICICI Bank" and not bank_connector.bulk_transaction:
		app_name += "_composite"

	url = f"{bank_connector.url}/api/method/{app_name}.{app_name}.doctype.bank_request_log.bank_request_log.make_payment"

	api_key = bank_connector.api_key
	api_secret = bank_connector.get_password("api_secret")
	headers = {
		"Authorization": f"token {api_key}:{api_secret}",
		"Content-Type": "application/json",
	}

	response = requests.request("POST", url, headers=headers, data=json.dumps({"payload": payment_payload}))

	#create api request log
	create_api_log(response, 'Make Payment', payment_order_doc.doctype, payment_order_doc.name)

	if response.ok:
		payment_details =response.json()
		return payment_details.get('message')

	frappe.throw('Invalid payment request')

@frappe.whitelist()
def get_bulk_payment_status(payment_order_doc):
	bank_connector_exists = frappe.db.exists("Bank Connector",
		{
			"company": payment_order_doc.company,
			"bank_account": payment_order_doc.company_bank_account
		}
	)

	if not bank_connector_exists:
		frappe.throw("Bank Connector is not initialized")

	bank_connector = frappe.get_doc("Bank Connector", bank_connector_exists)

	payment_payload = {}

	#payload reference to get payment status
	payment_payload['doc'] = payment_order_doc.as_dict(convert_dates_to_str=True)

	app_name =  frappe._dict(get_bank_info(payment_order_doc.company_bank)).app_name

	if bank_connector.bank == "ICICI Bank" and not bank_connector.bulk_transaction:
		app_name += "_composite"

	url = f"{bank_connector.url}/api/method/{app_name}.{app_name}.doctype.bank_request_log.bank_request_log.get_payment_status"

	api_key = bank_connector.api_key
	api_secret = bank_connector.get_password("api_secret")
	headers = {
		"Authorization": f"token {api_key}:{api_secret}",
		"Content-Type": "application/json",
	}

	response = requests.request("POST", url, headers=headers, data=json.dumps({'payload': payment_payload}))

	#create api request log
	create_api_log(response, 'Get Payment Status', payment_order_doc.doctype, payment_order_doc.name)

	if response.ok:
		response_details = frappe._dict(response.json().get('message', {}))
		payment_details = response_details.payment_status
		if response_details.get('server_status') == 'success':
			frappe.msgprint(response_details.get('server_message'), response_details.get('file_status'))
			if payment_details:
				for row in payment_order_doc.summary:
					row_payment_status = frappe._dict(payment_details.get(row.name, {}))
					if row.payment_status == "Initiated" and row_payment_status:
						if row_payment_status.transaction_status == 'SUC':
							frappe.db.set_value("Payment Order Summary", row.name,
								{
									"reference_number": row_payment_status.host_reference_number,
									"payment_status": 'Processed',
									"message": row_payment_status.host_response_message
								}
							)
							frappe.db.set_value("Payment Entry", row.payment_entry,
								"reference_no", row_payment_status.host_reference_number
							)
						elif row_payment_status.transaction_status == 'FAL':
							frappe.db.set_value("Payment Order Summary", row.name,
								"payment_status", 'Failed'
							)
							payment_entry_doc = frappe.get_doc("Payment Entry", row.payment_entry)
							if payment_entry_doc.docstatus == 1:
								payment_entry_doc.cancel()
							process_bank_payment_requests(row.name)
			update_payment_status(payment_order_doc)
		else:
			frappe.throw(msg=response_details.server_message, title='Failed')
	else:
		frappe.throw('Invalid Request')

def update_payment_status(payment_order_doc):
	success_count = 0
	faild_count = 0
	for ref in payment_order_doc.summary:
		if ref.payment_status == 'Processed':
			success_count += 1
		if ref.payment_status == 'Failed':
			faild_count += 1

	if success_count == len(payment_order_doc.summary):
		frappe.db.set_value("Payment Order",
			payment_order_doc.name,
			"status", 'Completed'
		)

	if faild_count == len(payment_order_doc.summary):
		frappe.db.set_value("Payment Order",
			payment_order_doc.name,
			"status", 'Failed'
		)

@frappe.whitelist()
def get_payment_status(docname):
	payment_order_doc = frappe.get_doc("Payment Order", docname)

	# Fetch the connector information
	bank_connector_exists = frappe.db.exists("Bank Connector",
		{
			"company": payment_order_doc.company,
			"bank_account": payment_order_doc.company_bank_account
		}
	)

	if not bank_connector_exists:
		frappe.throw("Bank Connector is not initialized")

	bank_connector = frappe.get_doc("Bank Connector", bank_connector_exists)

	if payment_order_doc.company_bank == 'ICICI Bank' and bank_connector.bulk_transaction :
		get_bulk_payment_status(payment_order_doc)

	else:
		for i in payment_order_doc.summary:
			if i.payment_status == "Initiated":
				payment_response = get_response(i, payment_order_doc.company_bank_account, payment_order_doc.company)

		payment_order_doc.reload()
		update_payment_status(payment_order_doc)

@frappe.whitelist()
def make_payment_entries(docname):
	payment_order_doc = frappe.get_doc("Payment Order", docname)
	"""create entry"""
	frappe.flags.ignore_account_permission = True

	for row in payment_order_doc.summary:
		pe = frappe.new_doc("Payment Entry")
		pe.payment_type = "Pay"
		pe.payment_entry_type = "Pay"
		pe.company = payment_order_doc.company
		pe.cost_center = row.cost_center
		pe.project = row.project
		pe.posting_date = nowdate()
		pe.mode_of_payment = "Wire Transfer"
		pe.party_type = row.party_type
		pe.party = row.party
		pe.bank_account = payment_order_doc.company_bank_account
		pe.party_bank_account = row.bank_account
		if pe.party_type == "Supplier":
			pe.ensure_supplier_is_not_blocked()
		pe.payment_order = payment_order_doc.name

		pe.paid_from = payment_order_doc.account
		if row.account:
			pe.paid_to = row.account
		pe.paid_from_account_currency = "INR"
		pe.paid_to_account_currency = "INR"
		pe.paid_amount = row.amount
		pe.received_amount = row.amount
		pe.letter_head = frappe.db.get_value("Letter Head", {"is_default": 1}, "name")
		pe.source_doctype = payment_order_doc.payment_order_type

		for dimension in get_accounting_dimensions():
			pe.update({dimension: payment_order_doc.get(dimension, '')})

		if row.tax_withholding_category:
			net_total = 0

			if not payment_order_doc.is_party_wise:
				net_total = row.amount
			else:
				for reference in payment_order_doc.references:
					if reference.party_type == row.party_type and \
							reference.party == row.party and \
							reference.cost_center == row.cost_center and \
							reference.project == row.project and \
							reference.bank_account == row.bank_account and \
							reference.account == row.account and \
							reference.tax_withholding_category == row.tax_withholding_category and \
							reference.reference_doctype == row.reference_doctype:
						net_total += frappe.db.get_value("Bank Payment Request", reference.bank_payment_request, "net_total")
			pe.paid_amount = net_total
			pe.received_amount = net_total
			pe.apply_tax_withholding_amount = 1
			pe.tax_withholding_category = row.tax_withholding_category
		for reference in payment_order_doc.references:

			if not reference.is_adhoc:
				filter_condition = ( reference.party_type == row.party_type and reference.party == row.party and reference.cost_center == row.cost_center
					and reference.project == row.project and reference.bank_account == row.bank_account and reference.account == row.account
					and reference.tax_withholding_category == row.tax_withholding_category and reference.reference_doctype == row.reference_doctype )
				if not payment_order_doc.is_party_wise:
					filter_condition = filter_condition and (reference.reference_doctype == row.reference_doctype and reference.reference_name == row.reference_name)

				if filter_condition:
					pe.append(
						"references",
						{
							"reference_doctype": reference.reference_doctype,
							"reference_name": reference.reference_name,
							"total_amount": reference.amount,
							"allocated_amount": reference.amount,
						},
					)
		pe.update(
			{
				"reference_no": payment_order_doc.name,
				"reference_date": nowdate(),
				"remarks": "Bank Payment Entry from Payment Order - {0}".format(
					payment_order_doc.name
				),
			}
		)
		pe.setup_party_account_field()
		pe.set_missing_values()
		pe.validate()
		pe.insert(ignore_permissions=True, ignore_mandatory=True)
		pe.submit()
		frappe.db.set_value("Payment Order Summary", row.name, "payment_entry", pe.name)

def process_payment(payment_info, payment_order_doc):
	# Fetch the connector information
	bank_connector_exists = frappe.db.exists("Bank Connector", {
			"company": payment_order_doc.company,
			"bank_account": payment_order_doc.company_bank_account
		}
	)

	if not bank_connector_exists:
		frappe.throw("Bank Connector is not initialized")

	bank_connector = frappe.get_doc("Bank Connector", bank_connector_exists)

	payment_payload = frappe._dict(payment_info.as_dict(convert_dates_to_str=True))

	party_field_name = "supplier_name" if payment_info.party_type == "Supplier" else "employee_name"

	party_name = frappe.db.get_value(payment_info.party_type, payment_info.party, party_field_name)

	payment_payload.party_name = party_name
	payment_payload.desc = f"Payment to {payment_info.party} via {payment_info.parent}"

	payment_payload.doc = payment_order_doc.as_dict(convert_dates_to_str=True)

	if not payment_order_doc.company_account_number:
		frappe.throw("Source bank account number is missing")

	app_name = frappe._dict(get_bank_info(payment_order_doc.company_bank)).app_name

	if bank_connector.bank == "ICICI Bank" and not bank_connector.bulk_transaction:
		app_name += "_composite"

	url = f"{bank_connector.url}/api/method/{app_name}.{app_name}.doctype.bank_request_log.bank_request_log.make_payment"

	api_key = bank_connector.api_key
	api_secret = bank_connector.get_password("api_secret")
	headers = {
		"Authorization": f"token {api_key}:{api_secret}",
		"Content-Type": "application/json",
	}

	response = requests.request("POST", url, headers=headers, data=json.dumps({"payload": payment_payload}))

	#create api request log
	create_api_log(response, 'Make Payment', payment_info.parenttype, payment_info.parent)

	if response.status_code == 200:
		response = json.loads(response.text)
		response_data = frappe._dict((response.get('message') or {}))

		if not response_data.status:
			return {"payment_status": "", "message": str(response)}

		elif response_data.status == "ACCEPTED":
			return {"payment_status": "Initiated", "message": response_data.message}

		elif response_data.status == "Request Failure":
			return {"payment_status": "", "message": "Request Failure"}

		else:
			return {"payment_status": "Failed", "message": response_data.message}
	else:
		return {"payment_status": "", "message": ""}

def get_bank_info(bank_name):
	for bank in STD_BANK_LIST:
		if bank['bank_name'] == bank_name:
			return bank
	return {}

def notify_party(payment_info, response_data):
	frappe.log_error("Payment email triggred")
	if payment_info.payment_entry:
		default_email_format= frappe.get_single("India Banking Settings").default_email_format or "Payment Advice"
		if default_email_format:
			try:
				payment_entry = frappe.get_doc("Payment Entry", payment_info.payment_entry)
				frappe.sendmail(
						recipients=[payment_info.email or frappe.db.get_value('Bank Account', payment_info.bank_account, "email")],
						subject="Payment Notification",
						message="Payment for {0} is completed. Please check the attachment for details".format(payment_info.party),
						attachments=[{"fname": "payment_details.pdf", "fcontent": frappe.get_print("Payment Entry", payment_entry.name, default_email_format, as_pdf=True)}]
					)
			except Exception as e:
				frappe.log_error("Payment Email Notification Failed", frappe.get_traceback())

def get_response(payment_info, company_bank_account, company):
	payment_order_doc = frappe.get_doc("Payment Order", payment_info.parent)

	bank_connector_exists = frappe.db.exists("Bank Connector", {"company": company, "bank_account": company_bank_account})

	if not bank_connector_exists:
		frappe.throw("Bank Connector is not initialized")

	bank_connector = frappe.get_doc("Bank Connector", bank_connector_exists)

	app_name = frappe._dict(get_bank_info(payment_order_doc.company_bank)).app_name

	if bank_connector.bank == "ICICI Bank" and not bank_connector.bulk_transaction:
		app_name += "_composite"

	url = f"{bank_connector.url}/api/method/{app_name}.{app_name}.doctype.bank_request_log.bank_request_log.get_payment_status"

	api_key = bank_connector.api_key
	api_secret = bank_connector.get_password("api_secret")
	headers = {
		"Authorization": f"token {api_key}:{api_secret}",
		"Content-Type": "application/json",
	}

	payment_info_payload = frappe._dict(payment_info.as_dict(convert_dates_to_str=True))

	payment_info_payload.doc = payment_order_doc.as_dict(convert_dates_to_str=True)

	response = requests.request("POST", url, headers=headers, data=json.dumps({"payload": payment_info_payload}))

	#create api request log
	create_api_log(response, 'Get Payment Status', payment_info.parenttype, payment_info.parent)

	if response.status_code == 200:
		response = json.loads(response.text)
		response_data = frappe._dict((response.get('message') or {}))

		if response_data:
			if response_data.status == "Processed":
				if response_data.reference_number:
					frappe.db.set_value("Payment Order Summary", payment_info.name, "reference_number", response_data.reference_number)
					frappe.db.set_value("Payment Entry", payment_info.payment_entry, "reference_no", response_data.reference_number)

					notify_party(payment_info, response_data)

				frappe.db.set_value("Payment Order Summary", payment_info.name, "payment_status", "Processed")

			elif response_data.status == "Pending":
				frappe.db.set_value("Payment Order Summary", payment_info.name, "message", "Payment is pending")
			
			elif response_data.status == "Failed":
				frappe.db.set_value("Payment Order Summary", payment_info.name, "payment_status", response_data.status)
				payment_entry_doc = frappe.get_doc("Payment Entry", payment_info.payment_entry)
				if payment_entry_doc.docstatus == 1:
					payment_entry_doc.cancel()
				process_bank_payment_requests(payment_info.name)
			
			elif response_data.status == "Rejected":
				frappe.db.set_value("Payment Order Summary", payment_info.name, "payment_status", response_data.status)
				payment_entry_doc = frappe.get_doc("Payment Entry", payment_info.payment_entry)
				if payment_entry_doc.docstatus == 1:
					payment_entry_doc.cancel()

				process_bank_payment_requests(payment_info.name)

def process_bank_payment_requests(payment_order_summary):
	pos = frappe.get_doc("Payment Order Summary", payment_order_summary)
	payment_order_doc = frappe.get_doc("Payment Order", pos.parent)

	key = (
		pos.party_type, pos.party, pos.bank_account, pos.account, 
		pos.cost_center, pos.project, pos.tax_withholding_category, 
		pos.reference_doctype
	)

	failed_prs = []
	for ref in payment_order_doc.references:
		ref_key = (
			ref.party_type, ref.party, ref.bank_account, ref.account, 
			ref.cost_center, ref.project, ref.tax_withholding_category, 
			ref.reference_doctype
		)
		if key == ref_key:
			failed_prs.append(ref.bank_payment_request)
	
	for pr in failed_prs:
		pr_doc = frappe.get_doc("Bank Payment Request", pr)
		if pr_doc.docstatus == 1:
			pr_doc.check_if_payment_entry_exists()
			pr_doc.set_as_cancelled()
			pr_doc.db_set("docstatus", 2)
