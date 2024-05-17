import frappe 

from erpnext.accounts.doctype.bank.bank import Bank
from frappe import _

class CustomBank(Bank):
    def on_trash(self):
        if self.is_standard:
            frappe.throw(_("Standard Bank cannot be deleted"), title=_("Action Not Permitted"))