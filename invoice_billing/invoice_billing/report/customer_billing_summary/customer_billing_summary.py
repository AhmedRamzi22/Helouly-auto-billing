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
		{"label": _("Customer"), "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 200},
		{"label": _("Frequency"), "fieldname": "frequency", "fieldtype": "Data", "width": 100},
		{"label": _("Payment Type"), "fieldname": "payment_type", "fieldtype": "Data", "width": 100},
		{"label": _("Start Date"), "fieldname": "start_date", "fieldtype": "Date", "width": 100},
		{"label": _("End Date"), "fieldname": "end_date", "fieldtype": "Date", "width": 100},
		{"label": _("Next Invoice"), "fieldname": "next_invoice", "fieldtype": "Date", "width": 110},
		{"label": _("Scheduled"), "fieldname": "scheduled", "fieldtype": "Int", "width": 90},
		{"label": _("Invoiced"), "fieldname": "invoiced", "fieldtype": "Int", "width": 90},
		{"label": _("Remaining"), "fieldname": "remaining", "fieldtype": "Int", "width": 90},
		{"label": _("Amount / Invoice"), "fieldname": "amount", "fieldtype": "Currency", "width": 140},
		{"label": _("Projected Remaining"), "fieldname": "projected", "fieldtype": "Currency", "width": 160},
	]


def get_data(filters):
	conditions = ["c.custom_enabled_auto_invoice = 1"]
	values = {}
	if filters.get("customer"):
		conditions.append("c.name = %(customer)s")
		values["customer"] = filters.customer
	if filters.get("frequency"):
		conditions.append("c.custom_invoicing_frequency = %(frequency)s")
		values["frequency"] = filters.frequency

	where = " AND ".join(conditions)

	rows = frappe.db.sql(
		f"""
		SELECT
			c.name AS customer,
			c.custom_invoicing_frequency AS frequency,
			c.custom_payment_type AS payment_type,
			c.custom_invoicing_start_date AS start_date,
			c.custom_invoicing_end_date AS end_date,
			COALESCE(amt.total, 0) AS amount,
			COUNT(ci.name) AS scheduled,
			SUM(CASE WHEN ci.invoiced = 1 THEN 1 ELSE 0 END) AS invoiced,
			SUM(CASE WHEN ci.invoiced = 0 THEN 1 ELSE 0 END) AS remaining,
			MIN(CASE WHEN ci.invoiced = 0 THEN ci.invoice_date END) AS next_invoice
		FROM `tabCustomer` c
		LEFT JOIN `tabCustomer Invoices` ci
			ON ci.parent = c.name AND ci.parenttype = 'Customer'
		LEFT JOIN (
			SELECT parent, SUM(qty * rate) AS total
			FROM `tabCustomer Billing Item`
			WHERE parenttype = 'Customer'
			GROUP BY parent
		) amt ON amt.parent = c.name
		WHERE {where}
		GROUP BY c.name
		ORDER BY next_invoice ASC
		""",
		values,
		as_dict=True,
	)

	for row in rows:
		row["projected"] = (row.get("remaining") or 0) * (row.get("amount") or 0)

	return rows
