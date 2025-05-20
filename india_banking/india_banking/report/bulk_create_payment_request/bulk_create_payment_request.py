# Copyright (c) 2025, Aerele Technologies Private Limited and contributors
# For license information, please see license.txt


import json

import frappe
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_accounting_dimensions,
)
from erpnext.accounts.doctype.payment_request.payment_request import (
	get_dummy_message,
	get_gateway_details,
)
from erpnext.accounts.party import get_party_account, get_party_bank_account
from erpnext.accounts.report.accounts_receivable.accounts_receivable import (
	ReceivablePayableReport,
)
from erpnext.accounts.utils import get_account_currency
from frappe import _, scrub
from frappe.model.document import Document
from frappe.query_builder.functions import Abs, Sum
from frappe.utils import cstr, flt, today

from india_banking.utils import add_background_job

ENQUEUE_LIMIT = 50


def execute(filters=None):
	args = {
		"account_type": "Payable",
		"naming_by": ["Buying Settings", "supp_master_name"],
	}
	return CustomPayableReport(filters).run(args)


class CustomPayableReport(ReceivablePayableReport):
	def __init__(self, filters=None):
		self.filters = frappe._dict(filters or {})
		if self.filters._for != "Order Advance":
			return super().__init__(filters)

	def run(self, args):
		if self.filters._for == "Order Advance":
			self.party_naming_by = frappe.db.get_value(
				args.get("naming_by")[0], None, args.get("naming_by")[1]
			)
			self.get_columns()
			self.get_data()
			self.order_term_details = {}
			return self.columns, self.data
		return super().run(args)

	def add_column(
		self,
		label,
		fieldname=None,
		fieldtype="Currency",
		options=None,
		width=120,
		ignore=False,
	):
		if not fieldname:
			fieldname = scrub(label)
		if fieldtype == "Currency":
			options = "currency"
		if fieldtype == "Date" and not width:
			width = 90
		if not ignore:
			self.columns.append(
				dict(
					label=label,
					fieldname=fieldname,
					fieldtype=fieldtype,
					options=options,
					width=width,
				)
			)

	def append_row(self, row):
		self.allocate_future_payments(row)
		self.set_invoice_details(row)
		self.set_party_details(row)
		self.set_ageing(row)
		self.set_payment_request_details(row)

		if self.filters.get("group_by_party"):
			self.update_sub_total_row(row, row.party)
			if self.previous_party and (self.previous_party != row.party):
				self.append_subtotal_row(self.previous_party)
			self.previous_party = row.party

		self.data.append(row)

	def set_payment_request_details(self, row):
		if row.voucher_type == "Purchase Invoice":
			(
				row.requested_amount,
				row.requested_amount_in_draft,
			) = self.get_payment_requested_amount(
				row.voucher_type, row.voucher_no, row.payment_term
			)

	def get_payment_requested_amount(self, doctype, docname, payment_term=None):
		PR = frappe.qb.DocType("Payment Request")

		query = (
			frappe.qb.from_(PR)
			.select(
				Abs(
					Sum(
						frappe.qb.terms.Case()
						.when(
							(PR.status.eq("Initiated") & PR.docstatus.eq(1)),
							PR.grand_total,
						)
						.else_(0)
					)
				).as_("requested"),
				Abs(
					Sum(
						frappe.qb.terms.Case()
						.when(PR.docstatus.eq(0), PR.grand_total)
						.else_(0)
					)
				).as_("draft_requested"),
			)
			.where(PR.reference_doctype.eq(doctype))
			.where(PR.reference_name.eq(docname))
			.where(PR.payment_request_type.eq("Outward"))
		)

		if payment_term:
			query = query.where(PR.payment_term.eq(payment_term))

		response = query.run()
		# requested and requested in draft
		return (
			(flt(response[0][0]), flt(response[0][1])) if response else (0, 0)
		)  # If response is empty consider default as (0, 0)

	def get_columns(self):
		self.columns = []

		label = _("Posting Date")
		fieldname = "posting_date"
		if self.filters._for == "Order Advance":
			label = _("Transaction Date")
			fieldname = "transaction_date"
		self.add_column(label=label, fieldname=fieldname, fieldtype="Date", width=180)
		self.add_column(
			label=_("Party Type"),
			fieldname="party_type",
			fieldtype="Data",
			width=100,
			ignore=self.filters._for == "Order Advance",
		)
		label = _("Party")
		fieldname = "party"
		fieldtype = "Dynamic Link"
		options = "party_type"
		if self.filters._for == "Order Advance":
			label = _("Supplier")
			fieldname = "supplier"
			fieldtype = "Link"
			options = "Supplier"
		self.add_column(
			label=label,
			fieldname=fieldname,
			fieldtype=fieldtype,
			options=options,
			width=180,
		)
		self.add_column(
			label=_("Payable Account"),
			fieldname="party_account",
			fieldtype="Link",
			options="Account",
			width=180,
			ignore=self.filters._for == "Order Advance",
		)

		if self.party_naming_by == "Naming Series":
			self.add_column(
				label=_("Supplier Name"),
				fieldname="supplier_name",
				fieldtype="Data",
			)

		self.add_column(
			label=_("Cost Center"), fieldname="cost_center", fieldtype="Data"
		)
		self.add_column(
			label=_("Voucher Type"),
			fieldname="voucher_type",
			fieldtype="Data",
			ignore=self.filters._for == "Order Advance",
		)

		label = _("Voucher No")
		fieldname = "voucher_no"
		fieldtype = "Dynamic Link"
		options = "voucher_type"
		if self.filters._for == "Order Advance":
			label = _("Purchase Order")
			fieldname = "purchase_order"
			fieldtype = "Link"
			options = "Purchase Order"
		self.add_column(
			label=label,
			fieldname=fieldname,
			fieldtype=fieldtype,
			options=options,
			width=200,
		)
		label = (_("Due Date"),)
		fieldname = ("due_date",)
		if self.filters._for == "Order Advance":
			label = _("Required By")
			fieldname = ("schedule_date",)
		self.add_column(label=label, fieldname=fieldname, fieldtype="Date")

		self.add_column(
			label=_("Bill No"),
			fieldname="bill_no",
			fieldtype="Data",
			ignore=self.filters._for == "Order Advance",
		)
		self.add_column(
			label=_("Bill Date"),
			fieldname="bill_date",
			fieldtype="Date",
			ignore=self.filters._for == "Order Advance",
		)

		if self.filters.based_on_payment_terms:
			self.add_column(
				label=_("Payment Term"), fieldname="payment_term", fieldtype="Data"
			)
			label = _("Invoice Grand Total")
			fieldname = "invoice_grand_total"
			if self.filters._for == "Order Advance":
				label = _("Order Grand Total")
				fieldname = "order_grand_total"

			self.add_column(label=label, fieldname=fieldname)

		label = _("Invoiced Amount")
		fieldname = "invoiced"
		if self.filters._for == "Order Advance":
			label = _("Grand Total")
			fieldname = "ordered"
		self.add_column(label=label, fieldname=fieldname)

		label = _("Paid Amount")
		fieldname = "paid"
		if self.filters._for == "Order Advance":
			label = _("Advance Paid")
			fieldname = "advance_paid"
		self.add_column(label=label, fieldname=fieldname)
		self.add_column(
			label=_("Debit Note"),
			fieldname="credit_note",
			ignore=self.filters._for == "Order Advance",
		)

		self.add_column(label=_("Outstanding Amount"), fieldname="outstanding")
		self.add_column(
			label=_("Requested(Draft)"),
			fieldname="requested_amount_in_draft",
			width=180,
		)
		self.add_column(
			label=_("Requested(Submitted)"), fieldname="requested_amount", width=180
		)
		if self.filters._for != "Order Advance":
			self.add_column(
				label=_("Age (Days)"), fieldname="age", fieldtype="Int", width=80
			)
			self.setup_ageing_columns()

			self.add_column(
				label=_("Currency"),
				fieldname="currency",
				fieldtype="Link",
				options="Currency",
				width=80,
			)

			if self.filters.show_future_payments:
				self.add_column(
					label=_("Future Payment Ref"),
					fieldname="future_ref",
					fieldtype="Data",
				)
				self.add_column(
					label=_("Future Payment Amount"), fieldname="future_amount"
				)
				self.add_column(
					label=_("Remaining Balance"), fieldname="remaining_balance"
				)

			self.add_column(
				label=_("Supplier Group"),
				fieldname="supplier_group",
				fieldtype="Link",
				options="Supplier Group",
				ignore=self.filters._for == "Order Advance",
			)

		if self.filters.show_remarks:
			self.add_column(
				label=_("Remarks"),
				fieldname="remarks",
				fieldtype="Text",
				width=200,
				ignore=self.filters._for == "Order Advance",
			)

	def append_payment_term(self, row, d, term, company_currency):
		invoiced = d.base_payment_amount
		paid_amount = d.base_paid_amount

		if company_currency == d.party_account_currency or self.filters.get(
			"in_party_currency"
		):
			invoiced = d.payment_amount
			paid_amount = d.paid_amount

		row.payment_terms.append(
			term.update(
				{
					"due_date": d.due_date,
					"invoiced": invoiced,
					"invoice_grand_total": row.invoiced,
					"payment_term": d.payment_term,
					"paid": paid_amount + d.discounted_amount,
					"credit_note": 0.0,
					"outstanding": invoiced - paid_amount - d.discounted_amount,
				}
			)
		)

		if paid_amount:
			row["paid"] -= paid_amount + d.discounted_amount

	def get_data(self):
		self.data = []
		if self.filters._for != "Order Advance":
			return super().get_data()

		PO = frappe.qb.DocType("Purchase Order")

		query = (
			frappe.qb.from_(PO)
			.select(
				PO.name.as_("purchase_order"),
				PO.transaction_date,
				PO.supplier,
				PO.supplier_name,
				PO.grand_total.as_("ordered"),
				PO.advance_paid,
				PO.cost_center,
				PO.schedule_date,
				PO.payment_terms_template,
				(PO.grand_total - PO.advance_paid).as_("outstanding"),
			)
			.where(PO.docstatus.eq(1))
			.where(PO.status.notin(["Completed", "Closed", "On Hold"]))
			.where(PO.per_billed < 100)
			.where((PO.grand_total - PO.advance_paid) > 0)
			.orderby(PO.name)
		)

		if posting_date := self.filters.report_date:
			query.where(PO.transaction_date.eq(posting_date))
		else:
			query.where(PO.transaction_date.eq(today()))

		if not self.filters.future_payments:
			query.where(PO.due_date < today())

		if self.filters.party:
			query.where(PO.supplier.eq(self.filters.party))

		order_data = query.run(as_dict=True)
		self.allocate_order_outstanding_based_on_payment_terms(order_data)

	def allocate_order_outstanding_based_on_payment_terms(self, order_data):
		for row in order_data:
			if self.filters.based_on_payment_terms and row.payment_terms_template:
				self.set_order_term_details(row)
			else:
				(
					row.requested_amount,
					row.requested_amount_in_draft,
				) = self.get_payment_requested_amount(
					"Purchase Order", row.purchase_order
				)
				row["order_grand_total"] = row["ordered"]
				row["outstanding"] -= row.requested_amount
				self.data.append(row)

	def set_order_term_details(self, row):
		PS = frappe.qb.DocType("Payment Schedule")

		order_terms_details = (
			frappe.qb.from_(PS)
			.select(
				PS.due_date.as_("schedule_date"),
				PS.payment_term,
				PS.payment_amount,
				PS.base_payment_amount,
				PS.description,
				PS.paid_amount,
				PS.base_paid_amount,
				PS.discounted_amount,
				PS.outstanding,
			)
			.where(
				(PS.parent == row.purchase_order) & (PS.parenttype == "Purchase Order")
			)
			.orderby(PS.due_date, order=frappe.qb.desc)
		).run(as_dict=True)

		company_currency = frappe.get_value(
			"Company", self.filters.get("company"), "default_currency"
		)
		original_row = row

		if len(order_terms_details) == 1 and order_terms_details[0].payment_term:
			term = frappe._dict(order_terms_details[0])
			term_row = self.get_term_row(
				term, order_terms_details[0], original_row, company_currency
			)
			self.data.append(term_row)
			return
		term_rows = []

		total_term_outstanding = 0
		for terms_details in order_terms_details:
			term = frappe._dict(row)
			term_row = self.get_term_row(
				term, terms_details, original_row, company_currency
			)
			term_rows.append(term_row)
			total_term_outstanding += term_row["outstanding"]

		# ignores invalid orders
		if total_term_outstanding <= row["outstanding"]:
			for term_row in term_rows:
				self.data.append(term_row)

	def get_term_row(self, term, terms_details, row, company_currency):
		ordered = terms_details.base_payment_amount
		paid_amount = terms_details.base_paid_amount

		if company_currency == terms_details.party_account_currency or self.filters.get(
			"in_party_currency"
		):
			ordered = terms_details.payment_amount
			paid_amount = terms_details.paid_amount

		term.update(
			{
				"due_date": terms_details.due_date,
				"ordered": ordered,
				"order_grand_total": row.ordered,
				"payment_term": terms_details.payment_term,
				"advance_paid": paid_amount + terms_details.discounted_amount,
			}
		)
		(
			term.requested_amount,
			term.requested_amount_in_draft,
		) = self.get_payment_requested_amount(
			"Purchase Order", row.purchase_order, terms_details.payment_term
		)

		term["outstanding"] = (
			ordered
			- paid_amount
			- terms_details.discounted_amount
			- term.requested_amount
		)

		return term


@frappe.whitelist()
def create_bulk_payment_request(invoices, filters=None) -> Document:
	def _is_valid_invoice(invoice):
		if invoice.voucher_type != "Purchase Invoice":
			return False

		return True

	if isinstance(invoices, str):
		invoices = json.loads(invoices)
	if isinstance(filters, str):
		filters = json.loads(filters)

	if not invoices:
		return []

	if filters.get("_for") == "Order Advance":
		return create_bulk_payment_request_for_order(orders=invoices, filters=filters)

	count = 0
	zero_outstanding = 0
	for invoice in invoices:
		invoice = frappe._dict(invoice)
		if not _is_valid_invoice(invoice):
			continue

		outstanding = flt(invoice.outstanding) - flt(invoice.requested_amount)
		payment_details = {
			"payment_request_type": "Outward",
			"company": filters.get("company"),
			"mode_of_payment": "Wire Transfer",
			"payment_type": frappe.db.exists(
				"Payment Type", {"company": filters.get("company"), "is_default": 1}
			),
			"party_type": invoice.party_type,
			"party": invoice.party,
			"reference_doctype": invoice.voucher_type,
			"reference_name": invoice.voucher_no,
			"net_total": outstanding,
			"payment_term": invoice.payment_term,
		}

		if not outstanding:
			zero_outstanding += 1
		else:
			if len(invoices) > ENQUEUE_LIMIT:
				job_id = invoice.voucher_no + cstr(invoice.payment_term)
				job_name = invoice.voucher_no + "-" + cstr(invoice.payment_term)
				method = make_payment_request
				add_background_job(job_id, job_name, method, **payment_details)
			else:
				make_payment_request(**payment_details)
			count += 1

	if count:
		msg = "{} Row Updated".format(count)
		if len(invoices) > ENQUEUE_LIMIT:
			msg = "{} Row added in background job".format(count)
		frappe.msgprint(msg)
	if not count and zero_outstanding:
		frappe.msgprint("No more outstanding invoice to Pay")


def create_bulk_payment_request_for_order(orders, filters=None):
	count = 0
	zero_outstanding = 0
	for order in orders:
		if not order:
			continue

		order = frappe._dict(order)

		payment_details = {
			"payment_request_type": "Outward",
			"company": filters.get("company"),
			"mode_of_payment": "Wire Transfer",
			"payment_type": frappe.db.exists(
				"Payment Type", {"company": filters.get("company"), "is_default": 1}
			),
			"party_type": "Supplier",
			"party": order.supplier,
			"reference_doctype": "Purchase Order",
			"reference_name": order.purchase_order,
			"net_total": order.outstanding,
			"payment_term": order.payment_term,
		}

		if not order.outstanding:
			zero_outstanding += 1
		else:
			if len(orders) > ENQUEUE_LIMIT:
				job_id = order.purchase_order + cstr(order.payment_term)
				job_name = order.purchase_order + "-" + cstr(order.payment_term)
				method = make_payment_request
				add_background_job(job_id, job_name, method, **payment_details)
			else:
				make_payment_request(**payment_details)
			count += 1

	if count:
		msg = "{} Row Updated".format(count)
		if len(orders) > ENQUEUE_LIMIT:
			msg = "{} Row added in background job".format(count)
		frappe.msgprint(msg)
	if not count and zero_outstanding:
		frappe.msgprint("No more outstanding invoice to Pay")


@frappe.whitelist(allow_guest=True)
def make_payment_request(**args):
	"""Make payment request"""

	args = frappe._dict(args)

	ref_doc = frappe.get_doc(args.reference_doctype, args.reference_name)
	gateway_account = get_gateway_details(args) or frappe._dict()

	grand_total = args.net_total

	bank_account = (
		get_party_bank_account(args.get("party_type"), args.get("party"))
		if args.get("party")
		else ""
	)

	req_filters = {
		"reference_doctype": args.reference_doctype,
		"reference_name": args.reference_name,
		"docstatus": 0,
	}

	if args.payment_term:
		req_filters.update({"payment_term": args.payment_term})

	draft_payment_request = frappe.db.get_value(
		"Payment Request",
		req_filters,
	)

	if grand_total <= 0:
		return

	if draft_payment_request:
		pr = frappe.get_doc("Payment Request", draft_payment_request)
		pr.net_total = grand_total
		pr.save()

	else:
		pr = frappe.new_doc("Payment Request")

		if not args.get("payment_request_type"):
			args["payment_request_type"] = "Outward"

		party_type = "Supplier"
		party_account_currency = ref_doc.get("party_account_currency")

		if not party_account_currency:
			party_account = get_party_account(
				party_type, ref_doc.get(party_type.lower()), ref_doc.company
			)
			party_account_currency = get_account_currency(party_account)

		pr.status = "Initiated"
		pr.payment_term = args.payment_term

		pr.update(
			{
				"payment_gateway_account": gateway_account.get("name"),
				"payment_gateway": gateway_account.get("payment_gateway"),
				"payment_account": gateway_account.get("payment_account"),
				"payment_channel": gateway_account.get("payment_channel"),
				"payment_request_type": args.get("payment_request_type"),
				"currency": ref_doc.currency,
				"party_account_currency": party_account_currency,
				"grand_total": grand_total,
				"mode_of_payment": "Wire Transfer" if bank_account else "",
				"email_to": args.recipient_id or ref_doc.owner,
				"subject": _("Payment Request for {0}").format(args.reference_name),
				"message": gateway_account.get("message") or get_dummy_message(ref_doc),
				"reference_doctype": args.reference_doctype,
				"reference_name": args.reference_name,
				"company": ref_doc.get("company"),
				"party_type": party_type,
				"party": args.get("party") or "",
				"bank_account": bank_account,
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
			if pr.get("__unsaved"):
				pr.insert(ignore_permissions=True)
			pr.submit()

	if args.return_doc:
		return pr

	return pr.as_dict()
