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
from pypika import terms

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
	columns = [
		{
			"label": _("Voucher Type"),
			"fieldname": "voucher_type",
			"fieldtype": "Data",
		},
		{
			"label": _("Voucher Name"),
			"fieldname": "voucher_name",
			"fieldtype": "Link",
			"options": filters.get("voucher_type"),
		},
	]
	if filters.get("voucher_type") == "Purchase Invoice":
		columns.append(
			{
				"label": _("Reconciliation Status"),
				"fieldname": "reconciliation_status",
				"fieldtype": "Data",
				"default": "No Found",
			}
		)
	columns.extend(
		[
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
		]
	)
	if filters.get("voucher_type") == "Purchase Invoice":
		columns.extend(
			[
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
			]
		)
	else:
		columns.extend(
			[
				{
					"label": _("Order Total"),
					"fieldname": "order_total",
					"fieldtype": "Currency",
				},
				{
					"label": _("Advance Paid"),
					"fieldname": "advance_paid",
					"fieldtype": "Currency",
				},
				{
					"label": _("Outstanding(Payment Request)"),
					"fieldname": "request_outstanding",
					"fieldtype": "Currency",
				},
				{
					"label": _("Due Balance"),
					"fieldname": "due_balance",
					"fieldtype": "Currency",
				},
			]
		)
	columns.append(
		{
			"label": _("GST Payable"),
			"fieldname": "gst_payable",
			"fieldtype": "Currency",
		}
	)
	label = _("Pay Net Outstanding")
	if filters.get("voucher_type") == "Purchase Order":
		label = _("Pay Due Balance")

	columns.append(
		{
			"label": label,
			"fieldname": "action",
			"fieldtype": "HTML",
		}
	)

	return columns


def get_data(filters=None):
	if filters.get("voucher_type") == "Purchase Invoice":
		return get_invoice_data(filters)
	else:
		return get_order_data(filters)


def get_order_data(filters):
	POI = DocType("Purchase Order Item")
	PO = DocType("Purchase Order")
	SUPP = DocType("Supplier")

	query = (
		frappe.qb.from_(POI)
		.join(PO)
		.on(PO.name == POI.parent)
		.join(SUPP)
		.on(SUPP.name == PO.supplier)
		.select(
			terms.LiteralValue("'Purchase Order'").as_("voucher_type"),
			PO.name.as_("voucher_name"),
			SUPP.name.as_("supplier"),
			SUPP.supplier_name.as_("supplier_name"),
			SUPP.hold_gst_payables,
			PO.rounded_total.as_("order_total"),
			PO.advance_paid,
			(Sum(POI.igst_amount) + Sum(POI.cgst_amount) + Sum(POI.sgst_amount)).as_(
				"gst_payable"
			),
		)
		.where(PO.docstatus == 1)
		.where(SUPP.hold_gst_payables == 1)
		.where(PO.company == filters.get("company"))
		.where(PO.per_billed < 100)
		.groupby(POI.name)
	)

	if filters.get("supplier"):
		query = query.where(PO.supplier == filters.get("supplier"))

	button = """<button class="btn btn-xs btn-default btn-primary" data-fieldtype="Button" data-fieldname="pay_due_balance" onclick= pay_due_balance('{}')>Create</button>"""

	data = []
	item_details = query.run(as_dict=True)
	for details in item_details:
		if details.gst_payable < 0:
			continue
		ref_doc = frappe.get_doc(details.voucher_type, details.voucher_name)
		request_outstanding = get_existing_payment_request_amount(ref_doc)
		due_balance = details.order_total - details.advance_paid - request_outstanding
		details.update(
			{
				"request_outstanding": request_outstanding,
				"due_balance": due_balance,
				"action": f"{button}".format(
					details.voucher_name + "amt:" + cstr(flt(due_balance))
				),
			}
		)
		if due_balance <= 0 or due_balance > details.gst_payable:
			continue

		data.append(details)

	return data


def get_invoice_data(filters):
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
			terms.LiteralValue("'Purchase Invoice'").as_("voucher_type"),
			PI.name.as_("voucher_name"),
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
		ref_doc = frappe.get_doc(details.voucher_type, details.voucher_name)
		request_outstanding = get_existing_payment_request_amount(ref_doc)
		net_outstanding = details.invoice_outstanding - request_outstanding
		details.update(
			{
				"request_outstanding": request_outstanding,
				"net_outstanding": net_outstanding,
				"reconciliation_status": details.reconciliation_status or "N/A",
				"action": f"{button}".format(
					details.voucher_name + "amt:" + cstr(flt(net_outstanding))
				),
			}
		)
		if net_outstanding <= 0 or net_outstanding > details.gst_payable:
			continue

		data.append(details)

	return data


@frappe.whitelist()
def create_single_payment_request(voucher_type, voucher_name, amount, filters=None):
	voucher = frappe.get_doc(voucher_type, voucher_name)
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
		"party": voucher.supplier,
		"reference_doctype": voucher_type,
		"reference_name": voucher_name,
		"net_total": flt(
			amount, frappe.get_precision("Payment Request", "grand_total")
		),
	}
	try:
		frappe.flags.ignore_hold_gst_payables = True
		pr = make_payment_request(**payment_details)
		link = get_link_to_form("Payment Request", pr.name)
		frappe.msgprint("payment request {}".format(bold(link)))
	except Exception:
		frappe.log_error(
			"Failed to create GST Payable", frappe.get_traceback(with_context=True)
		)
	finally:
		frappe.flags.ignore_hold_gst_payables = False


@frappe.whitelist()
def create_bulk_payment_request(vouchers, filters=None):
	if isinstance(vouchers, str):
		vouchers = json.loads(vouchers)
	if isinstance(filters, str):
		filters = json.loads(filters)

	if not vouchers:
		return []

	count = 0
	zero_outstanding = 0
	for voucher in vouchers:
		voucher = frappe._dict(voucher)
		net_total = flt(voucher.gst_payable)
		payment_details = {
			"payment_request_type": "Outward",
			"company": filters.get("company"),
			"mode_of_payment": "Wire Transfer",
			"payment_type": frappe.db.exists(
				"Payment Type", {"company": filters.get("company"), "is_default": 1}
			),
			"party_type": "Supplier",
			"party": voucher.supplier,
			"reference_doctype": voucher.voucher_type,
			"reference_name": voucher.voucher_name,
			"net_total": net_total,
		}

		if not net_total:
			zero_outstanding += 1
		else:
			if len(vouchers) > ENQUEUE_LIMIT:
				job_id = voucher.voucher_no + cstr(voucher.payment_term)
				job_name = voucher.voucher_no + "-" + cstr(voucher.payment_term)
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
		if len(vouchers) > ENQUEUE_LIMIT:
			msg = "{} Row added in background job".format(count)
		frappe.msgprint(msg)

	if not count and zero_outstanding:
		frappe.msgprint("No more outstanding to Pay")
