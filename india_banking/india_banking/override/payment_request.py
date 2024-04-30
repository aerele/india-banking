import frappe
from erpnext.accounts.doctype.payment_request.payment_request import PaymentRequest, get_existing_payment_request_amount, get_amount
from erpnext.accounts.doctype.tax_withholding_category.tax_withholding_category import get_party_tax_withholding_details
from frappe import _
from frappe.utils import flt, today

class CustomPaymentRequest(PaymentRequest):
	def validate(self):
		if not self.is_adhoc:
			super().validate()
		else:
			if self.get("__islocal"):
				self.status = "Draft"
			if self.reference_doctype or self.reference_name:
				frappe.throw("Payments with references cannot be marked as ad-hoc")

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

	def validate_payment_request_amount(self):
		existing_payment_request_amount = flt(
			get_existing_payment_request_amount(self.reference_doctype, self.reference_name)
		)

		ref_doc = frappe.get_doc(self.reference_doctype, self.reference_name)
		if not hasattr(ref_doc, "order_type") or getattr(ref_doc, "order_type") != "Shopping Cart":
			if self.reference_doctype in ["Purchase Order"]:
				ref_amount = flt(ref_doc.rounded_total) or flt(ref_doc.grand_total)
			elif self.reference_doctype in ["Purchase Invoice"]:
				ref_amount = flt(ref_doc.base_rounded_total)
			else:
				ref_amount = get_amount(ref_doc, self.payment_account)

			if existing_payment_request_amount + flt(self.grand_total) > ref_amount:
				frappe.throw(
					_("Total Payment Request amount cannot be greater than {0} amount").format(
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
			frappe.throw("Unable to determine debit account")
		if not self.is_adhoc:
			super().on_submit()
		else:
			if self.payment_request_type == "Outward":
				self.db_set("status", "Initiated")
				return

	def create_payment_entry(self, submit=True):
		payment_entry = super().create_payment_entry(submit=submit)
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
		
@frappe.whitelist(allow_guest=True)
def make_payment_request(**args):
	"""Make payment request"""
	from erpnext.accounts.doctype.payment_request.payment_request import (
		get_gateway_details, 
		get_amount, 
		get_existing_payment_request_amount,
		get_dummy_message
	)
	from erpnext.accounts.party import get_party_bank_account
	from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import get_accounting_dimensions

	args = frappe._dict(args)

	ref_doc = frappe.get_doc(args.dt, args.dn)
	gateway_account = get_gateway_details(args) or frappe._dict()

	if args.dt in ["Purchase Order"]:
		grand_total = flt(ref_doc.rounded_total) or flt(ref_doc.grand_total)
	elif args.dt in ["Purchase Invoice"]:
		grand_total = flt(ref_doc.base_rounded_total)
	else:
		grand_total = get_amount(ref_doc, gateway_account.get("payment_account"))

	if args.loyalty_points and args.dt == "Sales Order":
		from erpnext.accounts.doctype.loyalty_program.loyalty_program import validate_loyalty_points

		loyalty_amount = validate_loyalty_points(ref_doc, int(args.loyalty_points))
		frappe.db.set_value(
			"Sales Order", args.dn, "loyalty_points", int(args.loyalty_points), update_modified=False
		)
		frappe.db.set_value(
			"Sales Order", args.dn, "loyalty_amount", loyalty_amount, update_modified=False
		)
		grand_total = grand_total - loyalty_amount

	bank_account = (
		get_party_bank_account(args.get("party_type"), args.get("party"))
		if args.get("party_type")
		else ""
	)

	draft_payment_request = frappe.db.get_value(
		"Payment Request",
		{"reference_doctype": args.dt, "reference_name": args.dn, "docstatus": 0},
	)

	existing_payment_request_amount = get_existing_payment_request_amount(args.dt, args.dn)

	if existing_payment_request_amount:
		grand_total -= existing_payment_request_amount

	if draft_payment_request:
		frappe.db.set_value(
			"Payment Request", draft_payment_request, "grand_total", grand_total, update_modified=False
		)
		frappe.db.set_value(
			"Payment Request", draft_payment_request, "net_total", grand_total, update_modified=False
		)
		pr = frappe.get_doc("Payment Request", draft_payment_request)
	else:
		pr = frappe.new_doc("Payment Request")
		pr.update(
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
				"subject": _("Payment Request for {0}").format(args.dn),
				"message": gateway_account.get("message") or get_dummy_message(ref_doc),
				"reference_doctype": args.dt,
				"reference_name": args.dn,
				"party_type": args.get("party_type") or "Customer",
				"party": args.get("party") or ref_doc.get("customer"),
				"bank_account": bank_account,
				"net_total": grand_total
			}
		)

		# Update dimensions
		pr.update(
			{
				"cost_center": ref_doc.get("cost_center"),
				"project": ref_doc.get("project"),
			}
		)

		for dimension in get_accounting_dimensions():
			pr.update({dimension: ref_doc.get(dimension)})

		if args.order_type == "Shopping Cart" or args.mute_email:
			pr.flags.mute_email = True

		pr.insert(ignore_permissions=True)
		if args.submit_doc:
			pr.submit()

	if args.order_type == "Shopping Cart":
		frappe.db.commit()
		frappe.local.response["type"] = "redirect"
		frappe.local.response["location"] = pr.get_payment_url()

	if args.return_doc:
		return pr

	return pr.as_dict()