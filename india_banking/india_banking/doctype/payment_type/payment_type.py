# Copyright (c) 2024, Aerele Technologies Private Limited and contributors
# For license information, please see license.txt

import frappe
from erpnext.accounts.utils import get_autoname_with_number
from frappe import _
from frappe.model.document import Document


class PaymentType(Document):
	def autoname(self):
		self.name = get_autoname_with_number("", self.payment_type, self.company)

	def on_update(self):
		if self.is_default:
			frappe.db.set_value(
				"Payment Type",
				{"company": self.company, "name": ["!=", self.name]},
				"is_default",
				0,
			)
		else:
			if not frappe.db.exists(
				"Payment Type",
				{"company": self.company, "is_default": 1, "name": ["!=", self.name]},
			):
				frappe.msgprint(
					_(
						f"set as {frappe.bold(self.name)}, the company {frappe.bold(self.company)} default payment method"
					)
				)
				self.db_set("is_default", 1)
