# Copyright (c) 2026, ramzi and contributors
# For license information, please see license.txt

"""Idempotent creation of the Auto Invoicing dashboard objects.

Creates the number cards, dashboard charts, an overview HTML block and the
Dashboard. Safe to run repeatedly (used from the `after_migrate` hook), so a
fresh site gets the full dashboard automatically.
"""

import json

import frappe

MODULE = "Invoice Billing"
HTML_BLOCK = "auto-invoicing-overview"

NUMBER_CARDS = [
	{
		"name": "Auto Invoice Customers",
		"label": "Auto Invoice Customers",
		"document_type": "Customer",
		"filters_json": json.dumps([["Customer", "custom_enabled_auto_invoice", "=", 1]]),
		"color": "#29cd42",
	},
	{
		"name": "Upcoming Invoices",
		"label": "Upcoming Invoices",
		"document_type": "Customer Invoices",
		"parent_document_type": "Customer",
		"filters_json": json.dumps(
			[
				["Customer Invoices", "parenttype", "=", "Customer"],
				["Customer Invoices", "invoiced", "=", 0],
			]
		),
		"color": "#2490ef",
	},
	{
		"name": "Auto-Generated Invoices",
		"label": "Auto-Generated Invoices",
		"document_type": "Sales Invoice",
		"filters_json": json.dumps([["Sales Invoice", "custom_auto_invoice_row_name", "is", "set"]]),
		"color": "#7b6cf6",
	},
	{
		"name": "Billing Notifications Sent",
		"label": "Billing Notifications Sent",
		"document_type": "Customer Auto Billing Email Log",
		"filters_json": json.dumps([]),
		"color": "#ff9800",
	},
]

CHARTS = [
	{
		"name": "Invoice Forecast (Monthly)",
		"chart_type": "Report",
		"report_name": "Invoice Forecast",
		"use_report_chart": 1,
		"type": "Line",
	},
	{
		"name": "Auto Invoice Value (Monthly)",
		"chart_type": "Sum",
		"document_type": "Sales Invoice",
		"based_on": "posting_date",
		"value_based_on": "grand_total",
		"timeseries": 1,
		"time_interval": "Monthly",
		"timespan": "Last Year",
		"type": "Bar",
		"filters_json": json.dumps([["Sales Invoice", "custom_auto_invoice_row_name", "is", "set"]]),
	},
	{
		"name": "Upcoming vs Invoiced",
		"chart_type": "Group By",
		"document_type": "Customer Invoices",
		"parent_document_type": "Customer",
		"group_by_type": "Count",
		"group_by_based_on": "invoiced",
		"type": "Donut",
		"filters_json": json.dumps([["Customer Invoices", "parenttype", "=", "Customer"]]),
	},
]

OVERVIEW_HTML = """
<div style="padding:16px;border:1px solid #e2e8f0;border-radius:10px;background:#f8fafc;">
  <h3 style="margin:0 0 8px;">📋 Auto Invoicing</h3>
  <p style="margin:0 0 8px;color:#475569;">
    Customers with <b>Enabled Auto Invoice</b> are automatically scheduled and
    invoiced on their billing day. Use the cards and charts below to monitor the
    upcoming pipeline, forecasted revenue and generated invoices.
  </p>
  <ul style="margin:0;color:#475569;">
    <li><b>Upcoming Invoices</b> &mdash; what is due and when.</li>
    <li><b>Invoice Forecast</b> &mdash; projected revenue per month.</li>
    <li><b>Customer Billing Summary</b> &mdash; schedule status per customer.</li>
    <li><b>Auto Generated Invoices</b> &mdash; invoices created by the system.</li>
    <li><b>Billing Notifications Log</b> &mdash; who was notified, and when.</li>
  </ul>
</div>
"""


def setup_dashboard():
	_create_number_cards()
	_create_charts()
	_create_html_block()
	_create_dashboard()
	frappe.db.commit()


def _create_number_cards():
	for card in NUMBER_CARDS:
		if frappe.db.exists("Number Card", card["name"]):
			doc = frappe.get_doc("Number Card", card["name"])
		else:
			doc = frappe.new_doc("Number Card")
			doc.name = card["name"]
		doc.update(
			{
				"label": card["label"],
				"type": "Document Type",
				"function": "Count",
				"document_type": card["document_type"],
				"parent_document_type": card.get("parent_document_type"),
				"filters_json": card["filters_json"],
				"is_public": 1,
				"show_percentage_stats": 1,
				"stats_time_interval": "Daily",
				"module": MODULE,
				"color": card.get("color"),
			}
		)
		doc.save(ignore_permissions=True)


def _create_charts():
	for chart in CHARTS:
		if frappe.db.exists("Dashboard Chart", chart["name"]):
			doc = frappe.get_doc("Dashboard Chart", chart["name"])
		else:
			doc = frappe.new_doc("Dashboard Chart")
			doc.chart_name = chart["name"]
		doc.update(
			{
				"chart_type": chart["chart_type"],
				"document_type": chart.get("document_type"),
				"parent_document_type": chart.get("parent_document_type"),
				"report_name": chart.get("report_name"),
				"use_report_chart": chart.get("use_report_chart", 0),
				"based_on": chart.get("based_on"),
				"value_based_on": chart.get("value_based_on"),
				"group_by_type": chart.get("group_by_type"),
				"group_by_based_on": chart.get("group_by_based_on"),
				"timeseries": chart.get("timeseries", 0),
				"time_interval": chart.get("time_interval"),
				"timespan": chart.get("timespan"),
				"type": chart.get("type"),
				"filters_json": chart.get("filters_json", "[]"),
				"is_public": 1,
				"module": MODULE,
			}
		)
		doc.save(ignore_permissions=True)


def _create_html_block():
	if frappe.db.exists("Custom HTML Block", HTML_BLOCK):
		doc = frappe.get_doc("Custom HTML Block", HTML_BLOCK)
	else:
		doc = frappe.new_doc("Custom HTML Block")
		doc.name = HTML_BLOCK
	doc.html = OVERVIEW_HTML
	doc.private = 0
	doc.save(ignore_permissions=True)


def _create_dashboard():
	name = "Auto Invoicing"
	if frappe.db.exists("Dashboard", name):
		doc = frappe.get_doc("Dashboard", name)
	else:
		doc = frappe.new_doc("Dashboard")
		doc.dashboard_name = name
	doc.module = MODULE
	doc.set("charts", [{"chart": c["name"]} for c in CHARTS])
	doc.set("cards", [{"card": c["name"]} for c in NUMBER_CARDS])
	doc.save(ignore_permissions=True)
