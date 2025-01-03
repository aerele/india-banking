import click
import frappe
from frappe.custom.doctype.property_setter.property_setter import delete_property_setter

from india_banking.default import DEFAULT_WORKFLOW_LIST
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
	delete_default_workflow()


def delete_default_workflow():
	click.echo(" -> Removing Default workflow")

	for workflow in DEFAULT_WORKFLOW_LIST:
		workflow = frappe._dict(workflow)
		if workflow_name := frappe.db.exists(
			"Workflow",
			{
				"document_type": workflow.document_type,
				"workflow_name": workflow.workflow_name,
			},
		):
			click.echo(
				f" -> Deleting workflow for the {workflow.document_type} Doctype."
			)
			frappe.delete_doc("Workflow", workflow_name)


def delete_custom_fields():
	click.secho("* Removing India Banking Customizations")
	fieldnames = {
		"Journal Entry Account": [
			"payment_details",
			"payment_status",
			"payment_details_column_break",
			"reference_number",
		],
		"Bank Account": [
			"mobile_number",
			"email",
			"bank_balance",
		],
		"Payment Entry": [
			"source_section",
			"source_doctype",
			"source_column",
			"source_name",
		],
		"Payment Request": [
			"payment_type",
			"is_adhoc",
			"net_total",
			"taxes_deducted",
			"apply_tax_withholding_amount",
			"tax_withholding_category",
			"payment_term",
			"remarks",
			"remark_section",
		],
		"Payment Order": [
			"icici_bank_api_info",
			"unique_id",
			"bank_api_info_column_break",
			"file_sequence_number",
			"file_reference_id",
			"get_summary",
			"payment_summary",
			"default_mode_of_transfer",
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
			"cost_center",
			"project",
			"payment_entry",
			"journal_entry_account",
		],
		"Supplier": ["lei_number"],
		"Bank": ["is_standard"],
	}

	for doctype, fieldnames in fieldnames.items():
		click.secho(f" -> Uninstalling Custom Fields from {doctype}")
		for fieldname in fieldnames:
			frappe.db.delete("Custom Field", {"dt": doctype, "fieldname": fieldname})

		frappe.clear_cache(doctype=doctype)


def delete_propert_setters():
	delete_payment_request_property_setter()


def delete_payment_request_property_setter():
	for doctype in properties.keys():
		data = [
			(
				_property.get("doctype", ""),
				_property.get("property", ""),
				_property.get("fieldname", ""),
			)
			for _property in properties.get(doctype)
		]

		click.echo(f" -> Removing {doctype} Properties")
		for doctype, property, fieldname in data:
			delete_property_setter(doctype, property, fieldname)
