import json

import frappe

from india_banking.india_banking.doc_events.bank_account.bank_account import (
	get_bank_details_from_branch_code,
)
from india_banking.install import create_bank_account_custom_fields


def execute():
	create_bank_account_custom_fields()
	bank_accounts = frappe.get_all(
		"Bank Account", {"branch_code": ["!=", None]}, ["name", "branch_code"]
	)
	for row in bank_accounts:
		bank_details_json = get_bank_details_from_branch_code(row.branch_code)
		frappe.db.set_value(
			"Bank Account", row.name, "bank_details_json", json.dumps(bank_details_json)
		)
