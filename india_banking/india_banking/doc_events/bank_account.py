import frappe

from frappe.utils import cstr
from frappe import _
import re

IFSC_PATTERN = re.compile(r"^[A-Z]{4}0[A-Z0-9]{6}$")


def validate_ifsc_code(doc, method=None):
	if not IFSC_PATTERN.match(cstr(doc.branch_code)):
		frappe.throw(_("IFSC/Branch Code is not valid"))
