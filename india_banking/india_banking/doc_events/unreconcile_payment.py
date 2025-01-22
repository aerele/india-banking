import frappe

def on_submit(doc, method=None):
	if not doc.voucher_type == "Payment Entry":
		return

	if frappe.db.get_value("Payment Entry", doc.voucher_no, "source_doctype") != "Bank Payment Request":
		return

	payment_order_summary = get_payment_order_summary(doc.voucher_no)

	if not payment_order_summary:
		return

	payment_order = frappe.get_doc("Payment Order", payment_order_summary.parent)

	for reference in payment_order.references:
		filter_condition = ( payment_order_summary.party_type == reference.party_type and payment_order_summary.party == reference.party and payment_order_summary.cost_center == reference.cost_center
				and payment_order_summary.project == reference.project and payment_order_summary.bank_account == reference.bank_account and payment_order_summary.account == reference.account
				and payment_order_summary.tax_withholding_category == reference.tax_withholding_category and payment_order_summary.reference_doctype == reference.reference_doctype )
		if not payment_order.is_party_wise or payment_order.get('summarise_payment_based_on') == "Voucher":
			filter_condition = filter_condition and (payment_order_summary.reference_doctype == reference.reference_doctype and payment_order_summary.reference_name == reference.reference_name)
		if filter_condition:
			frappe.db.set_value("Bank Payment Request", reference.bank_payment_request, {"reference_doctype": "", "reference_name": ""})
			frappe.db.set_value("Payment Order Reference", reference.name, {"reference_doctype": "", "reference_name": ""})

def get_payment_order_summary(payment_entry):
	is_ammended = frappe.db.get_value("Payment Entry", payment_entry, "amended_from")
	payment_entry = "-".join(payment_entry.split("-")[:-1]) if is_ammended else payment_entry
	summary = frappe.db.get_value("Payment Order Summary", {"payment_entry": payment_entry}, "name")

	if summary:
		return frappe.get_doc("Payment Order Summary", summary)