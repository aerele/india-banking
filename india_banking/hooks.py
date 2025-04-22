app_name = "india_banking"
app_title = "India Banking"
app_publisher = "Aerele Technologies Private Limited"
app_description = "Indian Banking Integration with ERPNext"
app_email = "support@aerele.in"
app_license = "gpl-3.0"


after_install = "india_banking.install.after_install"

before_uninstall = "india_banking.uninstall.before_uninstall"

doctype_js = {
	"Payment Order": "public/js/payment_order.js",
	"Purchase Invoice": "public/js/purchase_invoice.js",
	"Bank Account": "public/js/bank_account.js",
	"Payment Request": "public/js/payment_request.js",
}

doctype_list_js = {
	"Payment Order": "public/js/payment_order_list.js",
	"Purchase Invoice": "public/js/purchase_invoice_list.js",
}

override_doctype_class = {
	"Payment Order": "india_banking.overrides.payment_order.CustomPaymentOrder",
	"Payment Request": "india_banking.overrides.payment_request.BankPaymentRequest",
}

doc_events = {
	"Bank": {
		"on_trash": "india_banking.india_banking.doc_events.bank.disallow_standard_bank_deletion"
	},
	"Bank Account": {
		"validate": "india_banking.india_banking.doc_events.bank_account.validate"
	},
	"Unreconcile Payment": {
		"on_submit": "india_banking.india_banking.doc_events.unreconcile_payment.on_submit",
	},
	"Payment Entry": {
		"on_cancel": "india_banking.india_banking.doc_events.payment_entry.on_cancel",
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
		"0 * * * *": ["india_banking.tasks.job_one_hour"],
		"0 0 * * *": ["india_banking.tasks.job_at_midnight"],
	},
}
