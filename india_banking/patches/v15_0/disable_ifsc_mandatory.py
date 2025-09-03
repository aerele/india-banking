import frappe


def execute():
	frappe.db.delete("Property Setter", "Bank Account-branch_code-reqd")
