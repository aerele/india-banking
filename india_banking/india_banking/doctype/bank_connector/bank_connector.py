# Copyright (c) 2024, Aerele Technologies Private Limited and contributors
# For license information, please see license.txt

import frappe
import requests
import json
from frappe.model.document import Document
from india_banking.india_banking.doctype.india_banking_request_log.india_banking_request_log import (
	create_api_log,
)


class BankConnector(Document):
	def post_request(self, bank_account_doc, action=None):
		url = f"{self.url}/api/method/india_banking_connector.api.connect"
		
		payment_payload = frappe._dict({})

		payment_payload.method = "update_benificery_details"
		payment_payload.doc = bank_account_doc.as_dict()
		payment_payload.doc.action = action

		api_key = self.api_key
		api_secret = self.get_password("api_secret")
		headers = {
			"Authorization": f"token {api_key}:{api_secret}",
			"Content-Type": "application/json",
		}
		response = requests.request(
			"POST", url, headers=headers, data=json.dumps(payment_payload)
		)

		# create api response log
		create_api_log(
			response, "Update Benificery Details", bank_account_doc.doctype, bank_account_doc.name
		)

		if response.ok:
			response_details = response.json().get("message")
			if association_id:= response_details.get("association_id"):
				frappe.db.set_value("Bank Account", bank_account_doc.name, "association_id", association_id)
			elif response_details.get("status") == "success":
				frappe.msgprint(response_details.get("message"), alert=1, indicator="green")
			else:
				frappe.msgprint(response_details.get("message"), alert=1, indicator="red")
		else:
			frappe.throw("Invalid Request")


@frappe.whitelist()
def update_benificery_details(bank_account, action=None):
	bank_account_doc = frappe.get_doc("Bank Account", bank_account)

	bank_connector_exists = frappe.db.exists(
		"Bank Connector", {"company": bank_account_doc.company, "bank": bank_account_doc.bank}
	)

	bank_connector = frappe.get_doc("Bank Connector", bank_connector_exists)

	bank_connector.post_request(bank_account_doc, action)