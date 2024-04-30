import frappe
from frappe import _

def valdidate_bank_for_wire_transfer(self, method):
	if self.mode_of_payment == "Wire Transfer" and not self.bank_account:
		frappe.throw(_("Bank Account is missing for Wire Transfer Payments"))

@frappe.whitelist()
def make_payment_order(source_name, target_doc=None):
	from frappe.model.mapper import get_mapped_doc

	def set_missing_values(source, target):
		target.payment_order_type = "Payment Request"
		account = ""
		if source.payment_type:
			account = frappe.db.get_value("Payment Type", source.payment_type, "account")
		if source.reference_doctype == "Purchase Invoice":
			account = frappe.db.get_value(source.reference_doctype, source.reference_name, "credit_to")
		target.append(
			"references",
			{
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
				"state": source.state,
				"cost_center": source.cost_center,
				"project": source.project,
				"tax_withholding_category": source.tax_withholding_category,
			},
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

