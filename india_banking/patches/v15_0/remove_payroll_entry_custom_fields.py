import click
import frappe

from india_banking.install import make_custom_fields, toggle_payment_request_creation


def execute():
	fieldnames = {
		"Payment Request": ["salary_slip"],
		"Payment Order Reference": ["payroll_entry"],
	}

	for doctype, fieldnames in fieldnames.items():
		click.secho(f" -> Uninstalling Custom Fields from {doctype}")
		for fieldname in fieldnames:
			frappe.db.delete("Custom Field", {"dt": doctype, "fieldname": fieldname})

		frappe.clear_cache(doctype=doctype)

	toggle_payment_request_creation()
	make_custom_fields()
