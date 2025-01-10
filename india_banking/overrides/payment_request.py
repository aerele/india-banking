import frappe
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_accounting_dimensions,
)
from erpnext.accounts.doctype.payment_request.payment_request import PaymentRequest
from erpnext.accounts.doctype.tax_withholding_category.tax_withholding_category import (
	get_party_tax_withholding_details,
)
from erpnext.accounts.party import get_party_bank_account
from frappe import _


class BankPaymentRequest(PaymentRequest):
	def validate(self):
		self.set_default_value()
		if not self.net_total:
			self.net_total = self.grand_total

		if (
			self.apply_tax_withholding_amount
			and self.tax_withholding_category
			and self.payment_request_type == "Outward"
		):
			tds_amount = self.calculate_pr_tds(self.net_total)
			self.taxes_deducted = tds_amount
			self.grand_total = self.net_total - self.taxes_deducted
		else:
			self.grand_total = self.net_total or self.grand_total

		if not self.is_adhoc:
			super().validate()
		else:
			if self.is_new():
				self.status = "Draft"
			if self.reference_doctype or self.reference_name:
				frappe.throw(_("Payments with references cannot be marked as ad-hoc"))

		if self.remarks:
			self.remarks = self.remarks[:48]

		self.valdidate_bank_for_wire_transfer()

	def set_default_value(self):
		if not self.payment_type or (
			payment_type := frappe.db.exists(
				"Payment Type",
				{
					"company": self.company,
					"is_default": 1,
				},
			)
		):
			self.db_set("payment_type", payment_type)
		else:
			frappe.throw(
				_(
					f"Set Default <b><a href='/app/payment-type'>Payment Type</a></b> for company {frappe.bold(self.company)}".format(
						self.company
					)
				)
			)

	def on_submit(self):
		if not self.grand_total or not self.net_total:
			frappe.throw(_("Amount cannot be zero"))

		bank_account = get_party_bank_account(self.party_type, self.party)
		if not bank_account:
			frappe.throw(
				_(
					"Default Bank Account is missing for {0} - {1}".format(
						self.party_type, self.party
					)
				)
			)

		debit_account = frappe.db.get_value(
			"Payment Type", self.payment_type, "account"
		) or frappe.db.get_value(
			self.reference_doctype, self.reference_name, "credit_to"
		)

		if not debit_account:
			frappe.throw(
				_(
					"Debit account for Payment Type <b>{}</b> cannot be determined"
				).format(self.payment_type or "")
			)

		if not self.is_adhoc:
			super().on_submit()
		else:
			if self.payment_request_type == "Outward":
				self.db_set("status", "Initiated")

	def create_payment_entry(self, submit=True):
		payment_entry = super().create_payment_entry(submit=submit)
		if payment_entry.docstatus != 1 and self.payment_type:
			payment_entry.paid_to = (
				frappe.db.get_value("Payment Type", self.payment_type, "account") or ""
			)

		return payment_entry

	def calculate_pr_tds(self, amount):
		doc = self
		doc.supplier = self.party
		doc.company = self.company
		doc.base_tax_withholding_net_total = amount
		doc.tax_withholding_net_total = amount
		doc.taxes = []
		taxes = get_party_tax_withholding_details(doc, self.tax_withholding_category)
		if taxes:
			return taxes["tax_amount"]
		else:
			return 0

	def valdidate_bank_for_wire_transfer(self):
		if self.mode_of_payment == "Wire Transfer" and not self.bank_account:
			frappe.throw(_("Bank Account is missing for Wire Transfer Payments"))

		try:
			status = frappe.db.get_value(
				"Bank Account", self.bank_account, "workflow_state"
			)

			if (
				self.mode_of_payment == "Wire Transfer"
				and status != "Approved"
				and frappe.get_single(
					"India Banking Settings"
				).activate_workflow_on_bank_account
			):
				frappe.throw(_("Cannot proceed with un-approved bank account"))
		except Exception:
			frappe.throw(_("Workflow Not Found for Bank Account"))


@frappe.whitelist()
def make_payment_order(source_name, target_doc=None):
	from frappe.model.mapper import get_mapped_doc

	def set_missing_values(source, target):
		target.payment_order_type = "Payment Request"
		account = ""
		if source.payment_type:
			account = frappe.db.get_value(
				"Payment Type", source.payment_type, "account"
			)
		if source.reference_doctype == "Purchase Invoice":
			account = frappe.db.get_value(
				source.reference_doctype, source.reference_name, "credit_to"
			)

		def _update_dimensions(source):
			return {
				dimension: source.get(dimension, "")
				for dimension in get_accounting_dimensions()
			}

		reference = {
			"reference_doctype": source.reference_doctype,
			"reference_name": source.reference_name,
			"amount": source.grand_total,
			"party_type": source.party_type,
			"party": source.party,
			"payment_request": source_name,
			"mode_of_payment": source.mode_of_payment,
			"bank_account": source.bank_account,
			"account": account,
			"is_adhoc": source.is_adhoc,
			"cost_center": source.cost_center,
			"project": source.project,
			"tax_withholding_category": source.tax_withholding_category,
		}
		reference.update(_update_dimensions(source))

		target.append(
			"references",
			reference,
		)
		target.status = "Pending"

	doclist = get_mapped_doc(
		"Payment Request",
		source_name,
		{
			"Payment Request": {
				"doctype": "Payment Order",
			}
		},
		target_doc,
		set_missing_values,
	)

	return doclist
