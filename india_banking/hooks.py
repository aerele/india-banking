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
	"Payment Type": "public/js/payment_type.js",
	"Bank Account": "public/js/bank_account.js",
	"Payment Request": "public/js/payment_request.js",
}

doctype_list_js = {
	"Payment Order": "public/js/payment_order_list.js",
}


override_doctype_class = {
	"Payment Order": "india_banking.overrides.payment_order.CustomPaymentOrder",
	"Payment Entry": "india_banking.overrides.payment_entry.CustomPaymentEntry",
	"Payment Request": "india_banking.overrides.payment_request.BankPaymentRequest",
}

doc_events = {
	"Bank": {"on_trash": "india_banking.india_banking.doc_events.bank.bank_on_trash"},
	"Bank Account": {
		"validate": "india_banking.india_banking.doc_events.bank.validate_ifsc_code"
	},
}

accounting_dimension_doctypes = [
	"Payment Order Reference",
	"Payment Order Summary",
]

scheduler_events = {"daily": ["india_banking.tasks.daily"]}
