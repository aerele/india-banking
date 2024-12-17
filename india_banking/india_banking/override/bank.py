import re

import frappe
from erpnext.accounts.doctype.bank.bank import Bank
from frappe import _, cstr


class CustomBank(Bank):
	def on_trash(self):
		if self.is_standard:
			frappe.throw(
				_("Standard Bank cannot be deleted"), title=_("Action Not Permitted")
			)

	def validate(self):
		super().validate()
		self.validate_ifsc_code()

	def validate_ifsc_code(self):
		pattern = re.compile("^[A-Z]{4}0[A-Z0-9]{6}$")
		if not pattern.match(cstr(self.branch_code)):
			frappe.throw(_("IFSC/Branch Code is not valid"))
