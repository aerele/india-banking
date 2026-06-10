import click
import frappe

from india_banking.install import make_custom_fields


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

	make_custom_fields()
