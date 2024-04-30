# Copyright (c) 2024, Aerele Technologies Private Limited and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from erpnext.accounts.doctype.payment_request.payment_request import PaymentRequest

from erpnext.accounts.doctype.payment_request import payment_request as PR

from erpnext.accounts.party import get_party_bank_account
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_accounting_dimensions,
)


class BankPaymentRequest(PaymentRequest):
	pass

@frappe.whitelist(allow_guest=True)
def make_bank_payment_request(**args):
	"""Make Bank payment request"""

	args = frappe._dict(args)

	ref_doc = frappe.get_doc(args.dt, args.dn)
	gateway_account = PR.get_gateway_details(args) or frappe._dict()

	grand_total = PR.get_amount(ref_doc, gateway_account.get("payment_account"))
	if args.loyalty_points and args.dt == "Sales Order":
		from erpnext.accounts.doctype.loyalty_program.loyalty_program import validate_loyalty_points

		loyalty_amount = validate_loyalty_points(ref_doc, int(args.loyalty_points))
		frappe.db.set_value(
			"Sales Order", args.dn, "loyalty_points", int(args.loyalty_points), update_modified=False
		)
		frappe.db.set_value("Sales Order", args.dn, "loyalty_amount", loyalty_amount, update_modified=False)
		grand_total = grand_total - loyalty_amount

	bank_account = (
		get_party_bank_account(args.get("party_type"), args.get("party")) if args.get("party_type") else ""
	)

	draft_payment_request = frappe.db.get_value(
		"Payment Request",
		{"reference_doctype": args.dt, "reference_name": args.dn, "docstatus": 0},
	)

	existing_payment_request_amount = PR.get_existing_payment_request_amount(args.dt, args.dn)

	if existing_payment_request_amount:
		grand_total -= existing_payment_request_amount

	if draft_payment_request:
		frappe.db.set_value(
			"Payment Request", draft_payment_request, "grand_total", grand_total, update_modified=False
		)
		bpr = frappe.get_doc("Bank Payment Request", draft_payment_request)
	else:
		bpr = frappe.new_doc("Bank Payment Request")

		if not args.get("payment_request_type"):
			args["payment_request_type"] = (
				"Outward" if args.get("dt") in ["Purchase Order", "Purchase Invoice"] else "Inward"
			)

		bpr.update(
			{
				"payment_gateway_account": gateway_account.get("name"),
				"payment_gateway": gateway_account.get("payment_gateway"),
				"payment_account": gateway_account.get("payment_account"),
				"payment_channel": gateway_account.get("payment_channel"),
				"payment_request_type": args.get("payment_request_type"),
				"currency": ref_doc.currency,
				"grand_total": grand_total,
				"mode_of_payment": args.mode_of_payment,
				"email_to": args.recipient_id or ref_doc.owner,
				"subject": frappe._("Babk Payment Request for {0}").format(args.dn),
				"message": gateway_account.get("message") or PR.get_dummy_message(ref_doc),
				"reference_doctype": args.dt,
				"reference_name": args.dn,
				"party_type": args.get("party_type") or "Customer",
				"party": args.get("party") or ref_doc.get("customer"),
				"bank_account": bank_account,
			}
		)

		# Update dimensions
		bpr.update(
			{
				"cost_center": ref_doc.get("cost_center"),
				"project": ref_doc.get("project"),
			}
		)

		for dimension in get_accounting_dimensions():
			bpr.update({dimension: ref_doc.get(dimension)})

		if args.order_type == "Shopping Cart" or args.mute_email:
			bpr.flags.mute_email = True

		bpr.insert(ignore_permissions=True)
		if args.submit_doc:
			bpr.submit()

	if args.order_type == "Shopping Cart":
		frappe.db.commit()
		frappe.local.response["type"] = "redirect"
		frappe.local.response["location"] = bpr.get_payment_url()

	if args.return_doc:
		return bpr

	return bpr.as_dict()

@frappe.whitelist()
def make_payment_order(source_name, target_doc=None):
	print(source_name, "source_name")
	from frappe.model.mapper import get_mapped_doc

	def set_missing_values(source, target):
		target.payment_order_type = "Bank Payment Request"
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
				"custom_bank_payment_request": source_name,
				"mode_of_payment": source.mode_of_payment,
				"bank_account": source.bank_account,
				"account": account,
				"is_adhoc": source.is_adhoc,
				# "state": source.state,
				"cost_center": source.cost_center,
				"project": source.project,
				"tax_withholding_category": source.tax_withholding_category,
			},
		)
		target.status = "Pending"

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

	return doclist

