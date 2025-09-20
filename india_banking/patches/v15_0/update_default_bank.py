import frappe

from india_banking.install import create_default_bank


def execute():
	try:
		create_default_bank()
	except Exception:
		frappe.log_error(
			"Failed to create default bank account", frappe.get_traceback()
		)
