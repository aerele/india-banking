import click
from frappe.custom.doctype.property_setter.property_setter import make_property_setter


def disable_adhoc_payment():
	click.secho(" -> Disabling Adhoc Payment in Payment Request")
	make_property_setter(
		"Payment Request",
		"is_adhoc",
		"hidden",
		1,
		"Check",
		validate_fields_for_doctype=False,
	)
