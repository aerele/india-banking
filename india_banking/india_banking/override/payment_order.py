import frappe, json
from erpnext.accounts.doctype.payment_order.payment_order import PaymentOrder
from india_banking.india_banking.doc_events.payment_order import make_payment_entries

from frappe.utils import get_datetime
import re

class CustomPaymentOrder(PaymentOrder):
	def before_submit(self):
		self.update_unique_and_file_reference_id()

	@frappe.whitelist()
	def update_unique_and_file_reference_id(self, save=False):
		unique_id = ''.join(re.findall(r'[0-9a-zA-Z]', self.name))+ get_datetime().strftime("%y%m%d%H%M")
		frappe.db.set_value("Payment Order", self.name, {"unique_id": unique_id, "file_reference_id": unique_id})
		if save:
			frappe.db.commit()

	def validate(self):
		self.validate_summary()
		for payment_info in self.summary:
			if payment_info.mode_of_transfer == "RTGS" and payment_info.amount >= 500000000:
				lei_number = frappe.db.get_value(payment_info.party_type, payment_info.party, "lei_number")
				if not lei_number:
					frappe.throw(f"LEI Number required for payment > 50 Cr. For {payment_info.party_type} - {payment_info.party} - {payment_info.amount}")

	def validate_summary(self):
		if len(self.summary) <= 0:
			frappe.throw("Please validate the summary")

		default_mode_of_transfer = None
		if self.default_mode_of_transfer:
			default_mode_of_transfer = frappe.get_doc("Mode of Transfer", self.default_mode_of_transfer)

		for payment in self.summary:
			if payment.mode_of_transfer:
				mode_of_transfer = frappe.get_doc("Mode of Transfer", payment.mode_of_transfer)
			else:
				if not default_mode_of_transfer:
					frappe.throw("Define a specific mode of transfer or a default one")
				mode_of_transfer = default_mode_of_transfer
				payment.mode_of_transfer = default_mode_of_transfer.mode

			if payment.amount < mode_of_transfer.minimum_limit or payment.amount > mode_of_transfer.maximum_limit:
				frappe.throw(f"Mode of Transfer not suitable for {payment.party} for {payment.amount}. {mode_of_transfer.mode}: {mode_of_transfer.minimum_limit}-{mode_of_transfer.maximum_limit}")

		summary_total = 0
		references_total = 0
		for ref in self.references:
			party_name_field = 'supplier_name' if ref.party_type == 'Supplier' else 'customer_name'
			#update party name
			ref.party_name = frappe.get_value(ref.party_type, ref.party, party_name_field)

			references_total += ref.amount

		for sum in self.summary:
			summary_total += sum.amount

		if summary_total != references_total:
			frappe.throw("Summary isn't matching the references")

	def on_submit(self):
		if self.payment_order_type == "Payment Entry":
			pass
		else:
			make_payment_entries(self.name)
			frappe.db.set_value("Payment Order", self.name, "status", "Pending")

			for ref in self.references:
				if hasattr(ref, "bank_payment_request"):
					frappe.db.set_value("Bank Payment Request", ref.bank_payment_request, "status", "Payment Ordered")

	def on_update_after_submit(self):
		frappe.throw("You cannot modify a payment order")
		return


	def before_cancel(self):
		for summary_item in self.summary:
			if summary_item.payment_status in ["Processed", "Initiated"]:
				frappe.throw("You cannot cancel a payment order with Initiated/Processed payments")
				return

	def on_trash(self):
		if self.docstatus == 1:
			frappe.throw("You cannot delete a payment order")
			return

	def update_payment_status(self, cancel=False):
		status = "Payment Ordered"
		if cancel:
			status = "Initiated"

		if self.payment_order_type == "Bank Payment Request":
			ref_field = "status"
			ref_doc_field = frappe.scrub(self.payment_order_type)
		else:
			ref_field = "payment_order_status"
			ref_doc_field = "reference_name"

		for d in self.references:
			frappe.db.set_value(self.payment_order_type, d.get(ref_doc_field), ref_field, status)


@frappe.whitelist()
def get_party_summary(references, company_bank_account):
	references = json.loads(references)
	if not len(references) or not company_bank_account:
		return

	# Considering the following dimensions to group payments
	# (party_type, party, bank_account, account, cost_center, project)
	def _get_unique_key(ref=None, summarise_field=False):
		summarise_payment_based_on = frappe.get_single("India Banking Settings").summarise_payment_based_on

		if summarise_payment_based_on == "Party":
			if summarise_field:
				return  ("party_type", "party", "bank_account", "account", "cost_center", "project",
				"tax_withholding_category", "reference_doctype", "payment_entry")

			return (ref.party_type, ref.party, ref.bank_account, ref.account, ref.cost_center, ref.project,
			ref.tax_withholding_category, ref.reference_doctype, ref.payment_entry)

		elif summarise_payment_based_on == "Voucher":
			if summarise_field:
				return ('party_type', 'party', 'reference_doctype', 'reference_name', 'bank_account',
				'account', 'cost_center', 'project', 'tax_withholding_category', 'payment_entry')

			return (ref.party_type, ref.party, ref.reference_doctype, ref.reference_name, ref.bank_account,
			ref.account, ref.cost_center, ref.project, ref.tax_withholding_category, ref.payment_entry)

	summary = {}
	for ref in references:
		ref = frappe._dict(ref)
		key = _get_unique_key(ref)
		if key in summary:
			summary[key] += ref.amount
		else:
			summary[key] = ref.amount

	result = []
	for key, val in summary.items():
		summary_line_item = {k: v for k, v in zip(_get_unique_key(summarise_field=True), key) }
		summary_line_item["amount"] = val
		summarise_payment_based_on = frappe.get_single("India Banking Settings").summarise_payment_based_on
		if summarise_payment_based_on == "Party":
			summary_line_item["is_party_wise"] = 1
		else:
			summary_line_item["is_party_wise"] = 0

		result.append(summary_line_item)

	for row in result:
		party_bank = frappe.db.get_value("Bank Account", row["bank_account"], "bank")
		company_bank = frappe.db.get_value("Bank Account", company_bank_account, "bank")
		row["mode_of_transfer"] = None
		if party_bank == company_bank:
			mode_of_transfer = frappe.db.get_value("Mode of Transfer", {"is_bank_specific": 1, "bank": party_bank})
			if mode_of_transfer:
				row["mode_of_transfer"] = mode_of_transfer
		else:
			mot = frappe.db.get_value("Mode of Transfer", {
				"minimum_limit": ["<=", row["amount"]],
				"maximum_limit": [">", row["amount"]],
				"is_bank_specific": 0
				}, 
				order_by = "priority asc")
			if mot:
				row["mode_of_transfer"] = mot

	return result