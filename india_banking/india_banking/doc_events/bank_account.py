import re

import frappe
from frappe import _
from frappe.utils import cstr

IFSC_PATTERN = re.compile(r"^[A-Z]{4}0[A-Z0-9]{6}$")
IBAN_PATTERN = re.compile(r"^[A-Z]{2}[0-9]{2}[A-Z0-9]{1,30}$")
SWIFT_PATTERN = re.compile(r"^[A-Z]{4}[A-Z0-9]{2}[A-Z0-9]{2}([A-Z0-9]{3})?$")


def validate(doc, method=None):
	update_transaction_currency(doc)
	if not doc.currency:
		frappe.throw(_("Currency is required for the Bank transaction."))

	if doc.currency == "INR":
		if not doc.bank_account_no:
			frappe.throw(_("Bank Account Number is required for INR transactions."))
		if not doc.branch_code:
			frappe.throw(_("IFSC/Branch Code is required for INR transactions."))
		validate_ifsc_code(doc)
	else:
		if not doc.swift_number:
			swift_number = frappe.db.get_value("Bank", doc.bank, "swift_number")
			if not swift_number:
				frappe.throw(
					_(
						"SWIFT number is required for inter-currency transactions. Please set it in the Bank master."
					)
				)
			else:
				doc.swift_number = swift_number
				validate_swift_code(doc)
				frappe.msgprint(
					_("SWIFT number is set to {0} from Bank master.").format(
						frappe.bold(doc.swift_number)
					)
				)
		else:
			validate_swift_code(doc)

		if not doc.iban:
			frappe.throw("IBAN number is required for inter-currency transactions.")
		else:
			validate_iban(doc)
			if not doc.bank_account_no:
				doc.bank_account_no = doc.iban


def validate_iban(doc):
	if not IBAN_PATTERN.match(cstr(doc.iban)):
		frappe.throw(_("IBAN is not valid"))


def validate_ifsc_code(doc):
	if not IFSC_PATTERN.match(cstr(doc.branch_code)):
		frappe.throw(_("IFSC/Branch Code is not valid"))


def validate_swift_code(doc):
	if not SWIFT_PATTERN.match(cstr(doc.swift_number)):
		frappe.throw(_("SWIFT code is not valid"))


def update_transaction_currency(doc):
	if doc.party_type and doc.party:
		currency_field = (
			"salary_currency" if doc.party_type == "Employee" else "default_currency"
		)
		doc.currency = frappe.get_value(
			doc.party_type, doc.party, currency_field
		) or frappe.db.get_value("Company", doc.company, "default_currency")
	elif doc.is_company_account:
		doc.currency = frappe.db.get_value("Company", doc.company, "default_currency")
