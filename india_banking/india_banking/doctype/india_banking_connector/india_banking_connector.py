# Copyright (c) 2024, Aerele Technologies Private Limited and contributors
# For license information, please see license.txt

import ast
import json
import math
import time

import frappe
import requests as request
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, cint, cstr, flt, get_datetime, getdate

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


class IndiaBankingConnector(Document):
	def __init__(self, *args, **kwargs):
		self.success_count = 0
		self.failed_count = 0
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

	def onload(self):
		self.set_onload(
			"connector_installed",
			"india_banking_connector" in frappe.get_installed_apps(),
		)

	def validate(self):
		self.validate_document_series()

		if (
			(not self.get_doc_before_save())
			or self.has_value_changed("auto_post_payments")
			and self.auto_post_payments
		):
			self.update_cron_job()

		self.enable_payment_entry_reposting()

		if not self.notify_party:
			self.payment_notification = []

	def enable_payment_entry_reposting(self):
		if self.auto_update_posting_date_as_payment_date:
			if not frappe.db.exists(
				"Repost Allowed Types",
				{
					"parent": "Repost Accounting Ledger Settings",
					"document_type": "Payment Entry",
					"allowed": 1,
				},
			):
				doc = frappe.get_single("Repost Accounting Ledger Settings")
				doc.append(
					"allowed_types",
					{
						"document_type": "Payment Entry",
						"allowed": 1,
					},
				)
				doc.save()

	def validate_document_series(self):
		if self.doctype_naming_series:
			for series in self.doctype_naming_series:
				if series.series:
					options = frappe.get_meta(series.doctype_name).get_options(
						"naming_series"
					)
					options_list = options.split("\n")
					if options and series.series not in options_list:
						frappe.throw(
							f"You can only select a series that starts with <b>{options_list}</b> at #Row {frappe.bold(series.idx)}"
						)

	def update_cron_job(self):
		self.last_execution = get_datetime()

	def check_otp_enabled(self, otp=None):
		if (self.bank, self.bulk_transaction) in OTP_ENABLED_BANK and otp is None:
			return True
		elif (self.bank, self.bulk_transaction) in OTP_ENABLED_BANK and not otp:
			frappe.throw(_("OTP is required for this transaction"))

	def verify_otp(self, payment_order, otp):
		pass

	def get_payload(self, payment_order, action=None, otp=None):
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
		payment_payload.doc.otp = otp

		return payment_payload

	def get_response_details(self, response):
		try:
			return frappe._dict(response.json().get("message"))
		except Exception:
			frappe.throw(_("Invalid Response: Check API Log"))

	def make_post_request(
		self, payment_order, otp=None, action=None, check_processed_payments=False
	):
		self.check_user_permission()

		if action == "initiate_payment":
			if self.check_otp_enabled(otp):
				return self.generate_otp(payment_order)

		self.action = action

		if otp:
			self.verify_otp(payment_order, otp)

		if self.bulk_transaction:
			url = self.connector_url
			headers = self.headers

			payload = self.get_payload(payment_order, otp=otp)

			response = request.post(url, headers=headers, data=json.dumps(payload))

			# create api request log
			create_api_log(
				response, self.action, payment_order.doctype, payment_order.name
			)

			self.verify_response(response, payment_order)
		else:
			if (
				self.action == "initiate_payment"
				and self.enqueue_large_payments_in_the_background
			):
				if self.add_payment_in_the_background(payment_order):
					return

			last_call = None
			for summary in payment_order.summary:
				if self.action == "initiate_payment":
					last_call = self.check_payment_delay(last_call)
					if summary.payment_initiated or summary.payment_status != "Pending":
						# Ignoring Already initiated Payment
						continue
				elif self.action == "get_payment_status":
					statuses = ["Pending", "Initiated"]
					if check_processed_payments:
						retry_period = cint(
							frappe.db.get_value(
								"India Banking Connector",
								payment_order.company_bank_account,
								"retry_period",
							)
						)
						if summary.payment_date >= add_days(getdate(), -(retry_period)):
							statuses.append("Processed")
					if summary.payment_status not in statuses:
						continue
				self.make_single_request(payment_order, summary)

		if self.action == "initiate_payment":
			msg = _("Payment Initiated")
			if not self.bulk_transaction:
				msg = _("{0} Payment(s) Initiated".format(self.success_count))
			frappe.msgprint(msg)

	def verify_response(self, response, payment_order):
		if self.action == "initiate_payment":
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
						self.success_count += 1

					elif details.get("payment_status", "") == "Failed":
						frappe.db.set_value(
							"Payment Order Summary",
							_name,
							{
								"payment_status": "Failed",
								"payment_initiated": 1,
								"message": details.get("message", ""),
							},
						)
						summary = frappe.get_doc("Payment Order Summary", _name)
						if summary.payment_entry:
							self.process_bank_payment_requests(payment_order, summary)

							payment_entry_doc = frappe.get_doc(
								"Payment Entry", summary.payment_entry
							)
							if payment_entry_doc.docstatus == 1:
								payment_entry_doc.cancel()

						if summary.journal_entry_account:
							frappe.db.set_value(
								"Journal Entry Account",
								summary.journal_entry_account,
								"payment_status",
								"Failed",
							)
						self.failed_count += 1

					elif details.get("payment_status", "") == "Request Failure":
						frappe.db.set_value(
							"Payment Order Summary",
							_name,
							{
								"payment_status": "Pending",
								"message": details.get("message", ""),
							},
						)
						self.failed_count += 1

					else:
						frappe.db.set_value(
							"Payment Order Summary",
							_name,
							{
								"payment_status": "Pending",
								"payment_initiated": 1,
								"message": details.get("message", ""),
							},
						)
						self.failed_count += 1

			elif payment_status == "FAILED":
				frappe.msgprint(
					title=_("Failed"),
					msg=_(message),
					indicator="red",
				)

			else:
				extract_error_message(response.json(), show_message=True)

		else:
			frappe.throw(_("Connection Failed"))

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
						if status_details.utr_number and status_details.status not in [
							"Rejected",
							"Failed",
						]:
							frappe.db.set_value(
								"Payment Order Summary",
								summary.name,
								{
									"reference_number": status_details.utr_number,
									"payment_status": status_details.status,
									"message": status_details.message,
									"payment_initiated": 1,
								},
							)
							if summary.payment_entry:
								frappe.db.set_value(
									"Payment Entry",
									summary.payment_entry,
									{
										"reference_no": status_details.utr_number,
										"reference_date": summary.payment_date,
									},
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

							self._notify_party(summary)

					elif status_details.status == "Pending":
						frappe.db.set_value(
							"Payment Order Summary",
							summary.name,
							{
								"payment_initiated": 1,
								"message": status_details.message,
							},
						)

					elif status_details.status == "Failed":
						frappe.db.set_value(
							"Payment Order Summary",
							summary.name,
							{
								"payment_status": "Failed",
								"payment_initiated": 1,
								"message": status_details.message,
							},
						)

						if summary.payment_entry:
							self.process_bank_payment_requests(payment_order, summary)

							payment_entry_doc = frappe.get_doc(
								"Payment Entry", summary.payment_entry
							)
							if payment_entry_doc.docstatus == 1:
								payment_entry_doc.cancel()

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
								"payment_initiated": 1,
								"message": status_details.message,
							},
						)

						if summary.payment_entry:
							self.process_bank_payment_requests(payment_order, summary)

							payment_entry_doc = frappe.get_doc(
								"Payment Entry", summary.payment_entry
							)
							if payment_entry_doc.docstatus == 1:
								payment_entry_doc.cancel()

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

	def check_payment_delay(self, last_call=None):
		payment_call_interval = (
			self.payment_call_interval
			if self.enable_payment_delay and self.payment_call_interval
			else 0
		)
		if not payment_call_interval:
			# Skip delay validation check
			return None

		payment_delay = 0
		if not last_call:
			last_call = time.time()
		else:
			last_duration_in_seconds = math.ceil(time.time() - last_call)
			payment_delay = payment_call_interval - last_duration_in_seconds
			if payment_delay < 0:
				payment_delay = 0

		if payment_delay:
			# Minimum 1-minute delay to avoid invalid behavior
			payment_delay = 60 if payment_delay > 60 else payment_delay
			time.sleep(payment_delay)
			last_call = time.time()

		return last_call

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
		"""Process payments in the background."""

		pending_payments = []
		for summary in payment_order.summary:
			summary.load_from_db()
			if summary.payment_initiated == 0 and summary.payment_status == "Pending":
				pending_payments.append(summary.name)
		if pending_payments and len(pending_payments) > self.enqueue_payments_threshold:
			payment_order.db_set("enqueue_status", "Queued", update_modified=False)
			error = None
			try:
				frappe.get_doc(
					"Scheduled Job Type",
					{"method": "india_banking.tasks.process_payment_in_the_background"},
				).enqueue(force=True)  # Execute job immediately
			except Exception as e:
				error = e
			if error:
				frappe.throw("Execution Failed", error)
			else:
				frappe.msgprint(
					_(f"{len(pending_payments)} payments added in background")
				)
			return True
		else:
			return False

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
			initiated_count = 0
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
				if status == "Initiated":
					initiated_count += 1

			if initiated_count == len(payment_order.summary):
				frappe.db.set_value(
					"Payment Order", payment_order.name, "status", "Initiated"
				)
			elif success_count == len(payment_order.summary):
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
			elif initiated_count > 0:
				frappe.db.set_value(
					"Payment Order", payment_order.name, "status", "Partially Initiated"
				)
		except Exception:
			frappe.log_error(
				title="Payment Order Status Update Error",
				message=frappe.get_traceback(),
			)

	def _notify_party(self, summary_row):
		if not self.notify_party or not self.payment_notification:
			return

		if summary_row.payment_entry:
			payment_entry = frappe.get_doc("Payment Entry", summary_row.payment_entry)
			notification_details = frappe.get_value(
				"Payment Notification",
				{"company": payment_entry.company},
				["company", "email_format", "letter_head", "cc"],
				as_dict=1,
			)
			if notification_details:
				notification_details = frappe._dict(notification_details)
				try:
					frappe.sendmail(
						recipients=[
							summary_row.email
							or frappe.db.get_value(
								"Bank Account", summary_row.bank_account, "email"
							)
						],
						cc=notification_details.cc,
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
									notification_details.email_format
									or frappe.get_meta(
										"Payment Entry"
									).default_print_format
									or "Payment Advice",
									as_pdf=True,
									letterhead=notification_details.letter_head or None,
								),
							}
						],
					)
				except Exception:
					frappe.log_error(
						"Payment Email Notification Failed", frappe.get_traceback()
					)

	def get_bank_balance(self, bank_account):
		payload = frappe._dict({})
		doc = {
			"company_bank": bank_account.bank,
			"company_account_number": bank_account.bank_account_no,
		}
		payload.doc = doc
		payload.method = "get_bank_balance"
		payload.bulk_transaction = self.bulk_transaction

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

	def process_bank_payment_requests(self, payment_order, summary):
		payment_order.reload()
		summary_references = ast.literal_eval(summary.get("summary_references"))
		for reference in summary_references:
			payment_request = frappe.get_value(
				"Payment Order Reference", reference, "payment_request"
			)
			if payment_request:
				pr_doc = frappe.get_doc("Payment Request", payment_request)
				pr_doc.check_if_payment_entry_exists()
				pr_doc.set_as_cancelled()
				pr_doc.db_set("docstatus", 2)

	def update_bank_transactions(self, statements, bank_account):
		for statement in statements:
			statement = frappe._dict(statement)
			transaction_filter = {
				"bank_account": bank_account.name,
				"reference_number": statement.reference_number,
				"date": getdate(statement.transaction_date),
			}
			if flt(statement.transaction_amount) < 0:
				transaction_filter["withdrawal"] = abs(
					flt(statement.transaction_amount)
				)
			else:
				transaction_filter["deposit"] = abs(flt(statement.transaction_amount))

			# check if bank transaction already exists with same reference number, date and amount
			if not frappe.db.exists("Bank Transaction", transaction_filter):
				bank_transaction_doc = frappe.new_doc("Bank Transaction")
				bank_transaction_doc.company = bank_account.company
				bank_transaction_doc.bank_account = bank_account.name
				bank_transaction_doc.status = "Pending"
				bank_transaction_doc.date = getdate(statement.transaction_date)
				bank_transaction_doc.reference_number = statement.reference_number
				bank_transaction_doc.description = statement.transaction_description
				if flt(statement.transaction_amount) < 0:
					bank_transaction_doc.withdrawal = abs(
						flt(statement.transaction_amount)
					)
				else:
					bank_transaction_doc.deposit = statement.transaction_amount
				bank_transaction_doc.save()

	def get_bank_statement(
		self,
		bank_account,
		from_date=None,
		to_date=None,
		is_paginated=False,
		last_tran_id=None,
	):
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

		response = request.post(
			self.connector_url, headers=self.headers, data=json.dumps(payload)
		)
		# create api request log
		create_api_log(
			response, "Get Bank Statement", "Bank Account", bank_account.bank_account_no
		)

		if response.status_code == 200:
			response_details = self.get_response_details(response)
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


def get_bank_connector(bank_account, company):
	# Fetch the connector information
	bank_connector = frappe.db.exists(
		"India Banking Connector",
		{
			"company": company,
			"bank_account": bank_account,
		},
	)
	if not bank_connector:
		frappe.throw(_("Bank Connector is not initialized"))

	return frappe.get_doc("India Banking Connector", bank_connector)


@frappe.whitelist()
def make_payment(payment_order, otp=None):
	payment_order = frappe.get_doc("Payment Order", payment_order)
	bank_connector = get_bank_connector(
		payment_order.company_bank_account, payment_order.company
	)
	return bank_connector.make_post_request(
		payment_order, otp=otp, action="initiate_payment"
	)


@frappe.whitelist()
def get_payment_status(payment_order, check_processed_payments=False):
	payment_order = frappe.get_doc("Payment Order", payment_order)
	bank_connector = get_bank_connector(
		payment_order.company_bank_account, payment_order.company
	)
	return bank_connector.make_post_request(
		payment_order,
		action="get_payment_status",
		check_processed_payments=check_processed_payments,
	)


@frappe.whitelist()
def get_bank_balance(bank_account_name):
	bank_doc = frappe.get_doc("Bank Account", bank_account_name)
	bank_connector = get_bank_connector(bank_account_name, bank_doc.company)

	if bank_connector.fetch_bank_balance:
		return bank_connector.get_bank_balance(bank_doc)


@frappe.whitelist()
def get_bank_statement(
	bank_account_name,
	from_date=None,
	to_date=None,
	is_paginated=False,
	last_tran_id=None,
):
	bank_doc = frappe.get_doc("Bank Account", bank_account_name)
	bank_connector = get_bank_connector(bank_account_name, bank_doc.company)
	if bank_connector.fetch_bank_statement:
		return bank_connector.get_bank_statement(
			bank_doc,
			from_date=from_date,
			to_date=to_date,
			is_paginated=is_paginated,
			last_tran_id=last_tran_id,
		)
