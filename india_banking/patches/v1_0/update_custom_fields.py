from india_banking.install import make_custom_fields
from india_banking.uninstall import delete_custom_fields


def execute():
	delete_custom_fields()
	make_custom_fields()
