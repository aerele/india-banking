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
from frappe.utils import add_days, getdate


class BankConnector(Document):
	@property
	def header(self):
		return {
			"Authorization": f"token {self.api_key}:{self.get_password("api_secret")}",
			"Content-Type": "application/json",
		}

	def post_request(self, beneficiary_id, action=None):
		url = f"{self.url}/api/method/india_banking_connector.api.connect"

		payment_payload = frappe._dict(frappe.get_doc("Beneficiary", beneficiary_id).as_dict(convert_dates_to_str=True))

		payment_payload.method = "update_beneficiary_details"

		if action != "Submit" and payment_payload.beneficiary_status == "Draft":
			return self.post_request(beneficiary_id, action="Submit")

		self.get_payload(payment_payload)
		payment_payload.action = action

		response = requests.request(
			"POST", url, headers=self.header, data=json.dumps(payment_payload)
		)

		# create api response log
		create_api_log(
			response, "Update Beneficiary Details", "Beneficiary", beneficiary_id
		)

		if response.ok:
			response_details = response.json().get("message")

			if response_details.get("status") == "success" and (association_id:= response_details.get("association_id")):
				frappe.db.set_value("Beneficiary", beneficiary_id, "association_id", association_id)
				frappe.db.set_value("Beneficiary", beneficiary_id, "beneficiary_status", "Submitted")
				frappe.msgprint(response_details.get("message"), alert=1, indicator="green")
			elif response_details.get("status") == "success":
				self.update_beneficiary_status(beneficiary_id, action=action)
				frappe.msgprint(response_details.get("message", "Completed"), alert=1, indicator="green")
			elif response_details.get("status") == "Request Failure":
				frappe.throw(
					response_details.get("message", "Request Failed")
				)
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
			frappe.db.set_value("Beneficiary", beneficiary_id, {
				"beneficiary_status": "Discarded",
				"docstatus": 2,
			})
			bank_account = frappe.get_value("Beneficiary", beneficiary_id, "bank_account")
			if bank_account:
				frappe.db.set_value("Bank Account", bank_account, {
					"beneficiary": "",
					"workflow_state": "Pending",
				})
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

	@frappe.whitelist()
	def get_bank_statements(
		self,
		bank_account=None,
		from_date=None,
		to_date=None,
		is_paginated=False,
		last_tran_id=None,
	):
		url = f"{self.url}/api/method/india_banking_connector.api.connect"
		bank_account = frappe.get_doc("Bank Account", bank_account or self.bank_account)
		payload = frappe._dict({})
		doc = {
			"company_account_number": bank_account.bank_account_no,
			"company_bank": bank_account.bank,
			"from_date": from_date or add_days(getdate(), -1).strftime("%d-%m-%Y"),
			"to_date": to_date or getdate().strftime("%d-%m-%Y"),
			"paginated": is_paginated,
			"last_transaction_id": last_tran_id,
		}
		payload.doc = doc
		payload.method = "get_bank_statement"
		payload.bulk_transaction = self.bulk_transaction

		response = requests.post(
			url, headers=self.header, data=json.dumps(payload)
		)
		# create api request log
		create_api_log(
			response, "Get Bank Statement", "Bank Account", bank_account.bank_account_no
		)

		if response.status_code == 200:
			response_details = response.json().get("message")
			if response_details.get("server_status") == "Success":
				bank_statements = response_details.get("bank_statements", [])
				if bank_statements:
					if len(bank_statements) > 50:
						frappe.enqueue(
							self.update_bank_transactions,
							queue="long",
							enqueue_after_commit=True,
							statements=bank_statements,
							bank_account=bank_account,
						)
						frappe.msgprint(
							_("Transactions are being updated in the background.")
						)
					else:
						self.update_bank_transactions(
							bank_statements, bank_account=bank_account
						)
						frappe.msgprint(_("The transactions are being updated."))
		else:
			frappe.msgprint(
				title=_("API Failed"),
				msg=_("Statement Fetch Failed"),
				indicator="red",
			)

	def update_bank_transactions(self, statements, bank_account):
		for statement in statements:
			statement = frappe._dict(statement)
			if not frappe.db.exists(
				"Bank Transaction",
				{
					"bank_account": bank_account.name,
					"reference_number": statement.reference_number,
				},
			):
				bank_transaction_doc = frappe.new_doc("Bank Transaction")
				bank_transaction_doc.company = bank_account.company
				bank_transaction_doc.bank_account = bank_account.name
				bank_transaction_doc.status = "Pending"
				bank_transaction_doc.date = getdate(statement.transaction_date)
				bank_transaction_doc.withdrawal = statement.transaction_amount
				bank_transaction_doc.reference_number = statement.reference_number
				bank_transaction_doc.save()

@frappe.whitelist()
def get_bank_statements(
	bank_account=None,
	from_date=None,
	to_date=None,
	is_paginated=False,
	last_tran_id=None,
):
	"""Get bank statements from the connector"""
	bank_connector = frappe.get_doc("Bank Connector", bank_account)
	bank_connector.get_bank_statements(
		bank_account=bank_account,
		from_date=from_date,
		to_date=to_date,
		is_paginated=is_paginated,
		last_tran_id=last_tran_id,
	)