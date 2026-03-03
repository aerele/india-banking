app_name = "india_banking"
app_title = "India Banking"
app_publisher = "Aerele Technologies Private Limited"
app_description = "Indian Banking Integration with ERPNext"
app_email = "support@aerele.in"
app_license = "gpl-3.0"


before_uninstall = "india_banking.uninstall.before_uninstall"
after_install = "india_banking.install.after_install"


before_tests = "india_banking.setup.utils.before_tests"


doctype_js = {
	"Bank Account": "public/js/bank_account.js",
	"Purchase Invoice": "public/js/purchase_invoice.js",
	"Payment Request": "public/js/payment_request.js",
	"Payment Order": "public/js/payment_order.js",
}


doctype_list_js = {
	"Payment Request": "public/js/payment_request_list.js",
	"Purchase Invoice": "public/js/purchase_invoice_list.js",
	"Payment Order": "public/js/payment_order_list.js",
}


override_doctype_class = {
	"Payment Request": "india_banking.overrides.payment_request.payment_request.BankPaymentRequest",
	"Payment Order": "india_banking.overrides.payment_order.CustomPaymentOrder",
}


doc_events = {
	"Bank": {
		"on_trash": "india_banking.india_banking.doc_events.bank.bank.disallow_standard_bank_deletion",
	},
	"Bank Account": {
		"validate": "india_banking.india_banking.doc_events.bank_account.bank_account.validate",
	},
	"Payment Request": {
		"autoname": "india_banking.india_banking.doc_events.payment_request.payment_request.autoname",
	},
	"Payment Order": {
		"autoname": "india_banking.utils.update_series",
	},
	"Payment Entry": {
		"on_cancel": "india_banking.india_banking.doc_events.payment_entry.on_cancel",
	},
	"Unreconcile Payment": {
		"on_submit": "india_banking.india_banking.doc_events.unreconcile_payment.on_submit",
	},
}


accounting_dimension_doctypes = [
	"Payment Order",
	"Payment Order Reference",
	"Payment Order Summary",
]


scheduler_events = {
	"daily": ["india_banking.tasks.daily"],
	"cron": {
		"*/20 * * * *": ["india_banking.tasks.job_twenty_minutes"],
		"*/5 * * * *": ["india_banking.tasks.process_payment_in_the_background"],
		"0 * * * *": ["india_banking.tasks.job_one_hour"],
		"0 0 * * *": ["india_banking.tasks.job_at_midnight"],
	},
}


ignore_links_on_delete = ["Unreconcile Bank Payment", "Bank Payment Allocation"]
default_log_clearing_doctypes = {
	"India Banking Request Log": 60,
}
