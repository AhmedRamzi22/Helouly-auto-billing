# Copyright (c) 2026, ramzi and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = get_columns()
	data = get_data(filters)
	chart = get_chart(data)
	report_summary = get_summary(data)
	return columns, data, None, chart, report_summary


def get_columns():
	return [
		{"label": _("Month"), "fieldname": "month", "fieldtype": "Data", "width": 140},
		{"label": _("Invoices"), "fieldname": "invoices", "fieldtype": "Int", "width": 110},
		{"label": _("Forecast Amount"), "fieldname": "forecast", "fieldtype": "Currency", "width": 160},
	]


def get_data(filters):
	conditions = ["ci.parenttype = 'Customer'", "ci.invoiced = 0", "c.custom_enabled_auto_invoice = 1"]
	values = {}

	if filters.get("customer"):
		conditions.append("c.name = %(customer)s")
		values["customer"] = filters.customer
	if filters.get("from_date"):
		conditions.append("ci.invoice_date >= %(from_date)s")
		values["from_date"] = filters.from_date
	if filters.get("to_date"):
		conditions.append("ci.invoice_date <= %(to_date)s")
		values["to_date"] = filters.to_date

	where = " AND ".join(conditions)

	return frappe.db.sql(
		f"""
		SELECT
			DATE_FORMAT(ci.invoice_date, '%%b %%Y') AS month,
			DATE_FORMAT(ci.invoice_date, '%%Y-%%m') AS sort_key,
			COUNT(*) AS invoices,
			SUM(COALESCE(amt.total, 0)) AS forecast
		FROM `tabCustomer Invoices` ci
		INNER JOIN `tabCustomer` c ON ci.parent = c.name
		LEFT JOIN (
			SELECT parent, SUM(qty * rate) AS total
			FROM `tabCustomer Billing Item`
			WHERE parenttype = 'Customer'
			GROUP BY parent
		) amt ON amt.parent = c.name
		WHERE {where}
		GROUP BY DATE_FORMAT(ci.invoice_date, '%%Y-%%m')
		ORDER BY sort_key ASC
		""",
		values,
		as_dict=True,
	)


def get_chart(data):
	labels = [row["month"] for row in data]
	values = [row["forecast"] or 0 for row in data]
	return {
		"data": {
			"labels": labels,
			"datasets": [{"name": _("Forecast Amount"), "values": values}],
		},
		"type": "line",
		"colors": ["#2490ef"],
		"axisOptions": {"xIsSeries": True},
	}


def get_summary(data):
	total = sum(row["forecast"] or 0 for row in data)
	count = sum(row["invoices"] or 0 for row in data)
	return [
		{"value": total, "label": _("Total Forecast"), "datatype": "Currency", "indicator": "Blue"},
		{"value": count, "label": _("Total Upcoming Invoices"), "datatype": "Int", "indicator": "Green"},
	]
