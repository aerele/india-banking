# Copyright (c) 2024, Aerele Technologies Private Limited and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cstr


class IndiaBankingSettings(Document):
	def validate(self):
		self.enable_or_disable_workflow_to_bank_account()
		self.validate_custom_app_priority()

	def validate_custom_app_priority(self):
		self.custom_app_priority = cstr(self.custom_app_priority).strip()

		custom_app_priority = frappe.scrub(self.custom_app_priority)
		if (
			not custom_app_priority
			or frappe.scrub(custom_app_priority) == "india_banking"
		):
			return

		# Ensure that core apps are not set as custom app priority
		if custom_app_priority in ["frappe", "erpnext", "payments", "hrms"]:
			frappe.msgprint(
				_("Custom App cannot be {0}").format(
					frappe.unscrub(custom_app_priority)
				)
			)
			self.custom_app_priority = ""

	def enable_or_disable_workflow_to_bank_account(self):
		"""Enable or disable workflow to bank account based on settings."""
		if frappe.db.exists("Workflow", "Bank Account Approval"):
			frappe.set_value(
				"Workflow",
				"Bank Account Approval",
				"is_active",
				self.enable_bank_account_workflow,
			)
