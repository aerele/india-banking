DEFAULT_MODE_OF_TRANSFERS = [
	{
		"mode": "IMPS",
		"minimum_limit": 0,
		"maximum_limit": 200000,
		"start_time": "0:00:00",
		"end_time": "23:59:59",
		"disabled": 1,
		"priority": "1",
	},
	{
		"mode": "RTGS",
		"minimum_limit": 200000,
		"maximum_limit": 50000000,
		"start_time": "0:00:00",
		"end_time": "23:59:59",
		"disabled": 1,
		"priority": "1",
	},
	{
		"mode": "NEFT",
		"minimum_limit": 0,
		"maximum_limit": 100000000000,
		"start_time": "0:00:00",
		"end_time": "23:59:59",
		"disabled": 1,
		"priority": "1",
	},
	{
		"mode": "A2A/FT/Internal",
		"minimum_limit": 0,
		"maximum_limit": 0,
		"start_time": "0:00:00",
		"end_time": "23:59:59",
		"disabled": 1,
		"priority": "1",
	},
]

STD_BANK_LIST = [
	"Yes Bank",
	"HDFC Bank",
	"ICICI Bank",
	"Axis Bank",
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
