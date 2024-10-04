import frappe
from india_banking.india_banking.default import DEFAULT_MODE_OF_TRANSFERS, STD_BANK_LIST
def after_install():
	# As a part of the integration, for making ad-hoc payments, we are enabling creation of it.
	disable_reqd_for_reference_in_payment_order()
	update_payment_order_fields_options()
	create_lei_number_field()
	create_default_bank()
	create_default_mode_of_transfers()
	create_default_payment_type()

def create_default_mode_of_transfers():
	for mot in DEFAULT_MODE_OF_TRANSFERS:
		if not frappe.db.exists("Mode of Transfer",mot["mode"]):
			frappe.get_doc({
				"doctype": "Mode of Transfer",
				"mode": mot["mode"],
				"minimum_limit": mot["minimum_limit"],
				"maximum_limit": mot["maximum_limit"],
				"start_time": mot["start_time"],
				"end_time": mot["end_time"],
				"priority": mot["priority"]
			}).insert(ignore_permissions=True)

def update_payment_order_fields_options():
	payment_order_type = frappe.db.get_value("DocField", {"parent": "Payment Order", "fieldname": "payment_order_type"})
	frappe.db.set_value("DocField", payment_order_type, "options", "\nBank Payment Request\nPayment Request\nPayment Entry")

def disable_reqd_for_reference_in_payment_order():
	po_type = frappe.db.get_value("DocField", {"parent": "Payment Order Reference", "fieldname": "reference_doctype"})
	po_doc = frappe.db.get_value("DocField", {"parent": "Payment Order Reference", "fieldname": "reference_name"})
	po_amount = frappe.db.get_value("DocField", {"parent": "Payment Order Reference", "fieldname": "amount"})
	frappe.db.set_value("DocField", po_type, "reqd", 0)
	frappe.db.set_value("DocField", po_doc, "reqd", 0)
	frappe.db.set_value("DocField", po_amount, "reqd", 0)
	frappe.db.set_value("DocField", po_amount, "read_only", 0)

def create_lei_number_field():
	lei_number_field = frappe.db.get_value("Custom Field", {"dt": "Supplier", "fieldname": "lei_number"})
	if lei_number_field:
		return

	from frappe.custom.doctype.custom_field.custom_field import create_custom_field
	df = {
		"owner":"Administrator",
		"label":"LEI Number",
		"fieldname":"lei_number",
		"insert_after":"tax_id",
		"fieldtype":"Data"
	}
	create_custom_field("Supplier", df)

def create_default_bank():
	for bank_details in STD_BANK_LIST:
		if not frappe.db.exists("Bank", bank_details.get("bank_name")):
			bank_doc = frappe.new_doc('Bank')
			bank_doc.update(bank_details)
			bank_doc.save()

def create_default_payment_type():
	if not frappe.db.exists("Payment Type", "Pay"):
		frappe.get_doc({
			"doctype": "Payment Type",
			"payment_type": "Pay"
		}).insert(ignore_permissions=True, ignore_mandatory=True)