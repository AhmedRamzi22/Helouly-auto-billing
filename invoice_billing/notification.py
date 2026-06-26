# Copyright (c) 2026, ramzi and contributors
# For license information, please see license.txt

"""Upcoming-invoice notification system.

Two layers are sent to the relevant users `day_before_invoice` days before an
invoice is due:

1. A short in-app notification (the bell), e.g. "3 customers will be invoiced in
   14 days", which links to the filtered Customer list.
2. A full email listing each customer, its invoice date and amount, with a button
   that routes to those customers.

Recipients are the union of each customer's own notify users
(``custom_customer_notify_user``) and the global users configured in
**Auto Billing Setting**. Every send is recorded in **Customer Auto Billing
Email Log**, which also de-duplicates so the same upcoming invoice is never
notified twice.
"""

import json
from collections import defaultdict
from urllib.parse import quote

import frappe
from frappe import _
from frappe.utils import add_days, flt, fmt_money, formatdate, get_url, getdate, today

SETTING_DOCTYPE = "Auto Billing Setting"
LOG_DOCTYPE = "Customer Auto Billing Email Log"
CUSTOMER_NOTIFY_FIELD = "custom_customer_notify_user"
BILLING_ITEMS_FIELD = "custom_billing_items"
INVOICES_DOCTYPE = "Customer Invoices"


def notify_upcoming_invoices():
	"""Scheduler entry point: notify users about invoices due soon."""
	setting = frappe.get_single(SETTING_DOCTYPE)
	if not setting.enable_notifications:
		return

	day_before = int(setting.day_before_invoice or 0)
	target_date = getdate(add_days(today(), day_before))

	due = _due_customers(target_date)
	# Drop customers already notified for this exact invoice date.
	due = [c for c in due if not _already_logged(c["customer"], c["invoice_date"])]
	if not due:
		return

	global_users = _setting_users(setting)

	# Build: user -> {customer_name: info} and customer -> set(notified users).
	user_customers = defaultdict(dict)
	customer_users = defaultdict(set)

	for info in due:
		recipients = set(global_users) | set(info["notify_users"])
		recipients = {u for u in recipients if u}
		for user in recipients:
			user_customers[user][info["customer"]] = info
			customer_users[info["customer"]].add(user)

	for user, customers in user_customers.items():
		try:
			_notify_user(user, list(customers.values()), day_before)
		except Exception:
			frappe.log_error(
				title=f"Upcoming invoice notification failed for {user}",
				message=frappe.get_traceback(),
			)

	# Record one log per customer so we never notify the same invoice twice.
	for info in due:
		_create_log(info, sorted(customer_users[info["customer"]]))

	frappe.db.commit()


def _due_customers(target_date):
	"""Return enabled customers with an un-invoiced row on ``target_date``."""
	rows = frappe.get_all(
		INVOICES_DOCTYPE,
		filters={
			"parenttype": "Customer",
			"invoice_date": target_date,
			"invoiced": 0,
		},
		fields=["parent as customer", "invoice_date"],
	)

	due = []
	for row in rows:
		customer = frappe.get_cached_doc("Customer", row.customer)
		if not customer.get("custom_enabled_auto_invoice"):
			continue
		due.append(
			{
				"customer": customer.name,
				"customer_label": customer.customer_name or customer.name,
				"invoice_date": getdate(row.invoice_date),
				"amount": _customer_amount(customer),
				"currency": customer.get("default_currency"),
				"notify_users": _customer_notify_users(customer),
			}
		)
	return due


def _customer_amount(customer):
	"""Total of the customer's billing items (qty * rate)."""
	return sum(flt(item.qty) * flt(item.rate) for item in customer.get(BILLING_ITEMS_FIELD) or [])


def _customer_notify_users(customer):
	"""User list from the customer's own notify-users table."""
	return [row.user for row in customer.get(CUSTOMER_NOTIFY_FIELD) or [] if row.user]


def _setting_users(setting):
	"""Global user list from the Auto Billing Setting."""
	return [row.user for row in setting.global_users or [] if row.user]


def _already_logged(customer, invoice_date):
	"""True if this customer/invoice_date was already notified."""
	return bool(
		frappe.db.exists(
			LOG_DOCTYPE, {"customer": customer, "invoice_date": getdate(invoice_date)}
		)
	)


def _create_log(info, users):
	"""Persist a Customer Auto Billing Email Log row for audit + de-dup."""
	log = frappe.get_doc(
		{
			"doctype": LOG_DOCTYPE,
			"posting_date": today(),
			"customer": info["customer"],
			"invoice_date": info["invoice_date"],
			"users": [{"user": u} for u in users],
		}
	)
	log.insert(ignore_permissions=True)


# ---------------------------------------------------------------------------
# Delivery
# ---------------------------------------------------------------------------


def _notify_user(user, customers, day_before, now=False):
	"""Send the in-app notification and the detailed email to one user."""
	count = len(customers)
	customer_names = [c["customer"] for c in customers]
	route = _customer_list_route(customer_names)

	subject = _(
		"{0} customer(s) will be invoiced in {1} day(s)"
	).format(count, day_before)

	details_html = _build_email_html(customers, day_before, route)

	email = frappe.db.get_value("User", user, "email") or user
	email_sent = bool(email)
	if email_sent:
		frappe.sendmail(
			recipients=[email],
			subject=_get_email_subject(),
			message=details_html,
			reference_doctype=LOG_DOCTYPE,
			now=now,
		)

	_create_notification_log(user, subject, route, details_html, email, email_sent)


@frappe.whitelist()
def send_test_notification():
	"""Send a notification + email to the current user, for testing.

	Uses the real customers due in ``day_before_invoice`` days if any exist,
	otherwise a sample row built from an existing customer. Also writes the
	Customer Auto Billing Email Log (full production flow); the dedup guard keeps
	repeated tests from creating duplicate logs.
	"""
	setting = frappe.get_single(SETTING_DOCTYPE)
	day_before = int(setting.day_before_invoice or 0)
	target_date = getdate(add_days(today(), day_before))

	customers = _due_customers(target_date)
	if not customers:
		customers = [_sample_customer(target_date)]

	user = frappe.session.user
	_notify_user(user, customers, day_before, now=True)

	logged = 0
	for info in customers:
		if not frappe.db.exists("Customer", info["customer"]):
			continue
		if _already_logged(info["customer"], info["invoice_date"]):
			continue
		_create_log(info, [user])
		logged += 1

	return {"count": len(customers), "user": user, "logged": logged}


def _sample_customer(target_date):
	"""Build a sample customer dict from a real customer (for log validity)."""
	name = frappe.db.get_value("Customer", {"custom_enabled_auto_invoice": 1}) or frappe.db.get_value(
		"Customer", {}
	)
	label = frappe.db.get_value("Customer", name, "customer_name") if name else None
	return {
		"customer": name or "SAMPLE",
		"customer_label": label or _("Sample Customer"),
		"invoice_date": target_date,
		"amount": 1000.0,
		"currency": None,
		"notify_users": [],
	}


def _create_notification_log(user, subject, route, details_html, email, email_sent):
	"""Create the bell notification for a user, linking to the filtered list.

	The body confirms the detailed email was sent and embeds the same breakdown
	so it can be read straight from the bell.
	"""
	if email_sent:
		note = _("📧 A detailed email has been sent to {0}.").format(email)
	else:
		note = _("⚠️ No email address found, so only this notification was sent.")

	frappe.get_doc(
		{
			"doctype": "Notification Log",
			"for_user": user,
			"type": "Alert",
			"subject": subject,
			"email_content": f"<p>{note}</p>{details_html}",
			"link": route,
		}
	).insert(ignore_permissions=True)


def _get_email_subject():
	subject = frappe.db.get_single_value(SETTING_DOCTYPE, "email_subject")
	return subject or _("Upcoming Customer Invoices")


def _customer_list_route(customer_names):
	"""Desk route to the Customer list filtered to the given names."""
	flt_value = json.dumps(["in", customer_names])
	return "/app/customer?name=" + quote(flt_value)


def _build_email_html(customers, day_before, route):
	"""Build the detailed HTML email body with a routing button."""
	rows = []
	for c in customers:
		customer_url = get_url("/app/customer/" + quote(c["customer"]))
		row_button = (
			f"<a href='{customer_url}' "
			"style='display:inline-block;padding:4px 10px;background:#2490ef;color:#fff;"
			"text-decoration:none;border-radius:4px;font-size:12px;'>Open</a>"
		)
		rows.append(
			"<tr>"
			f"<td style='padding:6px 12px;border:1px solid #d1d8dd;'>{frappe.utils.escape_html(c['customer_label'])}</td>"
			f"<td style='padding:6px 12px;border:1px solid #d1d8dd;'>{formatdate(c['invoice_date'])}</td>"
			f"<td style='padding:6px 12px;border:1px solid #d1d8dd;text-align:right;'>{fmt_money(c['amount'], currency=c.get('currency'))}</td>"
			f"<td style='padding:6px 12px;border:1px solid #d1d8dd;text-align:center;'>{row_button}</td>"
			"</tr>"
		)

	table = (
		"<table style='border-collapse:collapse;margin:12px 0;'>"
		"<thead><tr>"
		"<th style='padding:6px 12px;border:1px solid #d1d8dd;text-align:left;'>Customer</th>"
		"<th style='padding:6px 12px;border:1px solid #d1d8dd;text-align:left;'>Invoice Date</th>"
		"<th style='padding:6px 12px;border:1px solid #d1d8dd;text-align:right;'>Amount</th>"
		"<th style='padding:6px 12px;border:1px solid #d1d8dd;text-align:center;'>Action</th>"
		"</tr></thead>"
		f"<tbody>{''.join(rows)}</tbody>"
		"</table>"
	)

	button = (
		f"<a href='{get_url(route)}' "
		"style='display:inline-block;padding:8px 16px;background:#2490ef;color:#fff;"
		"text-decoration:none;border-radius:6px;'>View Customers</a>"
	)

	intro = _(
		"The following {0} customer(s) will be invoiced in {1} day(s):"
	).format(len(customers), day_before)

	return f"<div><p>{intro}</p>{table}<p>{button}</p></div>"
