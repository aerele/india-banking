import frappe
import json
import requests
from frappe.utils import getdate


def update_bank_transactions(bank_doc, statements):
	for statement in statements:
		if not frappe.db.exists("Bank Transaction", {"bank_account": bank_doc.name, "reference_number": statement.transaction_id}):
			bank_transaction_doc = frappe.new_doc("Bank Transaction")
			bank_transaction_doc.update(statement)
			bank_transaction_doc.save()
