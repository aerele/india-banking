# Copyright (c) 2024, Aerele Technologies Private Limited and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from erpnext.accounts.doctype.payment_request.payment_request import PaymentRequest, get_existing_payment_request_amount
from erpnext.accounts.doctype.tax_withholding_category.tax_withholding_category import get_party_tax_withholding_details


from erpnext.accounts.doctype.payment_request import payment_request as PR

from erpnext.accounts.party import get_party_bank_account
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_accounting_dimensions,
)
from frappe.utils.data import flt, today


class BankPaymentRequest(PaymentRequest):
	def validate_subscription_details(self):
		pass

	def validate(self):
		if self.apply_tax_withholding_amount and self.tax_withholding_category and self.payment_request_type == "Outward":
			if not self.net_total:
				self.net_total = self.grand_total
			tds_amount = self.calculate_pr_tds(self.net_total)
			self.taxes_deducted = tds_amount
			self.grand_total = self.net_total - self.taxes_deducted
		else:
			if self.net_total and not self.grand_total:
				self.grand_total = self.net_total
			if self.grand_total and self.net_total != self.grand_total and not self.apply_tax_withholding_amount:
				self.grand_total = self.net_total

		if not self.is_adhoc:
			super().validate()
		else:
			if self.get("__islocal"):
				self.status = "Draft"
			if self.reference_doctype or self.reference_name:
				frappe.throw("Payments with references cannot be marked as ad-hoc")

		self.valdidate_bank_for_wire_transfer()

	def validate_payment_request_amount(self):
		existing_payment_request_amount = flt(
			get_existing_payment_request_amount(self.reference_doctype, self.reference_name)
		)

		docname = None
		if frappe.flags.update_amount or not self.is_new():
			docname = self.name

		existing_payment_request_amount_drafted = flt(
			get_existing_payment_request_amount(self.reference_doctype, self.reference_name, submitted=False, update=docname)
		)

		total_existing_payment_request_amount = existing_payment_request_amount + existing_payment_request_amount_drafted


		ref_doc = frappe.get_doc(self.reference_doctype, self.reference_name)

		if not hasattr(ref_doc, "order_type") or getattr(ref_doc, "order_type") != "Shopping Cart":
			if self.reference_doctype in ["Purchase Order"]:
				ref_amount = flt(ref_doc.rounded_total) or flt(ref_doc.grand_total)
			elif self.reference_doctype in ["Purchase Invoice"]:
				ref_amount = flt(ref_doc.base_rounded_total)
			else:
				ref_amount = get_amount(ref_doc, self.payment_account)

			if total_existing_payment_request_amount + flt(self.net_total) > ref_amount:
				frappe.throw(
					frappe._("Total Bank Payment Request amount cannot be greater than {0} amount").format(
						self.reference_doctype
					)
				)

	def on_submit(self):
		debit_account = None
		if self.payment_type:
			debit_account = frappe.db.get_value("Payment Type", self.payment_type, "account")
		elif self.reference_doctype == "Purchase Invoice":
			debit_account = frappe.db.get_value(self.reference_doctype, self.reference_name, "credit_to")

		if not debit_account:
			frappe.throw("Debit account for Payment Type <b>{}</b> cannot be determined".format(self.payment_type))
		if not self.is_adhoc:
			super().on_submit()
		else:
			if self.payment_request_type == "Outward":
				self.db_set("status", "Initiated")
				return

	def create_payment_entry(self, submit=True):
		payment_entry = super().create_payment_entry(submit=submit)
		payment_entry.source_doctype = self.payment_order_type
		if payment_entry.docstatus != 1 and self.payment_type:
			payment_entry.paid_to = frappe.db.get_value("Payment Type", self.payment_type, "account") or ""

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
			frappe.throw(frappe._("Bank Account is missing for Wire Transfer Payments"))


@frappe.whitelist()
def validate_payment_request_status(**args):
	total_bank_payment_request_amount = frappe.db.get_all(
		"Bank Payment Request", {
			"reference_doctype": args.get('ref_doctype'),
			"reference_name": args.get('ref_name'),
			"docstatus": 1
		},
		"sum(grand_total) as grand_total")

	if total_bank_payment_request_amount[0] and total_bank_payment_request_amount[0].get('grand_total'):
		if flt(total_bank_payment_request_amount[0].get('grand_total')) >= flt(args.get('grand_total')):
			return 'Completed'

	return ""


@frappe.whitelist(allow_guest=True)
def make_bank_payment_request(**args):
	"""Make Bank payment request"""

	args = frappe._dict(args)

	ref_doc = frappe.get_doc(args.dt, args.dn)
	gateway_account = PR.get_gateway_details(args) or frappe._dict()

	grand_total = get_amount(ref_doc, gateway_account.get("payment_account"))

	bank_account = (
		get_party_bank_account(args.get("party_type"), args.get("party")) if args.get("party_type") else ""
	)

	if not bank_account:
		frappe.throw(frappe._("Default Bank Account is missing for {0} - {1}").format(args.get("party_type"), args.get("party")))

	draft_payment_request = frappe.db.get_value(
		"Bank Payment Request",
		{"reference_doctype": args.dt, "reference_name": args.dn, "docstatus": 0},
	)
	
	existing_payment_request_amount = get_existing_payment_request_amount(args.dt, args.dn)

	if existing_payment_request_amount:
		grand_total -= existing_payment_request_amount

	if draft_payment_request:
		bpr = frappe.get_doc("Bank Payment Request", draft_payment_request)
		bpr.db_set("net_total", grand_total, update_modified=False)
		bpr.validate()
		frappe.db.set_value(
			"Bank Payment Request", draft_payment_request, {
				"net_total": bpr.net_total,
				"grand_total": bpr.grand_total,
				"taxes_deducted": bpr.taxes_deducted
				},
			update_modified=False
		)

	else:
		bpr = frappe.new_doc("Bank Payment Request")

		if not args.get("payment_request_type"):
			args["payment_request_type"] = (
				"Outward" if args.get("dt") in ["Purchase Order", "Purchase Invoice"] else "Inward"
			)

		bpr.payment_type = "Pay"

		bpr.update(
			{
				"payment_gateway_account": gateway_account.get("name"),
				"payment_gateway": gateway_account.get("payment_gateway"),
				"payment_account": gateway_account.get("payment_account"),
				"payment_channel": gateway_account.get("payment_channel"),
				"payment_request_type": args.get("payment_request_type"),
				"currency": ref_doc.currency,
				"company": ref_doc.company,
				"grand_total": grand_total,
				"mode_of_payment": "Wire Transfer",
				"transaction_date": today(),
				"email_to": args.recipient_id or ref_doc.owner,
				"subject": frappe._("Bank Payment Request for {0}").format(args.dn),
				"message": gateway_account.get("message") or PR.get_dummy_message(ref_doc),
				"reference_doctype": args.dt,
				"reference_name": args.dn,
				"party_type": args.get("party_type") or "Customer",
				"party": args.get("party") or ref_doc.get("customer"),
				"bank_account": bank_account,
				"net_total": grand_total
			}
		)

		# Update dimensions
		bpr.update(
			{
				"cost_center": ref_doc.get("cost_center") or 
    				frappe.get_value(ref_doc.get("doctype") + " Item",
                        {'parent': ref_doc.get("name")}, 'cost_center'
                    ),
				"project": ref_doc.get("project") or 
    				frappe.get_value(ref_doc.get("doctype") + " Item",
                        {'parent': ref_doc.get("name")}, 'project'
                	)
			}
		)

		for dimension in get_accounting_dimensions():
			bpr.update({dimension: ref_doc.get(dimension)})

		bpr.insert(ignore_permissions=True)

		if args.submit_doc:
			bpr.submit()

	if args.return_doc:
		return bpr

	return bpr.as_dict()

@frappe.whitelist()
def make_payment_order(source_name, target_doc=None, args= None):
	from frappe.model.mapper import get_mapped_doc

	def set_missing_values(source, target):
		target.payment_order_type = "Bank Payment Request"
		account = ""
		if source.payment_type:
			account = frappe.db.get_value("Payment Type", source.payment_type, "account")
		if source.reference_doctype == "Purchase Invoice":
			account = frappe.db.get_value(source.reference_doctype, source.reference_name, "credit_to")

		for dimension in get_accounting_dimensions():
			target.update({dimension: source.get(dimension, '')})

		target.append(
			"references",
			{
				"reference_doctype": source.reference_doctype,
				"reference_name": source.reference_name,
				"amount": source.grand_total,
				"party_type": source.party_type,
				"party": source.party,
				"bank_payment_request": source_name,
				"mode_of_payment": source.mode_of_payment,
				"bank_account": source.bank_account,
				"account": account,
				"is_adhoc": source.is_adhoc,
				"cost_center": source.cost_center,
				"project": source.project,
				"tax_withholding_category": source.tax_withholding_category
			},
		)
		target.status = "Pending"

	def update_missing_values(source, target):
		target.payment_order_type = "Payment Entry"
		target.company_bank_account = source.bank_account

		account = ""
		if source.paid_to:
			account = source.paid_to

		for dimension in get_accounting_dimensions():
			target.update({dimension: source.get(dimension, '')})

		if source.references:
			target.append(
				"references",
				{
					"reference_doctype": source.references[0].reference_doctype,
					"reference_name": source.references[0].reference_name,
					"amount": source.references[0].total_amount,
					"party_type": source.party_type,
					"party": source.party,
					"mode_of_payment": source.mode_of_payment,
					"bank_account": get_party_bank_account(source.get("party_type"), source.get("party")) if source.get("party_type") else "",
					"account": account,
					"cost_center": source.cost_center,
					"project": source.project,
					"payment_entry":  source.name
				}
			)
		else:
			target.append(
				"references",
				{
					"reference_doctype": "Payment Entry",
					"reference_name": source.name,
					"amount": source.paid_amount,
					"party_type": source.party_type,
					"party": source.party,
					"mode_of_payment": "Wire Transfer",
					"bank_account": source.party_bank_account,
					"account": source.paid_to,
					"cost_center": source.cost_center,
					"project": source.project,
					"payment_entry":  source.name
				}
			)
		target.status = "Pending"

	if args.get('ref_doctype') != "Payment Entry":
		doclist = get_mapped_doc(
			"Bank Payment Request",
			source_name,
			{
				"Bank Payment Request": {
					"doctype": "Payment Order",
				}
			},
			target_doc,
			set_missing_values,
		)
	else:
		doclist = get_mapped_doc(
			"Payment Entry",
			source_name,
			{
				"Payment Entry": {
					"doctype": "Payment Order",
				}
			},
			target_doc,
			update_missing_values,
		)

	return doclist

def get_existing_payment_request_amount(ref_dt, ref_dn, submitted= True, update=None):
	"""
	Get the existing Bank payment request which are unpaid or partially paid for payment channel other than Phone
	and get the summation of existing paid Bank payment request for Phone payment channel.
	"""

	docstatus = 1 if submitted else 0

	existing_payment_request_amount = frappe.db.sql(
		"""
		select sum(net_total)
		from `tabBank Payment Request`
		where
			name != %s
			and reference_doctype = %s
			and reference_name = %s
			and docstatus = %s
			and (status != 'Paid'
			or (payment_channel = 'Phone'
				and status = 'Paid'))
	""",
		(update or "", ref_dt, ref_dn, docstatus)
	)
	return flt(existing_payment_request_amount[0][0]) if existing_payment_request_amount else 0

def get_amount(ref_doc, payment_account=None):
	"""get amount based on doctype"""
	dt = ref_doc.doctype
	if dt in ["Sales Order", "Purchase Order"]:
		grand_total = flt(ref_doc.rounded_total) or flt(ref_doc.grand_total)
	elif dt in ["Sales Invoice", "Purchase Invoice"]:
		if not ref_doc.get("is_pos"):
			if ref_doc.party_account_currency == ref_doc.currency:
				grand_total = flt(ref_doc.grand_total)
			else:
				grand_total = flt(ref_doc.base_grand_total) / ref_doc.conversion_rate
		elif dt == "Sales Invoice":
			for pay in ref_doc.payments:
				if pay.type == "Phone" and pay.account == payment_account:
					grand_total = pay.amount
					break
	elif dt == "POS Invoice":
		for pay in ref_doc.payments:
			if pay.type == "Phone" and pay.account == payment_account:
				grand_total = pay.amount
				break
	elif dt == "Fees":
		grand_total = ref_doc.outstanding_amount

	if grand_total > 0:
		return grand_total
	else:
		frappe.throw(frappe._("Bank Payment Entry is already created"))
