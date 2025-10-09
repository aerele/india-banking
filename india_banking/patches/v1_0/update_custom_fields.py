from india_banking.install import make_custom_fields, toggle_payment_request_creation


def execute():
	toggle_payment_request_creation()
	make_custom_fields()
