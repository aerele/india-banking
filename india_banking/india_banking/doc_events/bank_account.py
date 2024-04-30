import frappe, re
from frappe import _

def validate_ifsc_code(self, method):
	pattern = re.compile("^[A-Z]{4}0[A-Z0-9]{6}$")
	if not pattern.match(self.branch_code):
		frappe.throw(_("IFSC Code is not valid"))