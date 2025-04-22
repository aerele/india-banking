import frappe

from india_banking.install import make_custom_fields, toggle_payment_request_creation
from india_banking.uninstall import delete_custom_fields


def execute():
	toggle_payment_request_creation()
	delete_custom_fields()
	make_custom_fields()