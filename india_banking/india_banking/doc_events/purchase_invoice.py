import frappe
from frappe.utils import today


def hold_invoice_for_payment(self, method):
	self.block_invoice("Hold on Payments")

def on_update_after_submit(self, method):
	unblock_bulk_release(self, method)

def unblock_bulk_release(self, method):
	if self.on_hold == 1 and self.hold_comment == "Hold on Payments":
		if self.release_using_data_import == 1:
			self.db_set("on_hold", 0)
			self.db_set("release_date", None)
			self.db_set("hold_comment", "Released using data import")

@frappe.whitelist()
def make_payment_order(source_name, target_doc=None):
	from frappe.model.mapper import get_mapped_doc

	def set_missing_values(source, target):
		target.payment_order_type = "Purchase Invoice"
		bank_account = source.bank_account
		if not bank_account:
			bank_account = frappe.db.get_value("Bank Account", {"party_type": "Supplier", "party": source.supplier, "is_default": 1, "workflow_state": "Approved"}, "name")
		
		if not bank_account:
			frappe.throw(f"{source.supplier} does not have an default & approved bank account")

		target.posting_date = today()
		target.append(
			"references",
			{
				"reference_doctype": source.doctype,
				"reference_name": source.name,
				"amount": source.outstanding_amount,
				"supplier": source.supplier,
				"mode_of_payment": "Wire Transfer",
				"bank_account": bank_account,
				"state": source.state
			},
		)
		target.status = "Pending"

	doclist = get_mapped_doc(
		"Purchase Invoice",
		source_name,
		{
			"Purchase Invoice": {
				"doctype": "Payment Order",
			}
		},
		target_doc,
		set_missing_values,
	)
	return doclist