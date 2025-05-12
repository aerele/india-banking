import re

import frappe
from frappe import _
from frappe.utils import cstr

IFSC_PATTERN = re.compile(r"^[A-Z]{4}0[A-Z0-9]{6}$")


def validate(doc, method=None):
	validate_ifsc_code(doc)
	update_party_transaction_currency(doc)


def validate_ifsc_code(doc):
	if not IFSC_PATTERN.match(cstr(doc.branch_code)):
		frappe.throw(_("IFSC/Branch Code is not valid"))


def update_party_transaction_currency(doc):
	if doc.party_type and doc.party:
		currency_field = (
			"salary_currency" if doc.party_type == "Employee" else "default_currency"
		)
		if frappe.get_meta(doc.party_type).has_field("default_currency"):
			doc.currency = frappe.get_value(
				doc.party_type, doc.party, currency_field
			) or frappe.db.get_value("Company", doc.company, "default_currency")
		else:
			doc.currency = frappe.db.get_value(
				"Company", doc.company, "default_currency"
			)
	elif doc.is_company_account:
		doc.currency = frappe.db.get_value("Company", doc.company, "default_currency")
