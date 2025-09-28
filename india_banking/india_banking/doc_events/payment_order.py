import ast

import frappe
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_accounting_dimensions,
)
from erpnext.accounts.doctype.payment_entry.payment_entry import get_split_invoice_rows
from frappe import _, parse_json
from frappe.utils import flt, nowdate

from india_banking.utils import get_bank_payment_naming_series


@frappe.whitelist()
def cancel_pending_payments(data):
	if isinstance(data, str) or isinstance(data, dict):
		data = parse_json(data)

	success_count = 0
	for d in data:
		d = parse_json(d)
		if d.row_name:
			if d.status == "Failed":
				frappe.db.set_value(
					"Payment Order Summary",
					d.row_name,
					{"payment_status": "Failed", "payment_initiated": 1},
				)

				if d.payment_entry:
					payment_entry_doc = frappe.get_doc("Payment Entry", d.payment_entry)
					if payment_entry_doc.docstatus == 1:
						payment_entry_doc.cancel()

				process_payment_requests(d.row_name)

				success_count += 1
	if success_count:
		frappe.msgprint(_(f"{success_count} payment(s) updated"))


def process_payment_requests(payment_order_summary):
	pos = frappe.get_doc("Payment Order Summary", payment_order_summary)

	summary_references = ast.literal_eval(pos.summary_references)
	for reference in summary_references:
		payment_request = frappe.get_value(
			"Payment Order Reference", reference, "payment_request"
		)
		if payment_request:
			pr_doc = frappe.get_doc("Payment Request", payment_request)
			pr_doc.check_if_payment_entry_exists()
			pr_doc.set_as_cancelled()
			pr_doc.db_set("docstatus", 2)


@frappe.whitelist()
def make_payment_entries(docname):
	def _append_reference(
		pe, reference, reference_amount, allocated_amount=None, payment_term=None
	):
		pe.append(
			"references",
			{
				"reference_doctype": reference.reference_doctype,
				"reference_name": reference.reference_name,
				"total_amount": flt(reference_amount),
				"allocated_amount": flt(allocated_amount) or flt(reference_amount),
				"payment_term": payment_term,
				"payment_request": reference.payment_request,
			},
		)

	payment_order_doc = frappe.get_doc("Payment Order", docname)
	"""create entry"""
	frappe.flags.ignore_account_permission = True
	for row in payment_order_doc.summary:
		if not row.summary_references:
			# Restricting 'NOT EXISTS' summary references.
			frappe.throw(_("Summary reference mismatch"))

		pe = frappe.new_doc("Payment Entry")
		# update bank payment naming series
		series = get_bank_payment_naming_series(
			payment_order_doc.company, "Payment Entry"
		)
		if series and series != pe.naming_series:
			pe.naming_series = series

		pe.payment_type = "Pay"
		pe.payment_entry_type = "Pay"
		pe.company = payment_order_doc.company
		pe.cost_center = row.cost_center
		pe.project = row.project
		pe.posting_date = nowdate()
		if frappe.get_single(
			"India Banking Settings"
		).use_payment_order_date_as_payment_entry_date:
			pe.posting_date = payment_order_doc.posting_date
		pe.mode_of_payment = "Wire Transfer"
		pe.party_type = row.party_type
		pe.party = row.party
		pe.bank_account = payment_order_doc.company_bank_account
		pe.party_bank_account = row.bank_account
		if pe.party_type == "Supplier":
			pe.ensure_supplier_is_not_blocked()
		pe.payment_order = payment_order_doc.name
		pe.paid_from = payment_order_doc.account
		if row.account:
			pe.paid_to = row.account
		pe.paid_from_account_currency = "INR"
		pe.paid_to_account_currency = "INR"
		pe.paid_amount = row.amount
		pe.received_amount = row.amount
		pe.letter_head = frappe.db.get_value("Letter Head", {"is_default": 1}, "name")
		pe.source_doctype = payment_order_doc.payment_order_type

		for dimension in get_accounting_dimensions():
			pe.update({dimension: row.get(dimension, "")})

		summary_references = ast.literal_eval(row.summary_references)
		if row.tax_withholding_category:
			net_total = 0
			for sr_name in summary_references:
				reference = frappe.get_doc("Payment Order Reference", sr_name)
				net_total += frappe.db.get_value(
					"Payment Request",
					reference.payment_request,
					"net_total",
				)

			pe.paid_amount = net_total
			pe.received_amount = net_total
			pe.apply_tax_withholding_amount = 1
			pe.tax_withholding_category = row.tax_withholding_category

		for sr_name in summary_references:
			reference = frappe.get_doc("Payment Order Reference", sr_name)
			if not reference.is_adhoc:
				reference_amount = frappe.db.get_value(
					"Payment Request",
					reference.payment_request,
					"net_total",
				)
				payment_term = frappe.db.get_value(
					"Payment Request",
					reference.payment_request,
					"payment_term",
				)

				if not payment_term:
					template = frappe.db.get_value(
						reference.reference_doctype,
						reference.reference_name,
						"payment_terms_template",
					)
					if template:
						splited_invoice_rows = get_split_invoice_rows(
							frappe._dict({"voucher_no": reference.reference_name}),
							template,
							exc_rates={
								reference.reference_name: frappe.get_doc(
									reference.reference_doctype,
									reference.reference_name,
								)
							},
						)
						is_term_applied = frappe.db.get_value(
							"Payment Terms Template",
							template,
							"allocate_payment_based_on_payment_terms",
						)
						if splited_invoice_rows and is_term_applied:
							for term_row in splited_invoice_rows:
								if reference_amount <= 0:
									break
								term_paid = (
									frappe.get_value(
										"Payment Entry Reference",
										{
											"reference_doctype": reference.reference_doctype,
											"reference_name": reference.reference_name,
											"payment_term": term_row.get(
												"payment_term"
											),
											"docstatus": 1,
										},
										"sum(allocated_amount)",
									)
									or 0
								)
								per = (
									frappe.db.get_value(
										"Payment Term",
										term_row.get("payment_term"),
										"invoice_portion",
									)
									/ 100
								)
								invoice_amount = frappe.db.get_value(
									reference.reference_doctype,
									reference.reference_name,
									"grand_total",
								)
								to_be_pay = per * invoice_amount
								paid_amount = min(
									reference_amount, to_be_pay - term_paid
								)
								if paid_amount > 0:
									_append_reference(
										pe,
										reference,
										invoice_amount,
										allocated_amount=paid_amount,
										payment_term=term_row.get("payment_term"),
									)
									reference_amount -= paid_amount
						else:
							_append_reference(pe, reference, reference_amount)
					else:
						_append_reference(pe, reference, reference_amount)
				else:
					_append_reference(
						pe, reference, reference_amount, payment_term=payment_term
					)
		pe.update(
			{
				"reference_no": payment_order_doc.name,
				"reference_date": nowdate(),
				"remarks": "Payment Entry from Payment Order - {0}".format(
					payment_order_doc.name
				),
			}
		)
		pe.setup_party_account_field()
		pe.set_missing_values()
		pe.validate()

		group_by_invoices(pe)

		pe.insert(ignore_permissions=True, ignore_mandatory=True)
		pe.submit()

		# add payment entry reference in summary row
		frappe.db.set_value("Payment Order Summary", row.name, "payment_entry", pe.name)


def group_by_invoices(self):
	grouped_references = {}
	if self.references:
		for ref in self.references:
			key = (ref.reference_name, ref.reference_doctype, ref.payment_term)
			if key not in grouped_references:
				grouped_references[key] = ref
			else:
				grouped_references[key].allocated_amount += ref.allocated_amount
		self.references = list(grouped_references.values())
