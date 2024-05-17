import frappe

STD_BANK_LIST = [
	{
		'bank_name': 'Yes Bank',
		'swift_number': '',
		'app_name': 'yes_integration_server',
		'is_standard': True
	},
	{
		'bank_name': 'HDFC Bank',
		'swift_number': '',
		'app_name': 'hdfc_integration_server',
		'is_standard': True
	},
	{
		'bank_name': 'ICICI Bank',
		'swift_number': '',
		'app_name': 'icici_integration_server',
		'is_standard': True
	},
	{
		'bank_name': 'Axis Bank',
		'swift_number': '',
		'app_name': 'axis_integration_server',
		'is_standard': True
	}
]

def after_install():
	# As a part of the integration, for making ad-hoc payments, we are enabling creation of it.
	disable_reqd_for_reference_in_payment_order()
	update_payment_order_fields_options()
	create_lei_number_field()
	create_default_bank()

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
		bank_doc = frappe.new_doc('Bank')
		bank_doc.update(bank_details)
		bank_doc.save()
