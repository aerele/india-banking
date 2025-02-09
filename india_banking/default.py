PAYMENT_SUMMARIES_FIELDS = [
	"party_type",
	"party",
	"bank_account",
	"account",
	"cost_center",
	"project",
	"tax_withholding_category",
	"reference_doctype",
	"reference_name",
	"payment_entry",
	"journal_entry_account",
]

DEFAULT_MODE_OF_TRANSFERS = [
	{
		"mode": "A2A/FT/Internal",
		"minimum_limit": 1,
		"maximum_limit": 500000000,
		"start_time": "0:00:00",
		"end_time": "23:59:59",
		"disabled": 0,
		"priority": "1",
		"is_bank_specific": 1,
	},
	{
		"mode": "IMPS",
		"minimum_limit": 1,
		"maximum_limit": 200000,
		"start_time": "0:00:00",
		"end_time": "23:59:59",
		"disabled": 0,
		"priority": "2",
	},
	{
		"mode": "RTGS",
		"minimum_limit": 200000,
		"maximum_limit": 500000000,
		"start_time": "0:00:00",
		"end_time": "23:59:59",
		"disabled": 0,
		"priority": "3",
	},
	{
		"mode": "NEFT",
		"minimum_limit": 1,
		"maximum_limit": 500000000,
		"start_time": "0:00:00",
		"end_time": "23:59:59",
		"disabled": 0,
		"priority": "4",
	},
]

STD_BANK_LIST = [
	"Axis Bank",
	"HDFC Bank",
	"ICICI Bank",
	"Kotak Mahindra Bank",
]

DEFAULT_WORKFLOW_STATE = [
	"Pending",
	"Approved",
]

DEFAULT_WORKFLOW_ACTIONS = ["Approve", "Reject"]

DEFAULT_WORKFLOW_LIST = [
	{
		"doctype": "Workflow",
		"document_type": "Bank Account",
		"workflow_name": "Bank Account Approval",
		"workflow_state_field": "workflow_state",
		"is_active": 1,
		"states": [
			{
				"allow_edit": "All",
				"doc_status": "0",
				"parent": "Bank Account Approval",
				"parentfield": "states",
				"parenttype": "Workflow",
				"state": "Pending",
				"update_value": "Pending",
			},
			{
				"allow_edit": "Accounts Manager",
				"doc_status": "0",
				"parent": "Bank Account Approval",
				"parentfield": "states",
				"parenttype": "Workflow",
				"state": "Approved",
				"update_value": "Approved",
			},
		],
		"transitions": [
			{
				"state": "Pending",
				"action": "Approve",
				"next_state": "Approved",
				"allowed": "Accounts Manager",
				"allow_self_approval": 1,
				"parent": "Bank Account Approval",
				"parentfield": "transitions",
				"parenttype": "Workflow",
			},
			{
				"action": "Reject",
				"next_state": "Pending",
				"allowed": "Accounts Manager",
				"allow_self_approval": 1,
				"parent": "Bank Account Approval",
				"parentfield": "transitions",
				"parenttype": "Workflow",
				"state": "Approved",
			},
		],
	}
]

ALLOWED_PAYMENT_DOCTYPE = ["Payment Request", "Payment Entry", "Bank Entry(JV)"]
