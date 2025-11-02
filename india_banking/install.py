import click
import frappe
from frappe import make_property_setter
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from india_banking.default import (
	ALLOWED_PAYMENT_DOCTYPE,
	DEFAULT_MODE_OF_TRANSFERS,
	DEFAULT_ROLES,
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
	update_allowed_payment_doctypes()
	create_default_roles()


def make_custom_fields():
	create_bank_doc_custom_fields()
	create_bank_account_custom_fields()
	create_payment_request_custom_fields()
	create_payment_order_custom_fields()
	create_payment_entry_custom_fields()
	create_journal_entry_custom_fields()


def update_allowed_payment_doctypes():
	frappe.db.set_single_value(
		"India Banking Settings",
		"allowed_payment_doctypes",
		"\n".join(ALLOWED_PAYMENT_DOCTYPE),
	)


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
				"options": "\nOrdered\nPayment Ordered\nPaid\nFailed",
				"no_copy": 1,
				"read_only": 1,
				"insert_after": "payment_details",
			},
			{
				"label": "Reference Details",
				"fieldname": "reference_details",
				"fieldtype": "Data",
				"no_copy": 1,
				"read_only": 1,
				"insert_after": "payment_status",
			},
			{
				"fieldname": "payment_details_column_break",
				"fieldtype": "Column Break",
				"insert_after": "reference_details",
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
	custom_field = [
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
			"read_only": 1,
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

	create_custom_fields({"Payment Request": custom_field})


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
	],
	"Bank Account": [
		{
			"doctype_or_field": "DocField",
			"doctype": "Bank Account",
			"fieldname": "branch_code",
			"property": "label",
			"property_type": "Data",
			"value": "IFSC Code",
		},
		{
			"doctype_or_field": "DocField",
			"doctype": "Bank Account",
			"fieldname": "branch_code",
			"property": "reqd",
			"property_type": "Data",
			"value": 1,
		},
	],
	"Payment Order": [
		{
			"doctype_or_field": "DocField",
			"doctype": "Payment Order",
			"fieldname": "party",
			"property": "fieldtype",
			"property_type": "Link",
			"value": "Data",
		},
	],
	"Payment Order Reference": [
		{
			"doctype_or_field": "DocField",
			"doctype": "Payment Order Reference",
			"fieldname": "bank_account",
			"property": "reqd",
			"property_type": "Check",
			"value": 0,
		},
	],
}


def create_property_setter():
	for doctype in properties.keys():
		click.echo(f" -> Updating {doctype} Field Properties")
		for _property in properties.get(doctype):
			make_property_setter(_property)


def create_payment_order_custom_fields():
	click.secho(" -> Installing Custom Fields in a Payment Order")
	fields = {
		"Payment Order": [
			{
				"label": "Status",
				"fieldname": "status",
				"fieldtype": "Select",
				"options": "\nPending\nPending Approval\nPartially Approved\nApproved\nPartially Initiated\nInitiated\nRejected\nFailed",
				"read_only": 1,
				"insert_after": "posting_date",
			},
			{
				"label": "File Reference Details",
				"fieldname": "file_reference_details_section",
				"fieldtype": "Section Break",
				"insert_after": "account",
			},
			{
				"label": "File Sequence Number",
				"fieldname": "file_sequence_number",
				"fieldtype": "Data",
				"read_only": 1,
				"insert_after": "file_reference_details_section",
			},
			{
				"label": "",
				"fieldname": "payment_summary",
				"fieldtype": "Section Break",
				"insert_after": "references",
			},
			{
				"label": "Default Mode of Transfer",
				"fieldname": "default_mode_of_transfer",
				"fieldtype": "Link",
				"options": "Mode of Transfer",
				"insert_after": "payment_summary",
			},
			{
				"label": "Payment Summary",
				"fieldname": "payment_summary2",
				"fieldtype": "Section Break",
				"insert_after": "default_mode_of_transfer",
			},
			{
				"label": "Summarise Payment Based On",
				"fieldname": "summarise_payment_based_on",
				"fieldtype": "Select",
				"options": "Party\nVoucher",
				"no_copy": 1,
				"insert_after": "payment_summary2",
			},
			{
				"label": "Get Summary",
				"fieldname": "get_summary",
				"fieldtype": "Button",
				"insert_after": "summarise_payment_based_on",
			},
			{
				"label": "Summary",
				"fieldname": "summary",
				"fieldtype": "Table",
				"options": "Payment Order Summary",
				"insert_after": "get_summary",
				"no_copy": 1,
			},
			{
				"label": "Total",
				"fieldname": "total",
				"fieldtype": "Currency",
				"insert_after": "summary",
			},
			{
				"label": "Accounting Dimensions",
				"fieldname": "accounting_dimensions",
				"fieldtype": "Section Break",
				"insert_after": "account",
				"collapsible": 1,
			},
			{
				"label": "Project",
				"fieldname": "project",
				"fieldtype": "Link",
				"options": "Project",
				"no_copy": 1,
				"insert_after": "accounting_dimensions",
			},
			{
				"label": "",
				"fieldname": "accounting_dimensions_column_break",
				"fieldtype": "Column Break",
				"insert_after": "project",
			},
			{
				"label": "Cost Center",
				"fieldname": "cost_center",
				"fieldtype": "Link",
				"options": "Cost Center",
				"no_copy": 1,
				"insert_after": "accounting_dimensions_column_break",
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
			{
				"label": "Payment Entry",
				"fieldname": "payment_entry",
				"fieldtype": "Data",
				"insert_after": "amount",
				"read_only": 1,
			},
			{
				"label": "Journal Entry Account",
				"fieldname": "journal_entry_account",
				"fieldtype": "Data",
				"hidden": 1,
				"insert_after": "payment_entry",
			},
			{
				"label": "Bank",
				"fieldname": "bank",
				"fieldtype": "Data",
				"read_only": 1,
				"insert_after": "journal_entry_account",
				"fetch_from": "bank_account.bank",
			},
			{
				"label": "Bank Account No",
				"fieldname": "bank_account_no",
				"fieldtype": "Data",
				"read_only": 1,
				"insert_after": "bank",
				"fetch_from": "bank_account.bank_account_no",
			},
			{
				"label": "Branch Code",
				"fieldname": "branch_code",
				"fieldtype": "Data",
				"read_only": 1,
				"insert_after": "bank_account_no",
				"fetch_from": "bank_account.branch_code",
			},
			{
				"label": "Account Name",
				"fieldname": "account_name",
				"fieldtype": "Data",
				"read_only": 1,
				"insert_after": "branch_code",
				"fetch_from": "bank_account.account_name",
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
				"no_copy": 1,
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
				"no_copy": 1,
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
				"mandatory_depends_on": "is_company_account",
				"fieldtype": "Data",
				"insert_after": "iban",
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
				"depends_on": "eval: doc.is_company_account",
			},
			{
				"label": "Currency",
				"fieldname": "currency",
				"fieldtype": "Link",
				"options": "Currency",
				"insert_after": "email",
				"reqd": 0,
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
	companies = frappe.get_all(
		"Company", ["name", "default_payable_account"], as_list=1
	)
	for company, default_payable_account in companies:
		if not frappe.db.exists(
			"Payment Type",
			{
				"payment_type": "Pay",
				"account": default_payable_account,
				"company": company,
			},
		):
			frappe.get_doc(
				{
					"doctype": "Payment Type",
					"payment_type": "Pay",
					"company": company,
					"account": default_payable_account,
					"is_default": 1,
				}
			).insert(ignore_permissions=True, ignore_mandatory=True)


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


def create_default_roles():
	click.echo(" -> Creating Default Roles")
	for role in DEFAULT_ROLES:
		if not frappe.db.exists("Role", role):
			role_doc = frappe.new_doc("Role")
			role_doc.role_name = "Payment Manager"
			role_doc.save()
