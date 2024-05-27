app_name = "india_banking"
app_title = "India Banking"
app_publisher = "Aerele Technologies Private Limited"
app_description = "Indian Banking Integration with ERPNext"
app_email = "support@aerele.in"
app_license = "gpl-3.0"
# required_apps = []

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/india_banking/css/india_banking.css"
# app_include_js = "/assets/india_banking/js/india_banking.js"

# include js, css files in header of web template
# web_include_css = "/assets/india_banking/css/india_banking.css"
# web_include_js = "/assets/india_banking/js/india_banking.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "india_banking/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

doctype_js = {
	"Payment Order" : "public/js/payment_order.js",
	"Purchase Order" : "public/js/purchase_order.js",
	"Purchase Invoice": "public/js/purchase_invoice.js",
	"Payment Type": "public/js/payment_type.js",

}

doctype_list_js = {"Payment Order" : "public/js/payment_order_list.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "india_banking/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "india_banking.utils.jinja_methods",
# 	"filters": "india_banking.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "india_banking.install.before_install"
# after_install = "india_banking.install.after_install"
after_install = "india_banking.india_banking.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "india_banking.uninstall.before_uninstall"
# after_uninstall = "india_banking.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "india_banking.utils.before_app_install"
# after_app_install = "india_banking.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "india_banking.utils.before_app_uninstall"
# after_app_uninstall = "india_banking.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "india_banking.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

override_doctype_class = {
	"Payment Order": "india_banking.india_banking.override.payment_order.CustomPaymentOrder",
	"Payment Entry": "india_banking.india_banking.override.payment_entry.CustomPaymentEntry",
	"Bank":  "india_banking.india_banking.override.bank.CustomBank"
}


# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

doc_events = {
	"Bank Account": {
		"validate": "india_banking.india_banking.doc_events.bank_account.validate_ifsc_code",
	}
}

# accounting_dimension_doctypes = ['Bank Payment Request', 'Payment Order', 'Payment Order Reference', 'Payment Order Summary']
accounting_dimension_doctypes = ['Bank Payment Request']

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"india_banking.tasks.all"
# 	],
# 	"daily": [
# 		"india_banking.tasks.daily"
# 	],
# 	"hourly": [
# 		"india_banking.tasks.hourly"
# 	],
# 	"weekly": [
# 		"india_banking.tasks.weekly"
# 	],
# 	"monthly": [
# 		"india_banking.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "india_banking.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "india_banking.event.get_events"
# }

override_whitelisted_methods = {
	"erpnext.accounts.doctype.payment_request.payment_request.make_payment_request": "india_banking.india_banking.override.payment_request.make_payment_request"
}

#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "india_banking.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["india_banking.utils.before_request"]
# after_request = ["india_banking.utils.after_request"]

# Job Events
# ----------
# before_job = ["india_banking.utils.before_job"]
# after_job = ["india_banking.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"india_banking.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

