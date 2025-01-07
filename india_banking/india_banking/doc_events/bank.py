import frappe
from frappe import _


def disallow_standard_bank_deletion(doc, method=None):
	if getattr(doc, "is_standard", False):
		frappe.throw(
			_("Standard Bank cannot be deleted"), title=_("Action Not Permitted")
		)
