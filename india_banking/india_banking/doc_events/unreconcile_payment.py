import frappe
from frappe import _

def on_submit(doc, method=None):
	if not doc.voucher_type == "Payment Entry":
		return

	if frappe.db.get_value("Payment Entry", doc.voucher_no, "source_doctype") != "Bank Payment Request":
		return
	if not frappe.db.get_single_value("India Banking Settings", "allow_unreconcile"):
		return

	if not has_unlink_permission():
		frappe.throw(_("You are not permitted to unlink Bank Payment Request from the invoice."), frappe.PermissionError)

	payment_order_summary = get_payment_order_summary(doc.voucher_no)

	if not payment_order_summary:
		return

	payment_order = frappe.get_doc("Payment Order", payment_order_summary.parent)

	for reference in payment_order.references:
		fields = ["party_type", "party", "cost_center", "project", "bank_account", "account", "tax_withholding_category", "reference_doctype"]
		if not payment_order.get("is_party_wise", "") or payment_order.get('summarise_payment_based_on') == "Voucher":
			fields = fields + ["reference_name"]

		filter_condition = [(payment_order_summary.get(field, ""), reference.get(field, "")) for field in fields]
		values_match = True
		for filter in filter_condition:
			if bool(filter[0]) == bool(filter[1]):
				if  filter[0] != filter[1]:
					values_match = False
					break

		if values_match:
			frappe.db.set_value("Bank Payment Request", reference.bank_payment_request, {"reference_doctype": "", "reference_name": ""})
			frappe.db.set_value("Payment Order Reference", reference.name, {"reference_doctype": "", "reference_name": ""})

UNLINK_ADMIN_ROLES = {"Administrator", "Local Admin"}


def has_unlink_permission():
	user_roles = set(frappe.get_roles())
	if UNLINK_ADMIN_ROLES & user_roles:
		return True

	allowed_roles = set(
		frappe.get_all(
			"Bank Payment Request Unlink Role",
			filters={"parent": "India Banking Settings"},
			pluck="role",
		)
	)
	return bool(allowed_roles & user_roles)


def get_payment_order_summary(payment_entry):
	is_ammended = frappe.db.get_value("Payment Entry", payment_entry, "amended_from")
	payment_entry = "-".join(payment_entry.split("-")[:-1]) if is_ammended else payment_entry
	summary = frappe.db.get_value("Payment Order Summary", {"payment_entry": payment_entry}, "name")

	if summary:
		return frappe.get_doc("Payment Order Summary", summary)
