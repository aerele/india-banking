# Copyright (c) 2024, Aerele Technologies Private Limited and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _

OTP_ENABLED_BANK = [
	("ICICI Bank", 1)  # ICICI Bank, Bulk Transaction
]

class BankConnector(Document):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

	def check_permission(self):
		if not frappe.has_permission("Payment Order", "write"):
			frappe.throw(_("Not permitted"), frappe.PermissionError)

	@property
	def headers(self):
		return {
			"Authorization": f"token {self.get_password("api_key")}:{self.get_password("api_secret")}",
			"Content-Type": "application/json",
		}

	@property
	def url(self):
		return f"{self.url}/api/method/india_banking_connector.api.connect"

	def check_otp_enabled(self, otp=None):
		if (self.bank, self.bulk_transaction) in OTP_ENABLED_BANK and otp is None:
			return True
		elif (self.bank, self.bulk_transaction) in OTP_ENABLED_BANK and not otp:
			frappe.throw(_("OTP is required for this transaction"))

	def make_payment(self, payment_order, otp=None):
		payment_order = frappe.get_doc("Payment Order", payment_order)

		if self.check_otp_enabled(otp):
			self.generate_otp(payment_order)


	def generate_otp(self, payment_order):
		payment_order.update_unique_and_file_reference_id(save=True)
		payment_order.reload()

	def make_bulk_payment():
		pass


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

	bank_connector = frappe.get_doc("Bank Connector", bank_connector)


@frappe.whitelist()
def make_payment(payment_order, otp=None):
	payment_order = frappe.get_doc("Payment Order", payment_order)
	bank_connector = get_bank_connector(payment_order.bank_account, payment_order.company)
	bank_connector.make_payment(payment_order, otp)


@frappe.whitelist()
def get_payment_status(payment_order):
	payment_order = frappe.get_doc("Payment Order", payment_order)
	bank_connector = get_bank_connector(payment_order.bank_account, payment_order.company)
	return bank_connector.get_payment_status(payment_order)

