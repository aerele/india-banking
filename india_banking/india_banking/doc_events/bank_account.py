import frappe, re
from frappe import _ , cstr

def validate_ifsc_code(self, method):
	pattern = re.compile("^[A-Z]{4}0[A-Z0-9]{6}$")
	if not pattern.match(cstr(self.branch_code)):
		frappe.throw(_("IFSC/Branch Code is not valid"))