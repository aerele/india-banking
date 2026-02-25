import re

import frappe
import requests
from frappe import _
from frappe.utils import cstr

IFSC_PATTERN = re.compile(r"^[A-Z]{4}0[A-Z0-9]{6}$")
NAME_PATTERN = re.compile(r"^[A-Za-z0-9]+(?: [A-Za-z0-9]+)*$")


def validate(doc, method=None):
	"""Validate Bank Account document before saving"""
	strip_whitespace(doc)
	validate_special_characters(doc)
	validate_ifsc_code(doc)
	validate_unique_acc_no(doc)
	update_party_transaction_currency(doc)

	if (
		(not doc.get_doc_before_save())
		or doc.has_value_changed("branch_code")
		and doc.branch_code
	):
		doc.bank_details_json = get_bank_details_from_branch_code(doc.branch_code)


def validate_unique_acc_no(doc):
	"""Ensure bank account number is unique"""
	# Check if the unique account number validation is enabled
	if not frappe.db.get_single_value(
		"India Banking Settings", "enable_unique_account_no"
	):
		return

	existing_account = frappe.get_all(
		"Bank Account",
		filters={
			"bank_account_no": doc.bank_account_no,
			"name": ["!=", doc.name],
			"disabled": 0,
		},
		limit=1,
	)
	if existing_account:
		frappe.throw(_("Bank Account Number must be unique"))


def strip_whitespace(doc):
	"""Strip leading and trailing whitespace from specified fields"""
	doc.bank_account_no = cstr(doc.bank_account_no).strip()
	doc.branch_code = cstr(doc.branch_code).strip()
	doc.account_name = cstr(doc.account_name).strip()
	doc.mobile_number = cstr(doc.mobile_number).strip()
	doc.email = cstr(doc.email).strip()


def validate_special_characters(doc):
	"""Validate that certain fields do not contain special characters"""
	mandatory_fields = ["account_name", "bank", "bank_account_no"]
	for field in mandatory_fields:
		value = cstr(doc.get(field))
		if not NAME_PATTERN.match(value):
			frappe.throw(
				_("{0} contains invalid characters").format(
					field.replace("_", " ").title()
				)
			)


def validate_ifsc_code(doc):
	"""Validate IFSC/Branch Code format"""
	if not IFSC_PATTERN.match(cstr(doc.branch_code)):
		frappe.throw(_("IFSC/Branch Code is not valid"))


def update_party_transaction_currency(doc):
	"""Set currency based on party or company default currency"""
	if doc.party_type and doc.party:
		currency_field = (
			"salary_currency" if doc.party_type == "Employee" else "default_currency"
		)
		doc.currency = frappe.get_value(
			doc.party_type, doc.party, currency_field
		) or frappe.db.get_value("Company", doc.company, "default_currency")
	elif doc.is_company_account:
		doc.currency = frappe.db.get_value("Company", doc.company, "default_currency")


def get_bank_details_from_branch_code(branch_code):
	url = f"https://ifsc.razorpay.com/{branch_code}"

	try:
		response = requests.get(url)
		bank_details_json = {}
		if response.ok:
			bank_details_json = response.json()

		return bank_details_json

	except Exception:
		frappe.log_error("IFSC Bank Details Fetch Error", frappe.get_traceback())
