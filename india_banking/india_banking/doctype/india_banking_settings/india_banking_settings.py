# Copyright (c) 2024, Aerele Technologies Private Limited and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class IndiaBankingSettings(Document):
	def validate(self):
		self.validate_unlink_roles_change()

	def validate_unlink_roles_change(self):
		if "Administrator" in frappe.get_roles():
			return

		before = self.get_doc_before_save()
		old_roles = sorted([d.role for d in before.unlink_allowed_roles]) if before else []
		new_roles = sorted([d.role for d in self.unlink_allowed_roles])

		if old_roles != new_roles:
			frappe.throw(_("Only the Administrator can modify 'Allowed Roles to Unlink'."))
