import frappe
from frappe.utils import nowdate
import json
import uuid, requests
import random

@frappe.whitelist()
def make_bank_payment(docname):
	if not frappe.has_permission("Payment Order", "write"):
		frappe.throw("Not permitted", frappe.PermissionError)

	payment_order_doc = frappe.get_doc("Payment Order", docname)
	count = 0
	for i in payment_order_doc.summary:
		if not i.payment_initiated and i.payment_status == "Pending":
			invoices = []
			payment_response = process_payment(i, payment_order_doc.company_bank_account, payment_order_doc.company,  invoices=invoices)
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
				process_payment_requests(i.name)
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


@frappe.whitelist()
def get_payment_status(docname):
	payment_order_doc = frappe.get_doc("Payment Order", docname)
	for i in payment_order_doc.summary:
		if i.payment_status == "Initiated":
			payment_response = get_response(i, payment_order_doc.company_bank_account, payment_order_doc.company)
	payment_order_doc.reload()

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

		if row.tax_withholding_category:
			net_total = 0
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
				if reference.party_type == row.party_type and \
						reference.party == row.party and \
						reference.state == row.state and \
						reference.cost_center == row.cost_center and \
						reference.project == row.project and \
						reference.bank_account == row.bank_account and \
						reference.account == row.account and \
						reference.tax_withholding_category == row.tax_withholding_category and \
						reference.reference_doctype == row.reference_doctype:
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

def process_payment(payment_info, company_bank_account, company, invoices = None):
	# Fetch the connector information
	bank_connector = frappe.get_doc("Bank Connector", {"company": company, "bank_account": company_bank_account})

	if not bank_connector:
		frappe.throw("Bank Connector is not initialized")

	payment_payload = frappe._dict({})

	# Unique reference to this payment.
	payment_payload.name = payment_info.name

	# Party information
	payment_payload.party = payment_info.party
	party_name = ""
	if payment_info.party_type == "Supplier":
		party_name = frappe.db.get_value("Supplier", payment_info.party, "supplier_name")
	payment_payload.party_name = party_name
	payment_payload.desc = f"Payment to {payment_info.party} via {payment_info.parent}"

	# Party's account information
	bank_account_doc = frappe.get_doc("Bank Account", payment_info.bank_account)
	payment_payload.account_number = bank_account_doc.bank_account_no
	payment_payload.ifsc = bank_account_doc.branch_code

	# Payment details
	payment_payload.amount = payment_info.amount
	batch_number = str(random.randint(100,999))
	payment_payload.batch = batch_number + "0" + payment_info.parent[-2:]
	payment_payload.mode_of_transfer = payment_info.mode_of_transfer
	if payment_info.mode_of_transfer == "RTGS" and payment_info.amount >= 500000000:
		lei_number = frappe.db.get_value(payment_info.party_type, payment_info.party, "custom_lei_number")
		if lei_number:
			payment_payload.lei_number = lei_number
		else:
			frappe.throw("LEI Number required for payment > 50 Cr")
	else:
		payment_payload.lei_number = ""

	# Company bank accoount information
	company_bank_account_doc = frappe.get_doc("Bank Account", company_bank_account)
	payment_payload.company_account_number = company_bank_account_doc.bank_account_no
	payment_payload.company_ifsc = company_bank_account_doc.branch_code
	payment_payload.company = company

	if not company_bank_account_doc.bank_account_no:
		frappe.throw("Source bank account number is missing")

	url = f"{bank_connector.url}/api/method/hdfc_integration_server.hdfc_integration_server.doctype.bank_request_log.bank_request_log.make_payment"

	api_key = bank_connector.api_key
	api_secret = bank_connector.get_password("api_secret")
	headers = {
		"Authorization": f"token {api_key}:{api_secret}",
		"Content-Type": "application/json",
	}

	response = requests.request("POST", url, headers=headers, data=json.dumps({"payload": payment_payload}))

	if response.status_code == 200:
		response_data = json.loads(response.text)
		if "message" in response_data and response_data["message"]:
			if "status" in response_data["message"] and response_data["message"]["status"] == "ACCEPTED":
				return {"payment_status": "Initiated", "message": ""}
			else:
				return {"payment_status": "Failed", "message": response_data["message"]["status"]}
	else:
		return {"payment_status": "", "message": ""}

def get_response(payment_info, company_bank_account, company):
	bank_connector = frappe.get_doc("Bank Connector", {"company": company, "bank_account": company_bank_account})

	if not bank_connector:
		frappe.throw("Bank Connector is not initialized")

	url = f"{bank_connector.url}/api/method/hdfc_integration_server.hdfc_integration_server.doctype.bank_request_log.bank_request_log.get_payment_status"

	api_key = bank_connector.api_key
	api_secret = bank_connector.get_password("api_secret")
	headers = {
		"Authorization": f"token {api_key}:{api_secret}",
		"Content-Type": "application/json",
	}

	company_bank_account_doc = frappe.get_doc("Bank Account", company_bank_account)
	batch_number = str(random.randint(100,999))
	payload = {
		"status_payload": {
			"batch": batch_number + "0" + payment_info.parent[-2:],
			"name": payment_info.name,
			"mode_of_transfer": payment_info.mode_of_transfer,
			"payment_date": str(payment_info.payment_date),
			"company_account_number": company_bank_account_doc.bank_account_no
		}
	}

	response = requests.request("POST", url, headers=headers, data=json.dumps(payload))

	if response.status_code == 200:
		response_data = json.loads(response.text)
		if "message" in response_data and response_data["message"]:
			if "status" in response_data["message"] and response_data["message"]["status"] == "Processed":
				if response_data["message"]["reference_number"]:
					frappe.db.set_value("Payment Order Summary", payment_info.name, "reference_number", response_data["message"]["reference_number"])
					frappe.db.set_value("Payment Entry", payment_info.payment_entry, "reference_no", response_data["message"]["reference_number"])
				frappe.db.set_value("Payment Order Summary", payment_info.name, "payment_status", "Processed")
			elif "status" in response_data["message"] and response_data["message"]["status"] == "Failed":
				frappe.db.set_value("Payment Order Summary", payment_info.name, "payment_status", response_data["message"]["status"])
				payment_entry_doc = frappe.get_doc("Payment Entry", payment_info.payment_entry)
				if payment_entry_doc.docstatus == 1:
					payment_entry_doc.cancel()
				process_payment_requests(payment_info.name)
			elif "status" in response_data["message"] and response_data["message"]["status"] == "Rejected":
				frappe.db.set_value("Payment Order Summary", payment_info.name, "payment_status", response_data["message"]["status"])
				payment_entry_doc = frappe.get_doc("Payment Entry", payment_info.payment_entry)
				if payment_entry_doc.docstatus == 1:
					payment_entry_doc.cancel()
				process_payment_requests(payment_info.name)

def process_payment_requests(payment_order_summary):
	pos = frappe.get_doc("Payment Order Summary", payment_order_summary)
	payment_order_doc = frappe.get_doc("Payment Order", pos.parent)

	key = (pos.party_type, pos.party, pos.bank_account, pos.account, pos.state, pos.cost_center, pos.project, pos.tax_withholding_category, pos.reference_doctype)
	failed_prs = []
	for ref in payment_order_doc.references:
		if key == (ref.party_type, ref.party, ref.bank_account, ref.account, ref.state, ref.cost_center, ref.project, ref.tax_withholding_category, ref.reference_doctype):
			failed_prs.append(ref.payment_request)
	
	for pr in failed_prs:
		pr_doc = frappe.get_doc("Payment Request", pr)
		if pr_doc.docstatus == 1:
			pr_doc.check_if_payment_entry_exists()
			pr_doc.set_as_cancelled()
			pr_doc.db_set("docstatus", 2)
