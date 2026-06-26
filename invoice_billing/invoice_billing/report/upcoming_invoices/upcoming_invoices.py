# Copyright (c) 2026, ramzi and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = get_columns()
	data = get_data(filters)
	chart = get_chart(data)
	return columns, data, None, chart


def get_columns():
	return [
		{"label": _("Customer"), "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 200},
		{"label": _("Invoice Date"), "fieldname": "invoice_date", "fieldtype": "Date", "width": 110},
		{"label": _("Days Until"), "fieldname": "days_until", "fieldtype": "Int", "width": 90},
		{"label": _("Frequency"), "fieldname": "frequency", "fieldtype": "Data", "width": 110},
		{"label": _("Payment Type"), "fieldname": "payment_type", "fieldtype": "Data", "width": 110},
		{"label": _("Amount"), "fieldname": "amount", "fieldtype": "Currency", "width": 130},
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
			c.name AS customer,
			ci.invoice_date AS invoice_date,
			DATEDIFF(ci.invoice_date, CURDATE()) AS days_until,
			c.custom_invoicing_frequency AS frequency,
			c.custom_payment_type AS payment_type,
			COALESCE(amt.total, 0) AS amount
		FROM `tabCustomer Invoices` ci
		INNER JOIN `tabCustomer` c ON ci.parent = c.name
		LEFT JOIN (
			SELECT parent, SUM(qty * rate) AS total
			FROM `tabCustomer Billing Item`
			WHERE parenttype = 'Customer'
			GROUP BY parent
		) amt ON amt.parent = c.name
		WHERE {where}
		ORDER BY ci.invoice_date ASC
		""",
		values,
		as_dict=True,
	)


def get_chart(data):
	by_date = {}
	for row in data:
		key = str(row["invoice_date"])
		by_date[key] = by_date.get(key, 0) + (row["amount"] or 0)

	labels = sorted(by_date.keys())
	return {
		"data": {
			"labels": labels,
			"datasets": [{"name": _("Upcoming Amount"), "values": [by_date[k] for k in labels]}],
		},
		"type": "bar",
	}
