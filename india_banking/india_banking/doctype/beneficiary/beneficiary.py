# Copyright (c) 2025, Aerele Technologies Private Limited and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import cstr

class Beneficiary(Document):
	@frappe.whitelist()
	def get_last_max_number(self):
		last_max_number = frappe.db.sql("""
			SELECT MAX(CAST(SUBSTRING_INDEX(beneficiary, ' ', 1) AS UNSIGNED))
			FROM `tabBeneficiary`""")
		frappe.log_error("Max-get_last_max_number", last_max_number)
		return last_max_number[0][0] + 1 if last_max_number else ""

	def on_update(self):
		"""Send the beneficiary details to the bank connector"""
		if self.beneficiary_status != "Draft":
			return

	def validate(self):
		if frappe.db.exists(
			"Beneficiary", {
				"company": self.company,
				"party_type": self.party_type,
				"party": self.party,
				"bank_connector": self.bank_connector,
				"bank_account": self.bank_account,
				"name": ["!=", self.name],
				"beneficiary_status": ["!=", "Discarded"]
			}
		):
			frappe.throw(
				"Beneficiary already exists for this Company, Party Type, Party and Bank Connector"
			)

	@frappe.whitelist()
	def submit_beneficiary(self):
		"""Submit the beneficiary details to the bank connector"""
		if not self.bank_connector:
			frappe.throw("Bank Connector not found for this Bank Account")

		bank_connector = frappe.get_doc("Bank Connector", self.bank_connector)
		bank_connector.post_request(beneficiary_id=self.name)

	@frappe.whitelist()
	def update_beneficiary(self, action=None):
		"""Update/delete the beneficiary details to the bank connector"""
		if not self.bank_connector:
			frappe.throw("Bank Connector not found for this Bank Account")

		bank_connector = frappe.get_doc("Bank Connector", self.bank_connector)
		bank_connector.post_request(beneficiary_id=self.name, action=action)

	@frappe.whitelist()
	def discard_beneficiary(self):
		self.update_beneficiary(action="Discard")

	def on_trash(self):
		if self.beneficiary_status != "Draft":
			frappe.throw("Beneficiary cannot be deleted")

	def is_beneficiary_approved(self):
		"""Check the beneficiary status"""
		if self.beneficiary_status == "Approved":
			return True
		elif self.beneficiary_status == "Draft":
			frappe.throw("Beneficiary is in Draft state")
		elif self.beneficiary_status == "Submitted":
			frappe.throw("Beneficiary is submitted")
		elif self.beneficiary_status == "Rejected":
			frappe.throw("Beneficiary is rejected")
		elif self.beneficiary_status == "Discarded":
			frappe.throw("Beneficiary is discarded")
		else:
			frappe.throw(f"Invalid Beneficiary status({self.beneficiary_status})")



@frappe.whitelist()
def add_beneficiary(**kwargs):
	bene_doc = frappe.new_doc("Beneficiary")
	bene_doc.update(kwargs)
	bene_doc.insert()

	frappe.db.set_value(
		"Bank Account", kwargs.get("bank_account"), "beneficiary", bene_doc.name
	)
	frappe.msgprint(
		f"Beneficiary {bene_doc.name} added successfully to Bank Account {kwargs.get('bank_account')}",
		alert=1,
		indicator="green",
	)
	return bene_doc.name


@frappe.whitelist()
def submit_beneficiary(beneficiary_id):
	"""Submit the beneficiary details to the bank connector"""
	beneficiary_doc = frappe.get_doc("Beneficiary", beneficiary_id)
	beneficiary_doc.submit_beneficiary()


@frappe.whitelist()
def update_beneficiary(beneficiary_id, action=None):
	"""Update the beneficiary details to the bank connector"""
	if not action:
		frappe.throw("Action not found")

	beneficiary_doc = frappe.get_doc("Beneficiary", beneficiary_id)
	beneficiary_doc.update_beneficiary(action=action)


@frappe.whitelist()
def update_beneficiary_details(**beneficiary_details):
	"""Update the beneficiary details to the bank connector"""
	if not beneficiary_details.get("action"):
		frappe.throw("Action not found")

	if beneficiary_id:=beneficiary_details.get("beneficiary"):
		beneficiary_doc = frappe.get_doc("Beneficiary", beneficiary_id)
		if beneficiary_details.get("limit_level") == "NONE":
			beneficiary_details.update(
				{
					"limit_frequency": "",
					"limit_on_amount": 0,
					"limit_on_transactions": 0,
				}
			)

		beneficiary_doc.update(beneficiary_details)
		beneficiary_doc.beneficiary_status = "Modified"
		beneficiary_doc.save()
	try:
		beneficiary_doc = frappe.get_doc("Beneficiary", beneficiary_id)
		beneficiary_doc.update_beneficiary(action=beneficiary_details.get("action"))
	except Exception:
		frappe.log_error(
			f"Error while updating beneficiary {beneficiary_id} with action {beneficiary_details.get('action')}",
			frappe.get_traceback(with_context=True),
		)
