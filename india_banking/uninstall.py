import click
import frappe
from frappe.custom.doctype.property_setter.property_setter import delete_property_setter

from india_banking.install import (
	properties,
	toggle_payment_request_creation,
	toggle_reqd_for_reference_in_payment_order,
)


def before_uninstall():
	delete_custom_fields()
	toggle_payment_request_creation(False)
	delete_propert_setters()
	toggle_reqd_for_reference_in_payment_order(True)


def delete_custom_fields():
	fieldnames = {
		"Payment Request": [
			"payment_type",
			"is_adhoc",
			"net_total",
			"taxes_deducted",
			"apply_tax_withholding_amount",
			"tax_withholding_category",
			"payment_term",
		],
		"Payment Order": [
			"get_summary",
			"payment_summary",
			"is_party_wise",
			"summary",
			"total",
			"status",
		],
		"Payment Order Reference": [
			"party_type",
			"party",
			"tax_withholding_category",
			"is_adhoc",
			"payment_term",
			"remarks",
		],
		"Supplier": ["lei_number"],
		"Bank": ["is_standard"],
	}

	for doctype, fieldnames in fieldnames.items():
		click.secho(f"* Uninstalling Custom Fields from {doctype}")
		for fieldname in fieldnames:
			frappe.db.delete("Custom Field", {"name": f"{doctype}-" + fieldname})

		frappe.clear_cache(doctype=doctype)


def delete_propert_setters():
	delete_payment_request_property_setter()


def delete_payment_request_property_setter():
	data = [
		(
			_property.get("doctype", ""),
			_property.get("property", ""),
			_property.get("fieldname", ""),
		)
		for _property in properties
	]
	for doctype, property, fieldname in data:
		click.echo(f"* Updating {doctype} Property")
		delete_property_setter(doctype, property, fieldname)
