# Copyright (c) 2024, Aerele Technologies Private Limited and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class IndiaBankingSettings(Document):
	def validate(self):
		self.enable_or_disable_workflow_to_bank_account()

	def enable_or_disable_workflow_to_bank_account(self):
		"""Enable or disable workflow to bank account based on settings."""
		if frappe.db.exists("Workflow", "Bank Account Approval"):
			frappe.set_value(
				"Workflow",
				"Bank Account Approval",
				"is_active",
				self.activate_workflow_on_bank_account,
			)
