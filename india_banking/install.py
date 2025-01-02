import click
import frappe
from frappe import make_property_setter
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from india_banking.default import (
	DEFAULT_MODE_OF_TRANSFERS,
	DEFAULT_WORKFLOW_ACTIONS,
	DEFAULT_WORKFLOW_LIST,
	DEFAULT_WORKFLOW_STATE,
	STD_BANK_LIST,
)


def after_install():
	click.secho("* Updating India Banking Customisations")
	toggle_payment_request_creation(True)
	make_custom_fields()
	create_property_setter()
	toggle_reqd_for_reference_in_payment_order(False)
	create_default_mode_of_transfers()
	create_default_payment_type()
	create_default_workflow()
	create_default_bank()


def make_custom_fields():
	create_bank_doc_custom_fields()
	create_bank_account_custom_fields()
	create_payment_request_custom_fields()
	create_payment_order_custom_fields()
	create_payment_entry_custom_fields()
	create_journal_entry_custom_fields()


def create_property_setter():
	create_payment_request_property_setter()


def toggle_payment_request_creation(allow=True):
	click.secho(
		" -> {} Payment Request Creation...".format(
			"Enabling" if allow else "Disabling"
		)
	)
	frappe.db.set_value(
		"DocType", "Payment Request", {"in_create": not allow, "track_changes": allow}
	)


def create_bank_doc_custom_fields():
	click.secho(" -> Installing Custom Fields in a Bank...")
	fields = {
		"Bank": [
			{
				"label": "Standard",
				"fieldname": "is_standard",
				"fieldtype": "Check",
				"read_only": 1,
				"insert_after": "bank",
			},
		]
	}

	create_custom_fields(fields)


def create_journal_entry_custom_fields():
	click.secho(" -> Installing Custom Fields in a Journal Entry...")
	fields = {
		"Journal Entry Account": [
			{
				"label": "Payment Details",
				"fieldname": "payment_details",
				"fieldtype": "Section Break",
				"insert_after": "against_account",
			},
			{
				"label": "Payment Status",
				"fieldname": "payment_status",
				"fieldtype": "Select",
				"options": "\nOrdered\nPaid\nFailed",
				"no_copy": 1,
				"read_only": 1,
				"insert_after": "payment_details",
			},
			{
				"fieldname": "payment_details_column_break",
				"fieldtype": "Column Break",
				"insert_after": "payment_status",
			},
			{
				"label": "Reference Number",
				"fieldname": "reference_number",
				"fieldtype": "Data",
				"no_copy": 1,
				"read_only": 1,
				"insert_after": "payment_details_column_break",
			},
		]
	}

	create_custom_fields(fields)


def create_supplier_custom_fields():
	click.secho(" -> Installing Custom Fields Supplier...")
	fields = {
		"Supplier": [
			{
				"label": "LEI Number",
				"fieldname": "lei_number",
				"fieldtype": "Data",
				"owner": "Administrator",
				"insert_after": "tax_id",
			}
		]
	}

	create_custom_fields(fields)


def create_payment_request_custom_fields():
	click.secho(" -> Installing Custom Fields in a Payment Request")
	fields = {
		"Payment Request": [
			{
				"label": "Payment Type",
				"fieldname": "payment_type",
				"fieldtype": "Link",
				"options": "Payment Type",
				"mandatory_depends_on": "eval:doc.mode_of_payment == 'Wire Transfer' && doc.reference_doctype != 'Purchase Invoice' && doc.payment_request_type == 'Outward'",
				"insert_after": "mode_of_payment",
			},
			{
				"label": "Is Adhoc",
				"fieldname": "is_adhoc",
				"fieldtype": "Check",
				"depends_on": "eval:doc.mode_of_payment == 'Wire Transfer' && doc.payment_request_type ==  'Outward'",
				"insert_after": "payment_type",
			},
			{
				"label": "Net Total",
				"fieldname": "net_total",
				"fieldtype": "Currency",
				"reqd": 1,
				"insert_after": "transaction_details",
			},
			{
				"label": "Taxes Deducted",
				"fieldname": "taxes_deducted",
				"fieldtype": "Currency",
				"depends_on": "eval:doc.tax_withholding_category",
				"insert_after": "net_total",
				"read_only": 1,
			},
			{
				"label": "Apply Tax Withholding Amount",
				"fieldname": "apply_tax_withholding_amount",
				"fieldtype": "Check",
				"depends_on": "eval:doc.party_type == 'Supplier' && doc.reference_doctype != 'Purchase Invoice' && doc.payment_request_type == 'Outward'",
				"insert_after": "currency",
			},
			{
				"label": "Tax Withholding Category",
				"fieldname": "tax_withholding_category",
				"fieldtype": "Link",
				"options": "Tax Withholding Category",
				"depends_on": "eval:doc.apply_tax_withholding_amount",
				"insert_after": "apply_tax_withholding_amount",
			},
			{
				"label": "Payment Term",
				"fieldname": "payment_term",
				"fieldtype": "Link",
				"options": "Payment Term",
				"depends_on": "eval:doc.apply_tax_withholding_amount",
				"insert_after": "tax_withholding_category",
			},
			{
				"label": "",
				"fieldname": "remark_section",
				"fieldtype": "Section Break",
				"insert_after": "amended_from",
			},
			{
				"label": "Remarks",
				"fieldname": "remarks",
				"fieldtype": "Small Text",
				"depends_on": "eval:doc.payment_request_type == 'Outward'",
				"insert_after": "remark_section",
			},
		]
	}
	create_custom_fields(fields)


properties = {
	"Payment Request": [
		{
			"doctype_or_field": "DocField",
			"doctype": "Payment Request",
			"fieldname": "grand_total",
			"property": "read_only",
			"property_type": "Check",
			"value": 1,
		},
		{
			"doctype_or_field": "DocField",
			"doctype": "Payment Request",
			"fieldname": "grand_total",
			"property": "reqd",
			"property_type": "Check",
			"value": 0,
		},
	]
}


def create_payment_request_property_setter():
	for doctype in properties.keys():
		click.echo(f" -> Updating {doctype} Field Properties")
		for _property in properties.get(doctype):
			make_property_setter(_property)


def create_payment_order_custom_fields():
	click.secho(" -> Installing Custom Fields in a Payment Order")
	fields = {
		"Payment Order": [
			{
				"label": "ICICI Bank Api Info",
				"fieldname": "icici_bank_api_info",
				"fieldtype": "Section Break",
				"insert_after": "account",
			},
			{
				"label": "Unique ID",
				"fieldname": "unique_id",
				"fieldtype": "Data",
				"hidden": 1,
				"insert_after": "icici_bank_api_info",
			},
			{
				"fieldtype": "Column Break",
				"fieldname": "bank_api_info_column_break",
				"insert_after": "unique_id",
			},
			{
				"label": "File Sequence Number",
				"fieldname": "file_sequence_number",
				"fieldtype": "Data",
				"hidden": 1,
				"insert_after": "bank_api_info_column_break",
			},
			{
				"label": "File Reference Id",
				"fieldname": "file_reference_id",
				"hidden": 1,
				"fieldtype": "Data",
				"insert_after": "file_sequence_number",
			},
			{
				"label": "Payment Summary",
				"fieldname": "payment_summary",
				"fieldtype": "Section Break",
				"insert_after": "references",
			},
			{
				"label": "Summarise Payment Based On",
				"fieldname": "summarise_payment_based_on",
				"fieldtype": "Select",
				"options": "Party\nVoucher",
				"no_copy": 1,
				"insert_after": "payment_summary",
			},
			{
				"label": "Get Summary",
				"fieldname": "get_summary",
				"fieldtype": "Button",
				"insert_after": "summarise_payment_based_on",
			},
			{
				"label": "Default Mode of Transfer",
				"fieldname": "default_mode_of_transfer",
				"fieldtype": "Link",
				"options": "Mode of Transfer",
				"insert_after": "payment_summary",
			},
			{
				"label": "Summary",
				"fieldname": "summary",
				"fieldtype": "Table",
				"options": "Payment Order Summary",
				"insert_after": "default_mode_of_transfer",
				"no_copy": 1,
			},
			{
				"label": "Total",
				"fieldname": "total",
				"fieldtype": "Currency",
				"insert_after": "summary",
			},
			{
				"label": "Status",
				"fieldname": "status",
				"fieldtype": "Select",
				"options": "\nPending\nPending Approval\nPartially Approved\nApproved\nPartially Initiated\nInitiated\nRejected\nFailed",
				"read_only": 1,
				"insert_after": "posting_date",
			},
		],
		"Payment Order Reference": [
			{
				"label": "Party Type",
				"fieldname": "party_type",
				"fieldtype": "Link",
				"options": "DocType",
				"in_list_view": 1,
				"reqd": 1,
				"insert_after": "column_break_4",
			},
			{
				"label": "Party",
				"fieldname": "party",
				"fieldtype": "Dynamic Link",
				"options": "party_type",
				"in_list_view": 1,
				"reqd": 1,
				"insert_after": "party_type",
			},
			{
				"label": "Tax Withholding Category",
				"fieldname": "tax_withholding_category",
				"fieldtype": "Link",
				"options": "Tax Withholding Category",
				"depends_on": 'eval:doc.party_type == "Supplier"',
				"insert_after": "party",
			},
			{
				"label": "Is Adhoc",
				"fieldname": "is_adhoc",
				"fieldtype": "Check",
				"insert_after": "tax_withholding_category",
			},
			{
				"label": "Payment Term",
				"fieldname": "payment_term",
				"fieldtype": "Link",
				"options": "Payment Term",
				"insert_after": "amount",
			},
			{
				"label": "remarks",
				"fieldname": "remarks",
				"fieldtype": "Small Text",
				"insert_after": "payment_term",
			},
			{
				"label": "Cost Center",
				"fieldname": "cost_center",
				"fieldtype": "Link",
				"options": "Cost Center",
				"insert_after": "remarks",
			},
			{
				"label": "Project",
				"fieldname": "project",
				"fieldtype": "Link",
				"options": "Project",
				"insert_after": "cost_center",
			},
		],
	}

	create_custom_fields(fields)


def create_payment_entry_custom_fields():
	click.secho(" -> Installing Custom Fields in a Payment Entry...")
	fields = {
		"Payment Entry": [
			{
				"fieldname": "source_section",
				"fieldtype": "Section Break",
				"insert_after": "title",
			},
			{
				"label": "Source Doctype",
				"fieldname": "source_doctype",
				"fieldtype": "Link",
				"options": "DocType",
				"read_only": 1,
				"insert_after": "source_section",
			},
			{
				"fieldtype": "Column Break",
				"fieldname": "source_column",
				"insert_after": "source_doctype",
			},
			{
				"label": "Source Name",
				"fieldname": "source_name",
				"fieldtype": "Dynamic Link",
				"options": "source_doctype",
				"read_only": 1,
				"insert_after": "source_column",
			},
		]
	}

	create_custom_fields(fields)


def create_bank_account_custom_fields():
	click.secho(" -> Installing Custom Fields in a Bank Account...")
	fields = {
		"Bank Account": [
			{
				"label": "Mobile Number",
				"fieldname": "mobile_number",
				"insert_after": "iban",
				"mandatory_depends_on": "is_company_account",
				"fieldtype": "Data",
			},
			{
				"label": "Email",
				"fieldname": "email",
				"fieldtype": "Data",
				"options": "Email",
				"insert_after": "mobile_number",
				"reqd": 1,
			},
			{
				"label": "Bank Balance",
				"fieldname": "bank_balance",
				"fieldtype": "Currency",
				"insert_after": "bank_account_no",
				"read_only": 1,
			},
		]
	}

	create_custom_fields(fields)


def toggle_reqd_for_reference_in_payment_order(reqd=False):
	frappe.db.set_value(
		"DocField",
		{"parent": "Payment Order Reference", "fieldname": "reference_doctype"},
		"reqd",
		reqd,
	)
	frappe.db.set_value(
		"DocField",
		{"parent": "Payment Order Reference", "fieldname": "reference_name"},
		"reqd",
		reqd,
	)
	frappe.db.set_value(
		"DocField",
		{"parent": "Payment Order Reference", "fieldname": "amount"},
		{"reqd": reqd, "read_only": reqd},
	)
	frappe.db.set_value(
		"DocField",
		{"parent": "Payment Order", "fieldname": "payment_order_type"},
		"options",
		"\nPayment Request\nPayment Entry\nJournal Entry",
	)


def create_default_bank():
	click.echo(" -> Creating Default Banks")
	for bank in STD_BANK_LIST:
		if not frappe.db.exists("Bank", bank):
			bank_doc = frappe.new_doc("Bank")
			bank_doc.bank_name = bank
			bank_doc.is_standard = 1
			bank_doc.save()


def create_default_mode_of_transfers():
	for mot_details in DEFAULT_MODE_OF_TRANSFERS:
		if not frappe.db.exists("Mode of Transfer", mot_details.get("mode")):
			mot_details.update({"doctype": "Mode of Transfer"})
			frappe.get_doc(mot_details).insert(ignore_permissions=True)


def create_default_payment_type():
	if not frappe.db.exists("Payment Type", "Pay"):
		frappe.get_doc({"doctype": "Payment Type", "payment_type": "Pay"}).insert(
			ignore_permissions=True, ignore_mandatory=True
		)


def create_default_workflow():
	click.echo(" -> Updating workflow")

	create_default_workflow_state()
	create_default_workflow_actions()

	for workflow in DEFAULT_WORKFLOW_LIST:
		workflow = frappe._dict(workflow)
		if not frappe.db.exists(
			"Workflow",
			{
				"document_type": workflow.document_type,
				"workflow_name": workflow.workflow_name,
			},
		):
			click.echo(
				f"    |-> Creating workflow for the {workflow.document_type} Doctype."
			)
			frappe.get_doc(workflow).insert(ignore_permissions=True, ignore_links=True)


def create_default_workflow_state():
	click.echo("    |-> Creating Workflow state")

	for state in DEFAULT_WORKFLOW_STATE:
		if not frappe.db.exists("Workflow Document State", state):
			workflow_state_doc = frappe.new_doc("Workflow Document State")
			workflow_state_doc.workflow_state_name = state


def create_default_workflow_actions():
	click.echo("    |-> Creating Workflow action")

	for action in DEFAULT_WORKFLOW_ACTIONS:
		if not frappe.db.exists("Workflow Action Master", action):
			workflow_state_doc = frappe.new_doc("Workflow Action Master")
			workflow_state_doc.workflow_action_name = action
