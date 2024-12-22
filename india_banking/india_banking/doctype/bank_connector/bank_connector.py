# Copyright (c) 2024, Aerele Technologies Private Limited and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import comma_and, cstr, get_link_to_form, getdate
from requests import request

from india_banking.india_banking.doctype.india_banking_request_log.india_banking_request_log import (
	create_api_log,
)
from india_banking.utils import get_bank_address_details

OTP_ENABLED_BANK = [
	("ICICI Bank", 1),  # ICICI Bank, Bulk Transaction
]


class BankConnector(Document):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

	def check_user_permission(self):
		if not frappe.has_permission("Payment Order", "write"):
			frappe.throw(_("Not permitted"), frappe.PermissionError)

	@property
	def headers(self):
		return {
			"Authorization": f"token {self.get_password("api_key")}:{self.get_password("api_secret")}",
			"Content-Type": "application/json",
		}

	@property
	def base_url(self):
		return f"{self.url}/api/method/india_banking_connector.api.connect"

	def check_otp_enabled(self, otp=None):
		if (self.bank, self.bulk_transaction) in OTP_ENABLED_BANK and otp is None:
			return True
		elif (self.bank, self.bulk_transaction) in OTP_ENABLED_BANK and not otp:
			frappe.throw(_("OTP is required for this transaction"))

	def make_payment(self, payment_order, otp=None):
		payment_order = frappe.get_doc("Payment Order", payment_order)

		if self.check_otp_enabled(otp):
			return self.generate_otp(payment_order)

		if otp:
			self.verify_otp(payment_order, otp)

		# Make the payment
		if self.bulk_transaction:
			return self.make_bulk_payment(payment_order, otp)
		else:
			return self.make_single_payment(payment_order)

	def make_single_payment(self, payment_order):
		count = 0
		for payment_row in payment_order.summary:
			if (
				not payment_row.payment_initiated
				and payment_row.payment_status == "Pending"
			):
				# handle failed or success response
				payment_response = self.process_payment_and_response(
					payment_row, payment_order
				)

				if (
					payment_response
					and "payment_status" in payment_response
					and payment_response["payment_status"] == "Initiated"
				):
					frappe.db.set_value(
						"Payment Order Summary",
						payment_row.name,
						{
							"payment_status": "Initiated",
							"payment_date": getdate(),
							"payment_initiated": 1,
						},
					)
					count += 1

				elif (
					payment_response
					and "payment_status" in payment_response
					and payment_response["payment_status"] == ""
				):
					if "message" in payment_response:
						frappe.db.set_value(
							"Payment Order Summary",
							payment_row.name,
							"message",
							payment_response.message,
						)
				else:
					frappe.db.set_value(
						"Payment Order Summary",
						payment_row.name,
						"payment_status",
						"Failed",
					)
					payment_entry = frappe.get_doc(
						"Payment Entry", payment_row.payment_entry
					)
					if payment_entry.docstatus == 1:
						payment_entry.cancel()

					self.process_bank_payment_requests(payment_order, payment_row)

					if payment_response and "message" in payment_response:
						frappe.db.set_value(
							"Payment Order Summary",
							payment_row.name,
							"message",
							payment_response.message,
						)

		payment_order.reload()
		processed_count = 0
		for row in payment_order.summary:
			if row.payment_initiated:
				processed_count += 1

		if processed_count == len(payment_order.summary):
			frappe.db.set_value(
				"Payment Order", payment_order.name, "status", "Initiated"
			)

		return {"message": f"{count} payments initiated"}

	def process_payment_and_response(self, payment_row, payment_order):
		payment_payload = self.get_payload(payment_order, "make_payment")
		payment_payload.update(payment_row.as_dict(convert_dates_to_str=True))
		party_field_name = (
			"supplier_name" if payment_row.party_type == "Supplier" else "employee_name"
		)

		party_name = frappe.db.get_value(
			payment_row.party_type, payment_row.party, party_field_name
		)

		payment_payload.party_name = party_name
		payment_payload.desc = (
			f"Payment to {payment_row.party} via {payment_row.parent}"
		)

		party_address = get_bank_address_details(payment_row.bank_account)
		bank_link = get_link_to_form("Bank Account", payment_row.bank_account)
		if not party_address:
			frappe.throw(
				f"Address not found for the selected bank account {bank_link} at <b>Row #{payment_row.idx}</b>"
			)

		payment_payload.address = json.dumps(party_address)

		response = request.post(
			self.base_url, headers=self.headers, data=json.dumps(payment_payload)
		)

		# create api request log
		create_api_log(
			response, "Make Payment", payment_order.doctype, payment_order.name
		)

		if response.status_code == 200:
			payment_response = self.get_response_details(response)

			if not payment_response.status:
				return {"payment_status": "", "message": str(response)}

			elif payment_response.status == "ACCEPTED":
				return {
					"payment_status": "Initiated",
					"message": payment_response.message,
				}

			elif payment_response.status == "Request Failure":
				return {"payment_status": "", "message": "Request Failure"}

			else:
				return {"payment_status": "Failed", "message": payment_response.message}
		else:
			return {"payment_status": "", "message": "Bad Request"}

	def process_bank_payment_requests(self, payment_order, payment_row):
		key = (
			payment_row.party_type,
			payment_row.party,
			payment_row.bank_account,
			payment_row.account,
			payment_row.cost_center,
			payment_row.project,
			payment_row.tax_withholding_category,
			payment_row.reference_doctype,
		)

		failed_prs = []
		for ref in payment_order.references:
			ref_key = (
				ref.party_type,
				ref.party,
				ref.bank_account,
				ref.account,
				ref.cost_center,
				ref.project,
				ref.tax_withholding_category,
				ref.reference_doctype,
			)
			if key == ref_key:
				failed_prs.append(ref.payment_request)

		for pr in failed_prs:
			pr_doc = frappe.get_doc("Payment Request", pr)
			if pr_doc.docstatus == 1:
				pr_doc.check_if_payment_entry_exists()
				pr_doc.set_as_cancelled()
				pr_doc.db_set("docstatus", 2)

	def make_bulk_payment(self, payment_order, otp):
		payment_payload = self.get_payload(payment_order, "make_payment")
		payment_payload.doc.update({"otp": otp})

		payment_account_list = []

		# Lei number validation
		for ref in payment_order.summary:
			if ref.mode_of_transfer == "RTGS" and ref.amount >= 500000000:
				lei_number = frappe.db.get_value(
					ref.party_type, ref.party, "lei_number"
				)
				payment_account_list.append(ref.account_name + "-" + lei_number)
				if not lei_number:
					frappe.throw("LEI Number required for payment > 50 Cr")
			else:
				payment_account_list.append(
					ref.account_name + "-" + ref.bank_account_no
				)

		payment_payload.doc.update(
			{
				"desc": f"Payment to {comma_and(payment_account_list)} via {payment_order.name}"
			}
		)

		response = request.post(
			self.base_url, headers=self.headers, data=json.dumps(payment_payload)
		)

		# create api request log
		create_api_log(
			response, "Make Payment", payment_order.doctype, payment_order.name
		)

		# handle failed or success response
		return self.process_bulk_payment_response(response, payment_order)

	def process_bulk_payment_response(self, response, payment_order):
		payment_response = self.get_response_details(response)
		if payment_response.get("status", "") == "ACCEPTED":
			frappe.db.set_value(
				"Payment Order", payment_order.name, "status", "Initiated"
			)
			frappe.db.set_value(
				"Payment Order",
				payment_order.name,
				"file_sequence_number",
				payment_response.get("file_sequence_number"),
			)

			for row in payment_order.summary:
				frappe.db.set_value(
					"Payment Order Summary",
					row.name,
					{
						"payment_status": "Initiated",
						"payment_date": getdate(),
						"payment_initiated": 1,
					},
				)

			return {"message": "Payment Initiated"}

		elif payment_response.get("status", "") == "Failed":
			return {"message": "Failed - " + cstr(payment_response.get("message"))}

		else:
			frappe.throw(_("Invalid Response: Check API Log"))

	def verify_otp(self, payment_order, otp):
		pass

	def generate_otp(self, payment_order):
		payment_order.update_unique_and_file_reference_id(save=True)
		payment_order.reload()

		# Generate OTP using POST request
		response = request.post(
			self.base_url,
			headers=self.headers,
			data=json.dumps(self.get_payload(payment_order, "generate_otp")),
		)

		# create api response log
		create_api_log(
			response, "Generate Otp", payment_order.doctype, payment_order.name
		)
		# handle failed or success response
		return self.handle_otp_response(response)

	def get_response_details(self, response):
		try:
			return frappe._dict(response.json().get("message"))
		except:
			frappe.throw(_("Invalid Response: Check API Log"))

	def handle_otp_response(self, response):
		if response.ok:
			response_details = self.get_response_details(response)
			if response_details.status == "success":
				return {"otp_required": True}
			else:
				frappe.throw(msg=_(cstr(response_details.message)), title=_("Failed"))
		else:
			frappe.throw(
				title=cstr(response.status_code),
				msg=_("Invalid Request: Check API Log"),
			)

	def get_payload(self, payment_order, action):
		payment_payload = frappe._dict()
		payment_payload.doc = payment_order.as_dict(convert_dates_to_str=True)
		payment_payload.method = action
		payment_payload.bulk_transaction = self.bulk_transaction
		return payment_payload

	def update_payment_status(self, payment_order):
		try:
			success_count = 0
			faild_count = 0
			rejected_count = 0
			for ref in payment_order.summary:
				status = frappe.db.get_value(
					"Payment Order Summary", ref.name, "payment_status"
				)
				if status == "Processed":
					success_count += 1
				if status == "Failed":
					faild_count += 1
				if status == "Rejected":
					rejected_count += 1

			if success_count == len(payment_order.summary):
				frappe.db.set_value(
					"Payment Order", payment_order.name, "status", "Approved"
				)

			elif faild_count == len(payment_order.summary):
				frappe.db.set_value(
					"Payment Order", payment_order.name, "status", "Failed"
				)
			elif rejected_count == len(payment_order.summary):
				frappe.db.set_value(
					"Payment Order", payment_order.name, "status", "Rejected"
				)
			elif (
				success_count > 1
				and success_count + faild_count + rejected_count
				== len(payment_order.summary)
			):
				frappe.db.set_value(
					"Payment Order", payment_order.name, "status", "Partially Approved"
				)
		except:
			frappe.log_error(
				title="Payment Order Status Update Error",
				message=frappe.get_traceback(),
			)


def get_bank_connector(bank_account, company):
	# Fetch the connector information
	bank_connector = frappe.db.exists(
		"Bank Connector",
		{
			"company": company,
			"bank_account": bank_account,
		},
	)
	if not bank_connector:
		frappe.throw("Bank Connector is not initialized")

	return frappe.get_doc("Bank Connector", bank_connector)


@frappe.whitelist()
def make_payment(payment_order, otp=None):
	payment_order = frappe.get_doc("Payment Order", payment_order)
	bank_connector = get_bank_connector(
		payment_order.company_bank_account, payment_order.company
	)
	return bank_connector.make_payment(payment_order, otp)


@frappe.whitelist()
def get_payment_status(payment_order):
	payment_order = frappe.get_doc("Payment Order", payment_order)
	bank_connector = get_bank_connector(
		payment_order.company_bank_account, payment_order.company
	)
	return bank_connector.get_payment_status(payment_order)
