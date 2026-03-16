import json

import frappe
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_accounting_dimensions,
)
from erpnext.accounts.doctype.payment_order.payment_order import PaymentOrder
from frappe import _
from frappe.utils import get_link_to_form, getdate

from india_banking.default import PAYMENT_SUMMARY_FIELDS
from india_banking.india_banking.doc_events.payment_order import make_payment_entries
from india_banking.india_banking.doctype.india_banking_connector.india_banking_connector import (
	get_bank_balance,
)


class CustomPaymentOrder(PaymentOrder):
	def before_submit(self):
		if not frappe.get_single(
			"India Banking Settings"
		).allow_future_date_payment_order:
			if getdate(self.posting_date) > getdate():
				link = get_link_to_form(
					"India Banking Settings", "India Banking Settings"
				)
				frappe.throw(
					title=_("Future Date Not Allowed"),
					msg=_(
						f"Future Payment Order Date is not allowed! <br> Please go to <b>{link}</b> and enable 'Allow Future Date Payment Order' to proceed."
					),
				)
		if frappe.db.get_value(
			"India Banking Connector",
			self.company_bank_account,
			"validate_bank_balance",
		):
			if bank_balance := get_bank_balance(self.company_bank_account):
				if bank_balance < self.total:
					frappe.throw(
						title=_("Insufficient Balance"),
						msg=_(
							"Bank Account {0} has insufficient balance {1} to process the total amount {2}"
						).format(self.company_bank_account, bank_balance, self.total),
					)

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
						frappe.throw(title=_("Invalid Amount"), msg=_(message))

	def validate(self):
		self.validate_summary()

	def validate_summary(self):
		a2a_mode = "A2A/FT/Internal"

		if not self.summary:
			frappe.throw(_("Please validate the summary"))

		default_mode_of_transfer = (
			frappe.get_doc("Mode of Transfer", self.default_mode_of_transfer)
			if self.default_mode_of_transfer
			else None
		)
		a2a_transfer_modes = frappe.db.get_all(
			"Mode of Transfer", {"mode": a2a_mode, "disabled": 0}, pluck="name"
		)

		summary_total = 0
		for payment in self.summary:
			if not payment.mode_of_transfer:
				frappe.throw(_("Define a specific mode of transfer or a default one"))

			mode_of_transfer = (
				frappe.get_doc("Mode of Transfer", payment.mode_of_transfer)
				if payment.mode_of_transfer
				else default_mode_of_transfer
			)

			if (
				mode_of_transfer.mode in ["NEFT", "RTGS"]
				and payment.amount >= 500000000
			):
				lei_number = frappe.db.get_value(
					payment.party_type, payment.party, "lei_number"
				)
				if not lei_number:
					frappe.throw(
						_(
							f"LEI Number required for payment > 50 Cr. For {payment.party_type} - {payment.party} - {payment.amount}"
						)
					)

			if "A2A" in mode_of_transfer.mode and payment.bank != self.company_bank:
				frappe.throw(
					_(
						f"Invalid mode of transfer for {payment.party_type} - {payment.party} at <b>row #{payment.idx}</b>"
					)
				)

			if (
				payment.bank == self.company_bank
				and mode_of_transfer.mode not in a2a_transfer_modes
			):
				if not a2a_transfer_modes:
					frappe.throw("Mode of Transfer: {0} not found".format(a2a_mode))

				payment.mode_of_transfer = a2a_transfer_modes[0]

			if not mode_of_transfer:
				frappe.throw(_("Define a specific mode of transfer or a default one"))

			if not (
				mode_of_transfer.minimum_limit
				<= payment.amount
				<= mode_of_transfer.maximum_limit
			):
				frappe.throw(
					_(
						f"Mode of Transfer not suitable for {payment.party} for {payment.amount}. {mode_of_transfer.mode}: {mode_of_transfer.minimum_limit}-{mode_of_transfer.maximum_limit}"
					)
				)

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
			frappe.throw(_("Summary isn't matching the references"))

	def get_party_field_name(self, party):
		if party.party_type == "Supplier":
			return "supplier_name"
		elif party.party_type == "Employee":
			return "employee_name"
		elif party.party_type == "Shareholder":
			return "name"
		elif party.party_type == "Customer":
			return "customer_name"
		else:
			return "name"

	def on_submit(self):
		if self.payment_order_type in [
			"Payment Request",
			"Payment Entry",
			"Journal Entry",
		]:
			if self.payment_order_type == "Payment Request":
				make_payment_entries(self.name)

			self.update_payment_status()

	def on_update_after_submit(self):
		frappe.throw(_("You cannot modify a payment order"))

	def on_cancel(self):
		for summary in self.summary:
			if summary.payment_status in ["Processed", "Initiated"]:
				frappe.throw(
					_(
						"You cannot cancel a payment order with Initiated/Processed payments"
					)
				)
		super().on_cancel()

		self.ignore_linked_doctypes = [
			"Unreconcile Bank Payment",
			"Bank Payment Allocation",
		]

	def on_update(self):
		if self.docstatus == 0:
			self.verify_and_update_summary_references()

	@frappe.whitelist()
	def verify_and_update_summary_references(self):
		try:

			def _get_unique_key(reference=None, summarise_field_only=False):
				summarise_field = PAYMENT_SUMMARY_FIELDS.copy()
				summarise_field.extend(get_accounting_dimensions())

				if self.summarise_payment_based_on == "Party":
					summarise_field.remove("reference_name")

				if summarise_field_only:
					return tuple(summarise_field)
				else:
					return tuple(
						[reference.get(field, "") for field in summarise_field]
					)

			summary = {}
			for reference in self.references:
				key = _get_unique_key(reference)

				if key in summary:
					summary[key]["amount"] += reference.amount
					summary[key]["summary_references"].append(reference.name)

				else:
					summary[key] = {
						"amount": reference.amount,
						"summary_references": [reference.name],
					}

			if len(summary) != len(self.summary):
				frappe.throw(_("Please validate the summary"))

			for ref_summary, summary_row in zip(list(summary.values()), self.summary):
				if ref_summary.get("amount") != summary_row.get("amount"):
					frappe.throw(
						title="Summary details mismatch",
						msg=_("Please validate the summary"),
					)
				summary_row.db_set(
					"summary_references", str(ref_summary["summary_references"])
				)
		except Exception:
			frappe.db.rollback()
		else:
			frappe.db.commit()

	def on_trash(self):
		if self.docstatus == 1:
			frappe.throw(_("You cannot delete a payment order"))

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
				doctype = (
					self.payment_order_type + " Account"
					if self.payment_order_type == "Journal Entry"
					else self.payment_order_type
				)
				frappe.db.set_value(
					doctype,
					d.get(ref_doc_field),
					ref_field,
					status,
				)


@frappe.whitelist()
def get_party_summary(
	references,
	company_bank_account,
	summarise_payment_based_on=None,
	default_mode_of_transfer=None,
):
	references = json.loads(references)
	if not len(references) or not company_bank_account:
		return

	# Considering the following dimensions to group payments
	def _get_unique_key(reference=None, summarise_field_only=False):
		summarise_field = PAYMENT_SUMMARY_FIELDS.copy()
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
			summary[key]["amount"] += reference.amount

		else:
			summary[key] = {
				"amount": reference.amount,
			}

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
				"amount": val.get("amount"),
				"mode_of_transfer": get_mode_of_transfer(
					val.get("amount"),
					party_bank,
					company_bank,
					default_mode_of_transfer,
				),
			}
		)

		result.append(summary_line_item)

	return result


def get_mode_of_transfer(
	amount, party_bank, company_bank, default_mode_of_transfer=None
):
	mode_of_transfer = None
	if party_bank == company_bank:
		mode_of_transfer = frappe.db.get_value(
			"Mode of Transfer", {"is_bank_specific": 1, "bank": party_bank}
		)
	else:
		mode_of_transfer = (
			frappe.db.get_value(
				"Mode of Transfer",
				{
					"minimum_limit": ["<=", amount],
					"maximum_limit": [">", amount],
					"is_bank_specific": 0,
					"disabled": 0,
				},
				order_by="priority asc",
			)
			or default_mode_of_transfer
		)

	return mode_of_transfer


@frappe.whitelist()
def create_payment_order(payment_entry, default_mode_of_transfer=None):
	from india_banking.overrides.payment_entry import make_payment_order

	po = make_payment_order(payment_entry)
	po.posting_date = frappe.utils.nowdate()
	po.default_mode_of_transfer = default_mode_of_transfer

	references = [ref.as_dict() for ref in po.references]
	summary_rows = get_party_summary(
		json.dumps(references),
		po.company_bank_account,
		default_mode_of_transfer=default_mode_of_transfer,
	)

	if not summary_rows:
		frappe.throw(
			_("Could not generate payment summary for Payment Entry {0}").format(
				payment_entry
			)
		)

	for row in summary_rows:
		po.append("summary", row)

	po.insert(ignore_permissions=True)
	po.submit()

	return po.name
