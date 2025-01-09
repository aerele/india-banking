import frappe

from india_banking.install import make_custom_fields, toggle_payment_request_creation
from india_banking.uninstall import delete_custom_fields


def execute():
	toggle_payment_request_creation()
	delete_custom_fields()
	remove_custom_section_and_column_break_fields()
	remove_main_field_order()
	make_custom_fields()


def remove_custom_section_and_column_break_fields():
	if fields := frappe.get_all(
		"Custom Field",
		filters={
			"dt": [
				"in",
				[
					"Journal Entry Account",
					"Payment Entry",
					"Payment Order",
					"Payment Order Reference",
					"Payment Request",
				],
			],
			"fieldtype": ["in", ["Section Break", "Column Break"]],
		},
		pluck="name",
	):
		frappe.db.delete("Custom Field", {"name": ["in", fields]})


def remove_main_field_order():
	doctypes = [
		"Payment Order",
		"Payment Order Reference",
		"Payment Request",
	]
	for doctype in doctypes:
		frappe.db.delete("Property Setter", {"name": f"{doctype}-main-field_order"})
