import click
import frappe


def after_install():
	toggle_payment_request_creation(True)


def before_uninstall():
	toggle_payment_request_creation(False)


def toggle_payment_request_creation(allow=True):
	click.secho(
		"* {} Payment Request Creation...".format("Enabling" if allow else "Disabling")
	)
	frappe.db.set_value(
		"DocType", "Payment Request", {"in_create": not allow, "track_changes": allow}
	)
