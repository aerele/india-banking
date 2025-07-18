# Copyright (c) 2024, Aerele Technologies Private Limited and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class IndiaBankingSettings(Document):
	def validate(self):
		self.enable_or_disable_workflow_to_bank_account()
		self.validate_document_series()
		self.enable_payment_entry_reposting()
		if not self.notify_party:
			self.payment_notification = []

	def validate_document_series(self):
		if self.doctype_naming_series:
			for series in self.doctype_naming_series:
				if series.series:
					options = frappe.get_meta(series.doctype_name).get_options(
						"naming_series"
					)
					options_list = options.split("\n")
					if options and series.series not in options_list:
						frappe.throw(
							f"You can only select a series that starts with <b>{options_list}</b> at #Row {frappe.bold(series.idx)}"
						)

	def enable_or_disable_workflow_to_bank_account(self):
		"""Enable or disable workflow to bank account based on settings."""
		if frappe.db.exists("Workflow", "Bank Account Approval"):
			frappe.set_value(
				"Workflow",
				"Bank Account Approval",
				"is_active",
				self.activate_workflow_on_bank_account,
			)

	def enable_payment_entry_reposting(self):
		if self.update_posting_date_as_payment_date:
			if not frappe.db.exists(
				"Repost Allowed Types",
				{
					"parent": "Repost Accounting Ledger Settings",
					"document_type": "Payment Entry",
					"allowed": 1,
				},
			):
				doc = frappe.get_single("Repost Accounting Ledger Settings")
				doc.append(
					"allowed_types",
					{
						"document_type": "Payment Entry",
						"allowed": 1,
					},
				)
				doc.save()
