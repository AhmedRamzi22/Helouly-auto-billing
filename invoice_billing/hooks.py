app_name = "invoice_billing"
app_title = "Invoice Billing"
app_publisher = "ramzi"
app_description = "auto billing"
app_email = "ahmed.ramzi222@gmail.com"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "invoice_billing",
# 		"logo": "/assets/invoice_billing/logo.png",
# 		"title": "Invoice Billing",
# 		"route": "/invoice_billing",
# 		"has_permission": "invoice_billing.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/invoice_billing/css/invoice_billing.css"
# app_include_js = "/assets/invoice_billing/js/invoice_billing.js"

# include js, css files in header of web template
# web_include_css = "/assets/invoice_billing/css/invoice_billing.css"
# web_include_js = "/assets/invoice_billing/js/invoice_billing.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "invoice_billing/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {
	"Customer": "public/js/customer.js",
	"Auto Billing Setting": "public/js/auto_billing_setting.js",
}
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "invoice_billing/public/icons.svg"

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
# 	"methods": "invoice_billing.utils.jinja_methods",
# 	"filters": "invoice_billing.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "invoice_billing.install.before_install"
# after_install = "invoice_billing.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "invoice_billing.uninstall.before_uninstall"
# after_uninstall = "invoice_billing.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "invoice_billing.utils.before_app_install"
# after_app_install = "invoice_billing.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "invoice_billing.utils.before_app_uninstall"
# after_app_uninstall = "invoice_billing.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "invoice_billing.notifications.get_notification_config"

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
	"Customer": {
		"validate": "invoice_billing.customer.validate",
	},
	"Sales Invoice": {
		"on_cancel": "invoice_billing.customer.on_sales_invoice_cancel",
		"on_trash": "invoice_billing.customer.on_sales_invoice_trash",
	},
}

# Scheduled Tasks
# ---------------

scheduler_events = {
	"daily": [
		"invoice_billing.notification.notify_upcoming_invoices",
		"invoice_billing.customer.create_due_invoices",
	],
}

# scheduler_events = {
# 	"all": [
# 		"invoice_billing.tasks.all"
# 	],
# 	"daily": [
# 		"invoice_billing.tasks.daily"
# 	],
# 	"hourly": [
# 		"invoice_billing.tasks.hourly"
# 	],
# 	"weekly": [
# 		"invoice_billing.tasks.weekly"
# 	],
# 	"monthly": [
# 		"invoice_billing.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "invoice_billing.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "invoice_billing.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "invoice_billing.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["invoice_billing.utils.before_request"]
# after_request = ["invoice_billing.utils.after_request"]

# Job Events
# ----------
# before_job = ["invoice_billing.utils.before_job"]
# after_job = ["invoice_billing.utils.after_job"]

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
# 	"invoice_billing.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

after_migrate = ["invoice_billing.setup.dashboard.setup_dashboard"]

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []

