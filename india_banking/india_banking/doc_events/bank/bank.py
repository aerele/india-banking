import frappe
from frappe import _


def disallow_standard_bank_deletion(doc, method=None):
	if getattr(doc, "is_standard", False):
		frappe.throw(
			title=_("Action Not Permitted"), msg=_("Standard Bank cannot be deleted")
		)
