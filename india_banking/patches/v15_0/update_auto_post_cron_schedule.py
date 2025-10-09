import frappe

from india_banking.utils import minutes_to_cron


def execute():
	"""Update the cron schedule for auto-posting payments."""
	try:
		settings = frappe.get_single("India Banking Settings")
		cron_format = minutes_to_cron(settings.get("retry_interval_minutes", 5))

		frappe.db.set_value(
			"Scheduled Job Type",
			"tasks.process_payment_in_the_background",
			{
				"cron_format": cron_format,
				"stopped": not settings.get("auto_post_payments", False),
			},
			update_modified=False,
		)
	except Exception:
		frappe.log_error(
			"Failed Update the cron schedule", frappe.get_traceback(with_context=True)
		)
