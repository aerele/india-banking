import frappe
from erpnext.accounts.doctype.payment_request.payment_request import (
	get_existing_payment_request_amount,
	make_payment_request,
)


@frappe.whitelist()
def make_bulk_payment_request(invoices, doctype):
	invoices = frappe.parse_json(invoices)
	success_request = []
	no_payment_invoices = []
	for invoice in invoices:
		if invoice.get("name", ""):
			invoice = frappe.get_doc(doctype, invoice.get("name", ""))
			if not is_valid_invoice(invoice):
				no_payment_invoices.append(invoice.name)
				continue
			try:
				args = {
					"dt": invoice.doctype,
					"dn": invoice.name,
					"recipient_id": "",
					"payment_request_type": "Outward",
					"party_type": "Supplier",
					"party": invoice.supplier,
					"return_doc": 1,
				}
				pr = make_payment_request(**args)
				success_request.append(pr)

			except Exception:
				frappe.log_error(
					f"Bulk Payment Failed({invoice.name})", frappe.get_traceback()
				)

	if no_payment_invoices and not len(success_request):
		frappe.msgprint("No Payment to Make")
	return {"success_request": len(success_request)}


def is_valid_invoice(invoice):
	existing_payment_request_amount = get_existing_payment_request_amount(invoice) or 0
	if invoice.outstanding_amount - existing_payment_request_amount > 0:
		return True

	return False
