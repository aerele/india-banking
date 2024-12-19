import re

import frappe
from frappe import _
from frappe.utils import cstr


def bank_on_trash(doc, method=None):
	if hasattr(doc, "is_standard") and doc.is_standard:
		frappe.throw(
			_("Standard Bank cannot be deleted"), title=_("Action Not Permitted")
		)


def validate_ifsc_code(doc, method=None):
	pattern = re.compile("^[A-Z]{4}0[A-Z0-9]{6}$")
	if not pattern.match(cstr(doc.branch_code)):
		frappe.throw(_("IFSC/Branch Code is not valid"))
