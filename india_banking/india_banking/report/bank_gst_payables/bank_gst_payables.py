# Copyright (c) 2025, Aerele Technologies Private Limited and contributors
# For license information, please see license.txt

import json

import frappe
from erpnext.accounts.doctype.payment_request.payment_request import (
	get_existing_payment_request_amount,
)
from frappe import _, bold, get_installed_apps
from frappe.query_builder import DocType
from frappe.query_builder.functions import Sum
from frappe.utils import cstr, flt, get_link_to_form

from india_banking.india_banking.report.bulk_create_payment_request.bulk_create_payment_request import (
	make_payment_request,
)
from india_banking.utils import add_background_job

ENQUEUE_LIMIT = 50


def execute(filters: dict | None = None):
	if "india_compliance" not in get_installed_apps():
		return [], []

	columns = get_columns(filters)
	data = get_data(filters)

	return columns, data


def get_columns(filters=None) -> list[dict]:
	return [
		{
			"label": _("Purchase Invoice"),
			"fieldname": "purchase_invoice",
			"fieldtype": "Link",
			"options": "Purchase Invoice",
		},
		{
			"label": _("Reconciliation Status"),
			"fieldname": "reconciliation_status",
			"fieldtype": "Data",
			"default": "No Found",
		},
		{
			"label": _("Supplier"),
			"fieldname": "supplier",
			"fieldtype": "Link",
			"options": "Supplier",
		},
		{
			"label": _("Hold GST Payables"),
			"fieldname": "hold_gst_payables",
			"fieldtype": "check",
		},
		{
			"label": _("Outstanding(Invoice)"),
			"fieldname": "invoice_outstanding",
			"fieldtype": "Currency",
		},
		{
			"label": _("Outstanding(Payment Request)"),
			"fieldname": "request_outstanding",
			"fieldtype": "Currency",
		},
		{
			"label": _("Net Outstanding"),
			"fieldname": "net_outstanding",
			"fieldtype": "Currency",
		},
		{
			"label": _("GST Payable"),
			"fieldname": "gst_payable",
			"fieldtype": "Currency",
		},
		{
			"label": _("Pay Net Outstanding"),
			"fieldname": "action",
			"fieldtype": "HTML",
		},
	]


def get_data(filters=None):
	PII = DocType("Purchase Invoice Item")
	PI = DocType("Purchase Invoice")
	SUPP = DocType("Supplier")

	query = (
		frappe.qb.from_(PII)
		.join(PI)
		.on(PI.name == PII.parent)
		.join(SUPP)
		.on(SUPP.name == PI.supplier)
		.select(
			PI.name.as_("purchase_invoice"),
			SUPP.name.as_("supplier"),
			SUPP.supplier_name.as_("supplier_name"),
			SUPP.hold_gst_payables,
			PI.outstanding_amount.as_("invoice_outstanding"),
			PI.reconciliation_status,
			(Sum(PII.igst_amount) + Sum(PII.cgst_amount) + Sum(PII.sgst_amount)).as_(
				"gst_payable"
			),
		)
		.where(PI.docstatus == 1)
		.where(SUPP.hold_gst_payables == 1)
		.where(PI.company == filters.get("company"))
		.where(PI.outstanding_amount > 0)
		.groupby(PII.name)
	)

	if filters.get("supplier"):
		query = query.where(PI.supplier == filters.get("supplier"))

	button = """<button class="btn btn-xs btn-default btn-primary" data-fieldtype="Button" data-fieldname="pay_net_outstanding" onclick= pay_net_outstanding('{}')>Create</button>"""

	data = []
	item_details = query.run(as_dict=True)
	for details in item_details:
		if details.gst_payable < 0:
			continue
		ref_doc = frappe.get_doc("Purchase Invoice", details.purchase_invoice)
		request_outstanding = get_existing_payment_request_amount(ref_doc)
		net_outstanding = details.invoice_outstanding - request_outstanding
		details.update(
			{
				"request_outstanding": request_outstanding,
				"net_outstanding": net_outstanding,
				"reconciliation_status": details.reconciliation_status or "N/A",
				"action": f"{button}".format(
					details.purchase_invoice + "amt:" + cstr(flt(net_outstanding))
				),
			}
		)
		if net_outstanding <= 0:
			continue

		data.append(details)

	return data


@frappe.whitelist()
def create_single_payment_request(invoice, net_outstanding, filters=None):
	net_total = flt(net_outstanding)
	invoice = frappe.get_doc("Purchase Invoice", invoice)
	if isinstance(filters, str):
		filters = json.loads(filters)
	payment_details = {
		"payment_request_type": "Outward",
		"company": filters.get("company"),
		"mode_of_payment": "Wire Transfer",
		"payment_type": frappe.db.exists(
			"Payment Type", {"company": filters.get("company"), "is_default": 1}
		),
		"party_type": "Supplier",
		"party": invoice.supplier,
		"reference_doctype": "Purchase Invoice",
		"reference_name": invoice.name,
		"net_total": net_total,
	}
	frappe.flags.ignore_hold_gst_payables = True
	try:
		pr = make_payment_request(**payment_details)
		frappe.flags.ignore_hold_gst_payables = False
		link = get_link_to_form("Payment Request", pr.name)
		frappe.msgprint("payment request {}".format(bold(link)))
	except Exception:
		pass


@frappe.whitelist()
def create_bulk_payment_request(invoices, filters=None):
	if isinstance(invoices, str):
		invoices = json.loads(invoices)
	if isinstance(filters, str):
		filters = json.loads(filters)

	if not invoices:
		return []

	count = 0
	zero_outstanding = 0
	for invoice in invoices:
		invoice = frappe._dict(invoice)
		net_total = flt(invoice.gst_payable)
		payment_details = {
			"payment_request_type": "Outward",
			"company": filters.get("company"),
			"mode_of_payment": "Wire Transfer",
			"payment_type": frappe.db.exists(
				"Payment Type", {"company": filters.get("company"), "is_default": 1}
			),
			"party_type": "Supplier",
			"party": invoice.supplier,
			"reference_doctype": "Purchase Invoice",
			"reference_name": invoice.purchase_invoice,
			"net_total": net_total,
		}

		if not net_total:
			zero_outstanding += 1
		else:
			if len(invoices) > ENQUEUE_LIMIT:
				job_id = invoice.voucher_no + cstr(invoice.payment_term)
				job_name = invoice.voucher_no + "-" + cstr(invoice.payment_term)
				method = make_payment_request
				add_background_job(job_id, job_name, method, **payment_details)
			else:
				frappe.flags.ignore_hold_gst_payables = True
				try:
					make_payment_request(**payment_details)
				except Exception:
					pass
				frappe.flags.ignore_hold_gst_payables = False
			count += 1
	if count:
		msg = "{} Row Updated".format(count)
		if len(invoices) > ENQUEUE_LIMIT:
			msg = "{} Row added in background job".format(count)
		frappe.msgprint(msg)

	if not count and zero_outstanding:
		frappe.msgprint("No more outstanding to Pay")
