import json
import re

import frappe
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_accounting_dimensions,
)
from erpnext.accounts.doctype.payment_order.payment_order import PaymentOrder
from frappe.utils import get_link_to_form

from india_banking.india_banking.doc_events.payment_order import make_payment_entries


class CustomPaymentOrder(PaymentOrder):
	def before_submit(self):
		self.validate_bank_payment_request()
		self.update_unique_and_file_reference_id()

	def validate_bank_payment_request(self):
		if self.references:
			for ref in self.references:
				if ref.payment_request:
					payment_request = frappe.get_doc(
						"Payment Request", ref.payment_request
					)
					if payment_request.grand_total != ref.amount:
						link = get_link_to_form("Payment Request", ref.payment_request)
						message = f"The amount in <b>#Row{ref.idx} </b>does not match the amount of the Payment Request -<b>{link}</b>. The Difference is <b>{ref.amount - payment_request.grand_total}</b>"
						frappe.throw(title="Invalid Amount", msg=message)

	@frappe.whitelist()
	def update_unique_and_file_reference_id(self):
		unique_id = "".join(re.findall(r"[0-9a-zA-Z]", self.name))[-10:]
		frappe.db.set_value(
			"Payment Order",
			self.name,
			{"unique_id": unique_id, "file_reference_id": unique_id},
		)
		self.reload()

	def validate(self):
		self.validate_summary()

	def validate_summary(self):
		if not self.summary:
			frappe.throw("Please validate the summary")

		default_mode_of_transfer = (
			frappe.get_doc("Mode of Transfer", self.default_mode_of_transfer)
			if self.default_mode_of_transfer
			else None
		)

		summary_total = 0
		for payment in self.summary:
			mode_of_transfer = (
				frappe.get_doc("Mode of Transfer", payment.mode_of_transfer)
				if payment.mode_of_transfer
				else default_mode_of_transfer
			)

			if mode_of_transfer.mode == "RTGS" and payment.amount >= 500000000:
				lei_number = frappe.db.get_value(
					payment.party_type, payment.party, "lei_number"
				)
				if not lei_number:
					frappe.throw(
						f"LEI Number required for payment > 50 Cr. For {payment.party_type} - {payment.party} - {payment.amount}"
					)

			if "A2A" in mode_of_transfer.mode and payment.bank != self.company_bank:
				frappe.throw(
					f"Invalid mode of transfer for {payment.party_type} - {payment.party} at <b>row #{payment.idx}</b>"
				)

			if not mode_of_transfer:
				frappe.throw("Define a specific mode of transfer or a default one")

			if not (
				mode_of_transfer.minimum_limit
				<= payment.amount
				<= mode_of_transfer.maximum_limit
			):
				frappe.throw(
					f"Mode of Transfer not suitable for {payment.party} for {payment.amount}. {mode_of_transfer.mode}: {mode_of_transfer.minimum_limit}-{mode_of_transfer.maximum_limit}"
				)

			payment.mode_of_transfer = mode_of_transfer.mode
			summary_total += payment.amount

		references_total = 0
		for reference in self.references:
			reference.party_name = frappe.get_value(
				reference.party_type,
				reference.party,
				self.get_party_field_name(reference),
			)
			references_total += reference.amount

		if summary_total != references_total:
			frappe.throw("Summary isn't matching the references")

	def get_party_field_name(self, party):
		if party.party_type == "Supplier":
			return "supplier_name"
		elif party.party_type == "Employee":
			return "employee_name"
		elif party.party_type == "Shareholder":
			return "name"
		elif party.part_type == "Customer":
			return "customer_name"
		else:
			frappe.throw(f"Unsupported party type {party.party_type}")

	def on_submit(self):
		if self.payment_order_type in [
			"Payment Request",
			"Payment Entry",
			"Journal Entry",
		]:
			if self.payment_order_type == "Payment Request":
				make_payment_entries(self.name)

			self.update_payment_status()

		self.reload()

	def on_update_after_submit(self):
		frappe.throw("You cannot modify a payment order")

	def on_cancel(self):
		for summary in self.summary:
			if summary.payment_status in ["Processed", "Initiated"]:
				frappe.throw(
					"You cannot cancel a payment order with Initiated/Processed payments"
				)
		super().on_cancel()

	def on_trash(self):
		if self.docstatus == 1:
			frappe.throw("You cannot delete a payment order")

	def update_payment_status(self, cancel=False):
		self.db_set("status", "Pending")

		status = "Initiated" if cancel else "Payment Ordered"

		ref_field_map = {
			"Payment Request": ("status", frappe.scrub(self.payment_order_type)),
			"Payment Entry": (
				"payment_order_status",
				frappe.scrub(self.payment_order_type),
			),
			"Journal Entry": (
				"payment_status",
				frappe.scrub(self.payment_order_type) + "_account",
			),
		}

		ref_field, ref_doc_field = ref_field_map.get(
			self.payment_order_type, (None, None)
		)

		if ref_field and ref_doc_field:
			for d in self.references:
				frappe.db.set_value(
					self.payment_order_type + " Account",
					d.get(ref_doc_field),
					ref_field,
					status,
				)


@frappe.whitelist()
def get_party_summary(
	references, company_bank_account, summarise_payment_based_on=None
):
	references = json.loads(references)
	if not len(references) or not company_bank_account:
		return

	# Considering the following dimensions to group payments
	# (party_type, party, bank_account, account, cost_center, project)
	def _get_unique_key(reference=None, summarise_field_only=False):
		summarise_field = [
			"party_type",
			"party",
			"bank_account",
			"account",
			"cost_center",
			"project",
			"tax_withholding_category",
			"reference_doctype",
			"reference_name",
			"payment_entry",
			"journal_entry",
			"journal_entry_account",
		]
		summarise_field.extend(get_accounting_dimensions())
		if summarise_payment_based_on == "Party":
			summarise_field.remove("reference_name")

		if summarise_field_only:
			return tuple(summarise_field)
		else:
			return tuple([reference.get(field, "") for field in summarise_field])

	summary = {}
	for reference in references:
		reference = frappe._dict(reference)
		key = _get_unique_key(reference)

		if key in summary:
			summary[key] += reference.amount
		else:
			summary[key] = reference.amount

	result = []
	for key, val in summary.items():
		summary_line_item = {
			k: v for k, v in zip(_get_unique_key(summarise_field_only=True), key)
		}
		party_bank = frappe.db.get_value(
			"Bank Account", summary_line_item["bank_account"], "bank"
		)
		company_bank = frappe.db.get_value("Bank Account", company_bank_account, "bank")

		summary_line_item.update(
			{
				"amount": val,
				"mode_of_transfer": get_mode_of_transfer(val, party_bank, company_bank),
			}
		)

		result.append(summary_line_item)

	return result


def get_mode_of_transfer(amount, party_bank, company_bank):
	mode_of_transfer = None
	if party_bank == company_bank:
		mode_of_transfer = frappe.db.get_value(
			"Mode of Transfer", {"is_bank_specific": 1, "bank": party_bank}
		)
	else:
		mode_of_transfer = frappe.db.get_value(
			"Mode of Transfer",
			{
				"minimum_limit": ["<=", amount],
				"maximum_limit": [">", amount],
				"is_bank_specific": 0,
			},
			order_by="priority asc",
		)

	return mode_of_transfer
