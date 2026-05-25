# Copyright (c) 2025, Aerele Technologies Private Limited and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _
from frappe.utils import cstr, flt


def execute(filters=None):
	return get_columns(filters), get_data(filters)


def get_data(filters=None):
	filters.update(
		{
			"docstatus": 0,
			"party_type": "Supplier",
			"payment_request_type": "Outward",
			"grand_total": [">", 0],
		}
	)
	if filters.get("supplier"):
		filters.update({"party": filters.pop("supplier")})
	if filters.transaction_date:
		filters.update(
			{"transaction_date": ["between", filters.pop("transaction_date")]}
		)

	data = frappe.db.get_all("Payment Request", filters=filters, fields=get_fields())

	button = """
				<button class="btn btn-xs btn-default edit-amount"
				data-fieldtype="Button"
				data-fieldname="edit_amount" onclick= update_amount('{}')>Edit</button>"""

	for row in data:
		if row.reference_doctype in ["Purchase Order", None]:
			row.update(
				{
					"action": f"{button}".format(
						row.payment_request + "amt:" + cstr(row.net_total)
					)
				}
			)
		else:
			row.update({"action": ""})

	return data


def get_fields(filters=None):
	fields = [
		"name as payment_request",
		"payment_request_type as request_type",
		"mode_of_payment as mode_of_payment",
		"transaction_date as transaction_date",
		"party_type as party_type",
		"party as party",
		"bank_account as bank_account",
		"reference_doctype as reference_doctype",
		"reference_name as reference_name",
		"net_total as net_total",
		"grand_total as amount",
	]
	return fields


def get_columns(filters=None):
	columns = [
		{
			"fieldname": _("payment_request"),
			"label": "Payment Request",
			"fieldtype": "Link",
			"options": "Payment Request",
		},
		{"fieldname": _("request_type"), "label": "Request Type", "fieldtype": "Data"},
		{
			"fieldname": _("mode_of_payment"),
			"label": "Mode of Payment",
			"fieldtype": "Data",
		},
		{
			"fieldname": _("transaction_date"),
			"label": "Transaction Date",
			"fieldtype": "Date",
		},
		{
			"fieldname": _("party_type"),
			"label": "Party Type",
			"fieldtype": "Link",
			"options": "DocType",
		},
		{
			"fieldname": _("party"),
			"label": "Party",
			"fieldtype": "Dynamic Link",
			"options": "party_type",
		},
		{
			"fieldname": _("bank_account"),
			"label": "Bank Account",
			"fieldtype": "Link",
			"options": "Bank Account",
		},
		{
			"fieldname": _("reference_doctype"),
			"label": "Reference DocType",
			"fieldtype": "Link",
			"options": "DocType",
		},
		{
			"fieldname": _("reference_name"),
			"label": "Reference Name",
			"fieldtype": "Dynamic Link",
			"options": "reference_doctype",
		},
		{
			"fieldname": _("net_total"),
			"label": "Net Total",
			"fieldtype": "Float",
			"precision": "3",
		},
		{
			"fieldname": _("amount"),
			"label": "Amount",
			"fieldtype": "Float",
			"precision": "3",
		},
		{"fieldname": _("action"), "label": "Action", "fieldtype": "HTML"},
	]
	return columns


@frappe.whitelist()
def update_bulk_payment_request(docnames, enque: bool = False):
	"""Update the Payment Request"""

	def validate_doc(doc, valid_doc=None):
		doc = frappe.get_doc("Payment Request", doc)
		if not doc.bank_account:
			return doc.party
		else:
			valid_doc.append(doc)

	if isinstance(docnames, str):
		docnames = json.loads(docnames)

	if not docnames:
		return

	valid_doc = []
	invalid_doc = [
		f"<b>{validate_doc(doc)}</b>"
		for doc in docnames
		if validate_doc(doc, valid_doc)
	]

	if len(invalid_doc) > 0:
		frappe.msgprint(
			title="Bank Account Missing for Listed Party",
			msg="Bank Account Missing for Listed Party</br></br>"
			+ "</br>".join(set(invalid_doc)),
		)

	if len(valid_doc) > 20:
		enque = True

	count = 0
	failed_doc = []
	for doc in valid_doc:
		try:
			if enque:
				frappe.enqueue(doc.submit, queue="long")
			else:
				doc.submit()
			count += 1

		except Exception:
			frappe.log_error(
				f"{doc} Failed", message=frappe.get_traceback(with_context=1)
			)
			failed_doc.append(doc.name)

	if count:
		frappe.msgprint("{} Row Updated".format(count))
	if len(failed_doc) > 0:
		frappe.msgprint(title="Some Rows Failed", msg=", ".join(failed_doc))


@frappe.whitelist()
def update_value(**args):
	if not args:
		return
	data = frappe._dict(args)

	doc = frappe.get_doc(data.doctype, data.docname)
	doc.db_set("net_total", flt(data.value))
	doc.save()

	return doc
