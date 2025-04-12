# Copyright (c) 2024, Aerele Technologies Private Limited and contributors
# For license information, please see license.txt

import frappe
import requests
import json
from frappe.model.document import Document
from india_banking.india_banking.doctype.india_banking_request_log.india_banking_request_log import (
	create_api_log,
)
from frappe import _


class BankConnector(Document):
	def post_request(self, beneficiary_id, action=None):
		url = f"{self.url}/api/method/india_banking_connector.api.connect"

		payment_payload = frappe._dict(frappe.get_doc("Beneficiary", beneficiary_id).as_dict(convert_dates_to_str=True))

		payment_payload.method = "update_beneficiary_details"
		payment_payload.action = action

		if action != "Submit" and payment_payload.beneficiary_status == "Draft":
			self.post_request(beneficiary_id, action="Submit")

		self.get_payload(payment_payload)

		headers = {
			"Authorization": f"token {self.api_key}:{self.get_password("api_secret")}",
			"Content-Type": "application/json",
		}

		response = requests.request(
			"POST", url, headers=headers, data=json.dumps(payment_payload)
		)

		# create api response log
		create_api_log(
			response, "Update Beneficiary Details", "Beneficiary", beneficiary_id
		)

		if response.ok:
			response_details = response.json().get("message")

			if association_id:= response_details.get("association_id"):
				frappe.db.set_value("Beneficiary", beneficiary_id, "association_id", association_id)
				frappe.db.set_value("Beneficiary", beneficiary_id, "beneficiary_status", "Submitted")
				frappe.msgprint(response_details.get("message"), alert=1, indicator="green")
			elif response_details.get("status") == "success":
				self.update_beneficiary_status(beneficiary_id, action=action)
				frappe.msgprint(response_details.get("message", "Completed"), alert=1, indicator="green")
			else:
				error = response_details.get("error", "")
				if error:
					frappe.throw(_(error), title="Error")
		else:
			frappe.throw(_("Invalid Request"))

	def update_beneficiary_status(self, beneficiary_id, action=None):
		if action == "Update":
			frappe.db.set_value("Beneficiary", beneficiary_id, "beneficiary_status", "Submitted")
		elif action == "Approve":
			frappe.db.set_value("Beneficiary", beneficiary_id, "beneficiary_status", "Approved")
		elif action == "Reject":
			frappe.db.set_value("Beneficiary", beneficiary_id, "beneficiary_status", "Rejected")
		elif action == "Suspend":
			frappe.db.set_value("Beneficiary", beneficiary_id, "beneficiary_status", "Suspended")
		elif action == "Discard":
			frappe.db.delete("Beneficiary", beneficiary_id)
		else:
			frappe.throw(_("Invalid Action"))
		frappe.msgprint(_("Beneficiary Status Updated"), alert=1, indicator="green")

	def get_payload(self, payment_payload):
		#Update the beneficiary bank account details
		payment_payload.update(
			frappe.get_value(
				"Bank Account",
				payment_payload.bank_account,
				[
					"bank_account_no",
					"bank",
					"branch_code",
				],
				as_dict=True
			)
		)

		#Update the connector bank account details
		payment_payload.doc = frappe._dict({})
		payment_payload.doc.update(
			frappe.get_value(
				"Bank Account",
				self.bank_account,
				[
					"name as company_bank_account",
					"bank_account_no as company_account_number",
					"bank as company_bank",
				],
				as_dict=True
			)
		)
