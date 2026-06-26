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
		{"label": _("Invoice"), "fieldname": "invoice", "fieldtype": "Link", "options": "Sales Invoice", "width": 180},
		{"label": _("Customer"), "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 180},
		{"label": _("Posting Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 110},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 110},
		{"label": _("Grand Total"), "fieldname": "grand_total", "fieldtype": "Currency", "options": "currency", "width": 140},
		{"label": _("Outstanding"), "fieldname": "outstanding_amount", "fieldtype": "Currency", "options": "currency", "width": 140},
		{"label": _("Currency"), "fieldname": "currency", "fieldtype": "Data", "width": 80},
	]


def get_data(filters):
	conditions = ["si.custom_auto_invoice_row_name IS NOT NULL", "si.custom_auto_invoice_row_name != ''"]
	values = {}

	if filters.get("customer"):
		conditions.append("si.customer = %(customer)s")
		values["customer"] = filters.customer
	if filters.get("status"):
		conditions.append("si.status = %(status)s")
		values["status"] = filters.status
	if filters.get("from_date"):
		conditions.append("si.posting_date >= %(from_date)s")
		values["from_date"] = filters.from_date
	if filters.get("to_date"):
		conditions.append("si.posting_date <= %(to_date)s")
		values["to_date"] = filters.to_date

	where = " AND ".join(conditions)

	return frappe.db.sql(
		f"""
		SELECT
			si.name AS invoice,
			si.customer AS customer,
			si.posting_date AS posting_date,
			si.status AS status,
			si.grand_total AS grand_total,
			si.outstanding_amount AS outstanding_amount,
			si.currency AS currency
		FROM `tabSales Invoice` si
		WHERE {where}
		ORDER BY si.posting_date DESC
		""",
		values,
		as_dict=True,
	)


def get_chart(data):
	by_status = {}
	for row in data:
		by_status[row["status"]] = by_status.get(row["status"], 0) + (row["grand_total"] or 0)

	labels = list(by_status.keys())
	return {
		"data": {
			"labels": labels,
			"datasets": [{"name": _("Grand Total"), "values": [by_status[k] for k in labels]}],
		},
		"type": "percentage",
	}
