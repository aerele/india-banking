# Copyright (c) 2024, Aerele Technologies Private Limited and contributors
# For license information, please see license.txt

import json
import re

import frappe
import requests as request
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, cstr, getdate
from frappe.utils.background_jobs import is_job_enqueued

from india_banking.india_banking.doctype.india_banking_request_log.india_banking_request_log import (
	create_api_log,
)
from india_banking.utils import (
	extract_error_message,
	get_bank_address_details,
	get_party_field_name,
)

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
			"Authorization": f"token {self.get_password('api_key')}:{self.get_password('api_secret')}",
			"Content-Type": "application/json",
		}

	@property
	def connector_url(self):
		return f"{self.url}/api/method/india_banking_connector.api.connect"

	def check_otp_enabled(self, otp=None):
		if (self.bank, self.bulk_transaction) in OTP_ENABLED_BANK and otp is None:
			return True
		elif (self.bank, self.bulk_transaction) in OTP_ENABLED_BANK and not otp:
			frappe.throw(_("OTP is required for this transaction"))

	def verify_otp(self, payment_order, otp):
		pass

	def get_payload(self, payment_order, action=None):
		bank_account = frappe.get_doc(
			"Bank Account", payment_order.company_bank_account
		)
		payment_payload = frappe._dict()
		payment_payload.doc = payment_order.as_dict(convert_dates_to_str=True)
		payment_payload.doc.update(
			{
				"company_account_number": bank_account.bank_account_no,
				"company_bank_account_name": bank_account.account_name,
				"company_ifsc": bank_account.branch_code,
				"mobile_number": bank_account.mobile_number,
			}
		)
		payment_payload.method = self.get("action", "") or action
		payment_payload.bulk_transaction = self.bulk_transaction

		return payment_payload

	def get_response_details(self, response):
		try:
			return frappe._dict(response.json().get("message"))
		except Exception:
			frappe.throw(_("Invalid Response: Check API Log"))

	def make_post_request(self, payment_order, otp=None, action=None):
		self.check_user_permission()

		if action == "intiate_payment":
			if self.check_otp_enabled(otp):
				return self.generate_otp(payment_order)

			action = "get_payment_status"
			self.make_post_request(payment_order, otp, action)
			action = "intiate_payment"

		self.action = action

		if otp:
			self.verify_otp(payment_order, otp)

		if self.bulk_transaction:
			url = self.connector_url
			headers = self.headers

			payload = self.get_payload(payment_order)

			response = request.post(url, headers=headers, data=json.dumps(payload))

			# create api request log
			create_api_log(
				response, self.action, payment_order.doctype, payment_order.name
			)

			self.verify_response(response, payment_order)
		else:
			# add payment in background
			if len(payment_order.summary) > 10 or cint(
				frappe.get_single(
					"India Banking Settings"
				).enable_payment_in_the_background
			):
				return self.add_payment_in_the_background(payment_order)

			for summary in payment_order.summary:
				if (
					not summary.payment_initiated
					and summary.payment_status != "Pending"
				):
					continue

				self.make_single_request(payment_order, summary)

	def verify_response(self, response, payment_order):
		if self.action == "intiate_payment":
			self.verify_payment_response(response, payment_order)
		elif self.action == "get_payment_status":
			self.verify_status_response(response, payment_order)

		self.update_payment_status(payment_order)

	def verify_payment_response(self, response, payment_order):
		payment_response = self.get_response_details(response)

		if response.ok:
			payment_status = payment_response.get("payment_status", "")
			message = payment_response.get("message", "")

			file_sequence_number = payment_response.get("file_sequence_number", "")

			summary_details = frappe._dict(payment_response.get("summary_details", {}))

			if payment_status == "ACCEPTED":
				if self.bulk_transaction:
					frappe.db.set_value(
						"Payment Order",
						payment_order.name,
						{
							"status": "Initiated",
							"file_sequence_number": file_sequence_number,
						},
					)

				for _name, details in summary_details.items():
					if details.get("payment_status", "") == "Accepted":
						frappe.db.set_value(
							"Payment Order Summary",
							_name,
							{
								"payment_status": "Initiated",
								"payment_date": getdate(),
								"payment_initiated": 1,
								"message": details.get("message", ""),
							},
						)
					elif details.get("payment_status", "") == "Failed":
						frappe.db.set_value(
							"Payment Order Summary",
							_name,
							{
								"payment_status": "Pending",
								"payment_initiated": 1,
								"message": details.get("message", ""),
							},
						)
					elif details.get("payment_status", "") == "Request Failure":
						frappe.db.set_value(
							"Payment Order Summary",
							_name,
							{
								"payment_status": "Pending",
								"message": details.get("message", ""),
							},
						)
					else:
						frappe.db.set_value(
							"Payment Order Summary",
							_name,
							{
								"payment_status": "Failed",
								"payment_initiated": 1,
								"message": details.get("message", ""),
							},
						)

			elif payment_status == "FAILED":
				frappe.msgprint(
					title=_("Failed"),
					msg=_(message),
					indicator="red",
				)

			else:
				extract_error_message(response.json(), show_message=True)

		else:
			frappe.throw("Connection Request")

	def verify_status_response(self, response, payment_order):
		payment_response = self.get_response_details(response)

		if response.ok:
			payment_status = payment_response.get("payment_status", "")
			message = payment_response.get("message", "")

			summary_details = frappe._dict(payment_response.get("summary_details", {}))

			if payment_status == "PROCESSED":
				for summary in payment_order.summary:
					status_details = frappe._dict(summary_details.get(summary.name, ""))
					if status_details.status == "Processed":
						if status_details.utr_number:
							frappe.db.set_value(
								"Payment Order Summary",
								summary.name,
								"reference_number",
								status_details.utr_number,
							)
							if summary.payment_entry:
								frappe.db.set_value(
									"Payment Entry",
									summary.payment_entry,
									"reference_no",
									status_details.utr_number,
								)
							if summary.journal_entry_account:
								frappe.db.set_value(
									"Journal Entry Account",
									summary.journal_entry_account,
									{
										"payment_status": "Paid",
										"reference_number": status_details.utr_number,
									},
								)

							self.notify_party(summary)

						frappe.db.set_value(
							"Payment Order Summary",
							summary.name,
							"payment_status",
							"Processed",
						)
					elif status_details.status == "Pending":
						frappe.db.set_value(
							"Payment Order Summary",
							summary.name,
							"message",
							status_details.message,
						)

					elif status_details.status == "Failed":
						frappe.db.set_value(
							"Payment Order Summary",
							summary.name,
							{
								"payment_status": status_details.status,
								"message": status_details.message,
							},
						)

						if summary.payment_entry:
							payment_entry_doc = frappe.get_doc(
								"Payment Entry", summary.payment_entry
							)
							if payment_entry_doc.docstatus == 1:
								payment_entry_doc.cancel()
							self.process_bank_payment_requests(payment_order, summary)

						if summary.journal_entry_account:
							frappe.db.set_value(
								"Journal Entry Account",
								summary.journal_entry_account,
								"payment_status",
								"Failed",
							)

					elif status_details.status == "Rejected":
						frappe.db.set_value(
							"Payment Order Summary",
							summary.name,
							{
								"payment_status": status_details.status,
								"message": status_details.message,
							},
						)

						if summary.payment_entry:
							payment_entry_doc = frappe.get_doc(
								"Payment Entry", summary.payment_entry
							)
							if payment_entry_doc.docstatus == 1:
								payment_entry_doc.cancel()

							self.process_bank_payment_requests(payment_order, summary)

						if summary.journal_entry_account:
							frappe.db.set_value(
								"Journal Entry Account",
								summary.journal_entry_account,
								"payment_status",
								"Failed",
							)

			elif payment_status == "FAILED":
				frappe.msgprint(
					title=_("Failed"),
					msg=_(message),
					indicator="red",
				)

			else:
				extract_error_message(response.json())

		else:
			frappe.throw("Invalid Request")

	def make_single_request(self, payment_order, summary):
		url = self.connector_url
		headers = self.headers

		payload = self.get_payload(payment_order)
		payload.update(summary.as_dict(convert_dates_to_str=True))
		payload.party_name = frappe.db.get_value(
			summary.party_type, summary.party, get_party_field_name(summary.party_type)
		)
		payload.address = json.dumps(get_bank_address_details(summary.bank_account))

		response = request.post(url, headers=headers, data=json.dumps(payload))

		# create api request log
		create_api_log(response, self.action, payment_order.doctype, payment_order.name)

		self.verify_response(response, payment_order)

	def add_payment_in_the_background(self, payment_order):
		def _add_queue(summary, job_id):
			frappe.enqueue(
				self.make_single_request,
				payment_order=payment_order,
				summary=summary,
				job_id=job_id,
				job_name=f"Make Payment {job_id}",
				enqueue_after_commit=True,
			)

		enqueue_count = 0
		for summary in payment_order.summary:
			if (
				self.action == "initiate_payment"
				and not summary.payment_initiated
				and summary.payment_status != "Pending"
			):
				continue
			if self.action == "get_payment_status" and summary.payment_status not in [
				"Pending",
				"Initiated",
			]:
				continue
			job_id = (
				"".join(re.findall(r"[0-9a-zA-Z]", self.name))[-10:]
				+ "-"
				+ summary.name
			)
			if not frappe.db.exists("RQ Job", job_id):
				_add_queue(summary=summary, job_id=job_id)
				enqueue_count += 1

			elif (rq_job := frappe.db.exists("RQ Job", job_id)) and not is_job_enqueued(
				job_id
			):
				frappe.get_doc("RQ Job", rq_job).delete()
				frappe.clear_cache(doctype="RQ Job")
				_add_queue(summary=summary, job_id=job_id)
				enqueue_count += 1

		frappe.msgprint(_(f"{enqueue_count} payments added in background"))

	def generate_otp(self, payment_order):
		payment_order.reload()

		# Generate OTP using POST request
		response = request.post(
			self.connector_url,
			headers=self.headers,
			data=json.dumps(self.get_payload(payment_order, "generate_otp")),
		)

		# create api response log
		create_api_log(
			response, "Generate Otp", payment_order.doctype, payment_order.name
		)
		# handle failed or success response
		return self.handle_otp_response(response)

	def handle_otp_response(self, response):
		if response.ok:
			response_details = self.get_response_details(response)
			if response_details.status == "success":
				return {"otp_required": True}
			else:
				frappe.throw(
					title=_("Invalid Request"),
					msg=_("OTP Initiation Failed: Check API Log"),
				)
		else:
			frappe.throw(
				title=cstr(response.status_code),
				msg=_("Invalid Request: Check API Log"),
			)

	def update_payment_status(self, payment_order):
		payment_order.reload()

		try:
			success_count = 0
			faild_count = 0
			rejected_count = 0
			for summary in payment_order.summary:
				status = frappe.db.get_value(
					"Payment Order Summary", summary.name, "payment_status"
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
		except Exception:
			frappe.log_error(
				title="Payment Order Status Update Error",
				message=frappe.get_traceback(),
			)

	def notify_party(self, summary_row):
		if not frappe.get_value(
			"India Banking Settings", "India Banking Settings", "notify_party"
		):
			return
		if summary_row.payment_entry:
			default_email_format = (
				frappe.get_single("India Banking Settings").default_email_format
				or "Payment Advice"
			)
			if default_email_format:
				try:
					payment_entry = frappe.get_doc(
						"Payment Entry", summary_row.payment_entry
					)
					frappe.sendmail(
						recipients=[
							summary_row.email
							or frappe.db.get_value(
								"Bank Account", summary_row.bank_account, "email"
							)
						],
						subject="Payment Notification",
						message="Payment for {0} is completed. Please check the attachment for details".format(
							summary_row.party
						),
						attachments=[
							{
								"fname": "payment_details.pdf",
								"fcontent": frappe.get_print(
									"Payment Entry",
									payment_entry.name,
									default_email_format,
									as_pdf=True,
								),
							}
						],
					)
				except Exception:
					frappe.log_error(
						"Payment Email Notification Failed", frappe.get_traceback()
					)

	def get_bank_balance(self, bank_account):
		payload = {
			"bank_account_number": bank_account.bank_account_no,
			"method": "get_bank_balance",
		}
		response = request.post(
			self.connector_url, headers=self.headers, data=json.dumps(payload)
		)
		# create api request log
		create_api_log(
			response, "Get Bank Balance", "Bank Account", bank_account.bank_account_no
		)

		if response.status_code == 200:
			response_details = self.get_response_details(response)
			if response_details.get("server_status") == "Success":
				if response_details.balance or response_details.balance == 0:
					frappe.db.set_value(
						"Bank Account",
						bank_account.name,
						"bank_balance",
						response_details.balance,
					)
			else:
				frappe.msgprint(
					title=_("API Failed"),
					msg=_("Balance Fetch Failed"),
					indicator="red",
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
		frappe.throw(_("Bank Connector is not initialized"))

	return frappe.get_doc("Bank Connector", bank_connector)


@frappe.whitelist()
def make_payment(payment_order, otp=None):
	payment_order = frappe.get_doc("Payment Order", payment_order)
	bank_connector = get_bank_connector(
		payment_order.company_bank_account, payment_order.company
	)
	return bank_connector.make_post_request(
		payment_order, otp=otp, action="intiate_payment"
	)


@frappe.whitelist()
def get_payment_status(payment_order):
	payment_order = frappe.get_doc("Payment Order", payment_order)
	bank_connector = get_bank_connector(
		payment_order.company_bank_account, payment_order.company
	)
	return bank_connector.make_post_request(payment_order, action="get_payment_status")


@frappe.whitelist()
def get_bank_balance(bank_account_name):
	bank_doc = frappe.get_doc("Bank Account", bank_account_name)
	bank_connector = get_bank_connector(bank_account_name, bank_doc.company)
	return bank_connector.get_bank_balance(bank_doc)
