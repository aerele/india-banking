import re

import frappe
from frappe import _
from frappe.utils import cstr

IFSC_PATTERN = re.compile(r"^[A-Z]{4}0[A-Z0-9]{6}$")


def bank_on_trash(doc, method=None):
	if getattr(doc, "is_standard", False):
		frappe.throw(
			_("Standard Bank cannot be deleted"), title=_("Action Not Permitted")
		)


def validate_ifsc_code(doc, method=None):
	if not IFSC_PATTERN.match(cstr(doc.branch_code)):
		frappe.throw(_("IFSC/Branch Code is not valid"))
