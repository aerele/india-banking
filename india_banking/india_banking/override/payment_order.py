import frappe, json
from erpnext.accounts.doctype.payment_order.payment_order import PaymentOrder
from india_banking.india_banking.doc_events.payment_order import make_payment_entries

class CustomPaymentOrder(PaymentOrder):
	def before_save(self):
		self.group_same_reference_rows()

	def group_same_reference_rows(self):
		group_by_reference = {}

		for ref in self.references:
			key = (ref.reference_doctype, ref.reference_name)
			if  key in group_by_reference:
				group_by_reference[key].amount += ref.amount
			else:
				group_by_reference[key] = ref

		self.references = group_by_reference.values()

	def validate(self):
		self.validate_summary()
		for payment_info in self.summary:
			if payment_info.mode_of_transfer == "RTGS" and payment_info.amount >= 500000000:
				lei_number = frappe.db.get_value(payment_info.party_type, payment_info.party, "custom_lei_number")
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

	summary = {}
	for ref in references:
		ref = frappe._dict(ref)
		if (ref.party_type, ref.party, ref.bank_account, ref.account, ref.cost_center, ref.project, ref.tax_withholding_category, ref.reference_doctype) in summary:
			summary[(ref.party_type, ref.party, ref.bank_account, ref.account, ref.cost_center, ref.project, ref.tax_withholding_category, ref.reference_doctype)] += ref.amount
		else:
			summary[(ref.party_type, ref.party, ref.bank_account, ref.account, ref.cost_center, ref.project, ref.tax_withholding_category, ref.reference_doctype)] = ref.amount

	result = []
	for k, v in summary.items():
		party_type, party, bank_account, account, cost_center, project, tax_withholding_category, reference_doctype = k
		summary_line_item = {}
		summary_line_item["party_type"] = party_type
		summary_line_item["party"] = party
		summary_line_item["bank_account"] = bank_account
		summary_line_item["account"] = account
		summary_line_item["cost_center"] = cost_center
		summary_line_item["project"] = project
		summary_line_item["tax_withholding_category"] = tax_withholding_category
		summary_line_item["reference_doctype"] = reference_doctype
		summary_line_item["amount"] = v
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