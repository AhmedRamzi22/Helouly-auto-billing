# Copyright (c) 2026, ramzi and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{"label": _("Log"), "fieldname": "log", "fieldtype": "Link", "options": "Customer Auto Billing Email Log", "width": 180},
		{"label": _("Posting Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 110},
		{"label": _("Customer"), "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 180},
		{"label": _("Invoice Date"), "fieldname": "invoice_date", "fieldtype": "Date", "width": 110},
		{"label": _("Users Notified"), "fieldname": "users", "fieldtype": "Int", "width": 110},
		{"label": _("Recipients"), "fieldname": "recipients", "fieldtype": "Data", "width": 320},
	]


def get_data(filters):
	conditions = ["1 = 1"]
	values = {}
	if filters.get("customer"):
		conditions.append("log.customer = %(customer)s")
		values["customer"] = filters.customer
	if filters.get("from_date"):
		conditions.append("log.posting_date >= %(from_date)s")
		values["from_date"] = filters.from_date
	if filters.get("to_date"):
		conditions.append("log.posting_date <= %(to_date)s")
		values["to_date"] = filters.to_date

	where = " AND ".join(conditions)

	return frappe.db.sql(
		f"""
		SELECT
			log.name AS log,
			log.posting_date AS posting_date,
			log.customer AS customer,
			log.invoice_date AS invoice_date,
			COUNT(u.name) AS users,
			GROUP_CONCAT(u.user SEPARATOR ', ') AS recipients
		FROM `tabCustomer Auto Billing Email Log` log
		LEFT JOIN `tabEmail Log User` u
			ON u.parent = log.name AND u.parentfield = 'users'
		WHERE {where}
		GROUP BY log.name
		ORDER BY log.posting_date DESC, log.creation DESC
		""",
		values,
		as_dict=True,
	)
