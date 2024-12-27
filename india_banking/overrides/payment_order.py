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
		self.update_unique_and_file_reference_id()
		self.validate_bank_payment_request()

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
	def update_unique_and_file_reference_id(self, save=False):
		unique_id = "".join(re.findall(r"[0-9a-zA-Z]", self.name))
		unique_id = unique_id[-10:]
		frappe.db.set_value(
			"Payment Order",
			self.name,
			{"unique_id": unique_id, "file_reference_id": unique_id},
		)
		if save:
			frappe.db.commit()

	def validate(self):
		self.validate_summary()
		for payment_info in self.summary:
			if (
				payment_info.mode_of_transfer == "RTGS"
				and payment_info.amount >= 500000000
			):
				lei_number = frappe.db.get_value(
					payment_info.party_type, payment_info.party, "lei_number"
				)
				if not lei_number:
					frappe.throw(
						f"LEI Number required for payment > 50 Cr. For {payment_info.party_type} - {payment_info.party} - {payment_info.amount}"
					)
			if (
				"A2A" in payment_info.mode_of_transfer
				and payment_info.bank != self.company_bank
			):
				frappe.throw(
					f"Invalid mode of transfer for {payment_info.party_type} - {payment_info.party} at <b>row #{payment_info.idx}</b>"
				)

	def validate_summary(self):
		if len(self.summary) <= 0:
			frappe.throw("Please validate the summary")

		default_mode_of_transfer = None
		if self.default_mode_of_transfer:
			default_mode_of_transfer = frappe.get_doc(
				"Mode of Transfer", self.default_mode_of_transfer
			)

		for payment in self.summary:
			if payment.mode_of_transfer:
				mode_of_transfer = frappe.get_doc(
					"Mode of Transfer", payment.mode_of_transfer
				)
			else:
				if not default_mode_of_transfer:
					frappe.throw("Define a specific mode of transfer or a default one")
				mode_of_transfer = default_mode_of_transfer
				payment.mode_of_transfer = default_mode_of_transfer.mode

			if (
				payment.amount < mode_of_transfer.minimum_limit
				or payment.amount > mode_of_transfer.maximum_limit
			):
				frappe.throw(
					f"Mode of Transfer not suitable for {payment.party} for {payment.amount}. {mode_of_transfer.mode}: {mode_of_transfer.minimum_limit}-{mode_of_transfer.maximum_limit}"
				)

		summary_total = 0
		references_total = 0
		for ref in self.references:
			party_name_field = self.get_party_field_name(ref)
			# update party name
			ref.party_name = frappe.get_value(
				ref.party_type, ref.party, party_name_field
			)

			references_total += ref.amount

		for sum in self.summary:
			summary_total += sum.amount

		if summary_total != references_total:
			frappe.throw("Summary isn't matching the references")

	def get_party_field_name(self, party):
		if party.party_type == "Supplier":
			return "supplier_name"
		elif party.party_type == "Employee":
			return "employee_name"
		else:
			frappe.throw(f"Unsupported party type {party.party_type}")

	def on_submit(self):
		if self.payment_order_type == "Payment Request":
			make_payment_entries(self.name)
			frappe.db.set_value("Payment Order", self.name, "status", "Pending")

			for ref in self.references:
				if hasattr(ref, "payment_request"):
					frappe.db.set_value(
						"Payment Request",
						ref.payment_request,
						"status",
						"Payment Ordered",
					)

		if self.payment_order_type == "Journal Entry":
			self.update_payemnt_status("submit")

	def update_payemnt_status(self, action=None):
		order_status = ""
		if action == "submit":
			order_status = "Ordered"
		elif action == "cancel":
			order_status = ""
		elif action == "Paid":
			order_status = "Paid"
		elif action == "Failed":
			order_status = "Failed"

		for jea in self.summary:
			frappe.db.set_value(
				"Journal Entry Account",
				jea.journal_entry_account,
				"payment_status",
				order_status,
			)

	def on_update_after_submit(self):
		frappe.throw("You cannot modify a payment order")
		return

	def before_cancel(self):
		self.update_payemnt_status("cancel")
		for summary_item in self.summary:
			if summary_item.payment_status in ["Processed", "Initiated"]:
				frappe.throw(
					"You cannot cancel a payment order with Initiated/Processed payments"
				)
				return
		for account in self.summary:
			if (
				account.payment_status == "Processed"
				or account.payment_status == "Initiated"
			):
				frappe.throw("Cannot cancel a {} Order".format(account.payment_status))

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
		if self.payment_order_type not in [
			"Payment Entry",
			"Journal Entry",
			"Payroll Entry",
		]:
			for d in self.references:
				frappe.db.set_value(
					self.payment_order_type, d.get(ref_doc_field), ref_field, status
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


def get_bank_entry_for_payroll(filters=None):
	if filters and filters.get("refrence_name"):
		condition = "AND jea.reference_name = '{0}'".format(
			filters.get("refrence_name")
		)

	journal_entry = frappe.db.sql(
		f"""
		SELECT
			je.name
		FROM
			`tabJournal Entry`je
		JOIN
			`tabJournal Entry Account`jea
		ON
			je.name = jea.parent
		WHERE
	 		je.docstatus != 2 AND jea.reference_type = 'Payroll Entry' AND je.voucher_type = 'Bank Entry'
			{condition} LIMIT 1
	 """,
		as_dict=1,
	)

	return journal_entry if journal_entry else ""
