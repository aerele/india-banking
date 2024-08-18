import frappe
import json
import requests
from frappe.utils import getdate


@frappe.whitelist()
def get_bank_statement(bank_name, from_date=None, to_date= None, is_paginated=False, last_tran_id=None, update=False):
	bank_doc = frappe.get_doc("Bank Account", bank_name)

	bank_connector_exists = frappe.db.exists("Bank Connector", {"company": bank_doc.company, "bank": bank_doc.bank})

	if not bank_connector_exists:
		frappe.throw("Bank Connector is not initialized")

	bank_connector = frappe.get_doc("Bank Connector", bank_connector_exists)

	app_name = frappe._dict(get_bank_info(bank_doc.bank)).app_name

	if bank_connector.bank == "ICICI Bank" and not bank_connector.bulk_transaction:
		app_name += "_composite"

	url = f"{bank_connector.url}/api/method/{app_name}.{app_name}.doctype.bank_request_log.bank_request_log.get_bank_statement"

	paginated_args = {}
	if is_paginated:
		url = f"{bank_connector.url}/api/method/{app_name}.{app_name}.doctype.bank_request_log.bank_request_log.get_bank_statements_paginated"
		paginated_args['conflg'] = 'Y' if not last_tran_id else 'N'
		paginated_args['last_tran_id'] = last_tran_id or ""

	api_key = bank_connector.api_key
	api_secret = bank_connector.get_password("api_secret")
	headers = {
		"Authorization": f"token {api_key}:{api_secret}",
		"Content-Type": "application/json",
	}

	payload = json.dumps({
		"bank_account_number": bank_doc.bank_account_no,
		"from_date": from_date or getdate().strftime("%d-%m-%Y"),
		"to_date": to_date or getdate().strftime("%d-%m-%Y"),
	})

	response = requests.request("POST", url, headers=headers, data= payload)

	#create api request log
	action = "Get Bank Statement" if not is_paginated else "Get Bank Statements Paginated"
	create_api_log(response, action , "Bank Account", bank_doc.name)

	if response.status_code == 200:
		response = json.loads(response.text)
		response_data = frappe._dict((response.get('message') or {}))
		if response_data.get('server_status') == "Success":
			if response_data.bank_statements and update:
				update_bank_transactions(bank_doc, response_data.bank_statements)
			if update:
				return response_data.bank_statements
		else:
			frappe.msgprint(title= "API Failed", msg=action + " Failed", indicator='red')



def update_bank_transactions(bank_doc, statements):
	for statement in statements:
		if not frappe.db.exists("Bank Transaction", {"bank_account": bank_doc.name, "reference_number": statement.transaction_id}):
			bank_transaction_doc = frappe.new_doc("Bank Transaction")
			bank_transaction_doc.update(statement)
			bank_transaction_doc.save()
