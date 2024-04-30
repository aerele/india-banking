import frappe

def after_install():
	# Payment request cannot be created in the default ERPNext.
	# As a part of the integration, for making ad-hoc payments, we are enabling creation of it.
	allow_payment_request_creation()
	disable_reqd_for_reference_in_payment_order()
	update_payment_order_fields_options()
	create_lei_number_field()

def update_payment_order_fields_options():
	payment_order_type = frappe.db.get_value("DocField", {"parent": "Payment Order", "fieldname": "payment_order_type"})
	frappe.db.set_value("DocField", payment_order_type, "options", "\nBank Payment Request\nPayment Request\nPayment Entry")

def allow_payment_request_creation():
	frappe.db.set_value("DocType", "Payment Request", "in_create", 0)
	frappe.db.set_value("DocType", "Payment Request", "track_changes", 1)

def disable_reqd_for_reference_in_payment_order():
	po_type = frappe.db.get_value("DocField", {"parent": "Payment Order Reference", "fieldname": "reference_doctype"})
	po_doc = frappe.db.get_value("DocField", {"parent": "Payment Order Reference", "fieldname": "reference_name"})
	po_amount = frappe.db.get_value("DocField", {"parent": "Payment Order Reference", "fieldname": "amount"})
	frappe.db.set_value("DocField", po_type, "reqd", 0)
	frappe.db.set_value("DocField", po_doc, "reqd", 0)
	frappe.db.set_value("DocField", po_amount, "reqd", 0)
	frappe.db.set_value("DocField", po_amount, "read_only", 0)

	po_doctype = frappe.db.get_value("DocField", {"parent": "Payment Order", "fieldname": "payment_order_type"})
	frappe.db.set_value("DocField", po_doctype, "options", "\nPayment Request\nPayment Entry\nPurchase Invoice")

def create_lei_number_field():
	lei_number_field = frappe.db.get_value("Custom Field", {"dt": "Supplier", "fieldname": "custom_lei_number"})
	if lei_number_field:
		return

	from frappe.custom.doctype.custom_field.custom_field import create_custom_field
	df = {
		"owner":"Administrator",
		"label":"LEI Number",
		"fieldname":"custom_lei_number",
		"insert_after":"tax_id",
		"fieldtype":"Data"
	}
	create_custom_field("Supplier", df)