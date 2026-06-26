# Copyright (c) 2026, ramzi and contributors
# For license information, please see license.txt

import datetime

import frappe
from dateutil.relativedelta import relativedelta
from frappe import _
from frappe.utils import flt, getdate, today

BILLING_ITEMS_FIELD = "custom_billing_items"

# Number of months to advance between two consecutive invoices for each frequency.
FREQUENCY_MONTHS = {
	"Monthly": 1,
	"Quarterly": 3,
	"Semi-Annually": 6,
	"Yearly": 12,
}

INVOICES_FIELD = "custom_customer_invoices"
INVOICES_DOCTYPE = "Customer Invoices"

# Settings that define the schedule; a change to any of them rebuilds the table.
SETTING_FIELDS = (
	"custom_enabled_auto_invoice",
	"custom_invoicing_frequency",
	"custom_invoicing_start_date",
	"custom_invoicing_end_date",
	"custom_invoice_day",
)


def validate(doc, method=None):
	"""Customer.validate hook entry point.

	- New customer, or any scheduling setting changed -> (re)build the schedule.
	- Otherwise -> keep the table as-is and block manual row deletion.
	"""
	calculate_billing_items(doc)
	_dedupe_notify_users(doc)

	if doc.is_new():
		populate_customer_invoices(doc)
		return

	# Invoiced rows are always protected, even when the schedule is rebuilt.
	prevent_invoice_row_deletion(doc)

	if _settings_changed(doc):
		rebuild_customer_invoices(doc)
	else:
		populate_customer_invoices(doc)


def calculate_billing_items(doc):
	"""Keep each billing item's amount in sync as qty * rate."""
	for row in doc.get(BILLING_ITEMS_FIELD) or []:
		row.amount = flt(row.qty) * flt(row.rate)


def _dedupe_notify_users(doc):
	"""Reject duplicate users in the customer's notify-users table."""
	seen = set()
	for row in doc.get("custom_customer_notify_user") or []:
		if not row.user:
			continue
		if row.user in seen:
			frappe.throw(
				_("User {0} is listed more than once in Notify Users.").format(
					frappe.bold(row.user)
				)
			)
		seen.add(row.user)


# ---------------------------------------------------------------------------
# Scheduled invoice creation
# ---------------------------------------------------------------------------


def create_due_invoices():
	"""Scheduler entry point: create Sales Invoices for every due, un-invoiced row.

	Runs over all customers with auto invoicing enabled. Each customer is handled
	in its own transaction so one failure does not block the rest.
	"""
	today_date = getdate(today())
	customers = frappe.get_all(
		"Customer", filters={"custom_enabled_auto_invoice": 1}, pluck="name"
	)

	for customer_name in customers:
		try:
			create_due_invoices_for_customer(customer_name, today_date)
			frappe.db.commit()
		except Exception:
			frappe.db.rollback()
			frappe.log_error(
				title=f"Auto invoice creation failed for {customer_name}",
				message=frappe.get_traceback(),
			)


def create_due_invoices_for_customer(customer_name, today_date=None):
	"""Create Sales Invoices for all due, not-yet-invoiced rows of one customer."""
	today_date = getdate(today_date or today())
	customer = frappe.get_doc("Customer", customer_name)

	if not customer.get("custom_enabled_auto_invoice"):
		return
	if not customer.get(BILLING_ITEMS_FIELD):
		return

	due_rows = [
		row
		for row in customer.get(INVOICES_FIELD) or []
		if not row.invoiced and row.invoice_date and getdate(row.invoice_date) <= today_date
	]
	if not due_rows:
		return

	for row in due_rows:
		invoice = _make_sales_invoice(customer, row)
		row.invoice_name = invoice.name
		row.invoiced = 1

	customer.save(ignore_permissions=True)


def _make_sales_invoice(customer, invoice_row):
	"""Build, insert and submit a Sales Invoice from the customer's billing items."""
	return _build_sales_invoice(
		customer, getdate(invoice_row.invoice_date), submit=True, row_name=invoice_row.name
	)


def _build_sales_invoice(
	customer, invoice_date, submit=True, ignore_permissions=True, row_name=None
):
	"""Build and insert a Sales Invoice from the customer's billing items.

	When ``submit`` is False the invoice is left as a draft (used by the test
	button); otherwise it is submitted (used by the scheduler). ``row_name`` is
	stored on the invoice so it can be traced back to its schedule row on cancel.
	"""
	invoice_date = getdate(invoice_date)

	si = frappe.new_doc("Sales Invoice")
	si.customer = customer.name
	si.set_posting_time = 1
	si.posting_date = invoice_date
	si.custom_auto_invoice_row_name = row_name

	company = si.company or _default_company(customer)
	si.company = company

	# Cost center from the customer if set, otherwise the company default.
	cost_center = customer.get("custom_cost_center") or _default_cost_center(company)
	project = customer.get("custom_project")
	si.project = project

	context = {"customer": customer.name, "invoice_date": invoice_date}
	for item in customer.get(BILLING_ITEMS_FIELD) or []:
		si.append(
			"items",
			{
				"item_code": item.item_code,
				"qty": item.qty,
				"rate": item.rate,
				"item_tax_template": item.get("item_tax_template"),
				"cost_center": cost_center,
				"project": project,
				"description": render_billing_description(item.description, context),
			},
		)

	si.insert(ignore_permissions=ignore_permissions)
	if submit:
		si.submit()
	return si


def _default_company(customer):
	"""Resolve the company for the invoice."""
	return (
		frappe.defaults.get_user_default("Company")
		or frappe.db.get_single_value("Global Defaults", "default_company")
	)


def _default_cost_center(company):
	"""Company default cost center, used so valuation/P&L GL entries don't fail."""
	if not company:
		return None
	return frappe.get_cached_value("Company", company, "cost_center")


@frappe.whitelist()
def create_next_invoice(customer):
	"""Generate a draft Sales Invoice for the next scheduled row.

	Picks the soonest un-invoiced row, creates a draft Sales Invoice, and marks
	the row (``invoiced = 1`` + ``invoice_name``). Cancelling or deleting the
	invoice resets the row back to ``invoiced = 0``. Returns the new invoice name.
	"""
	customer_doc = frappe.get_doc("Customer", customer)

	if not customer_doc.get(BILLING_ITEMS_FIELD):
		frappe.throw(_("Add at least one Billing Item before generating an invoice."))

	row = _next_invoice_row(customer_doc)
	if not row:
		frappe.throw(_("There is no upcoming un-invoiced row to generate."))

	invoice = _build_sales_invoice(
		customer_doc,
		getdate(row.invoice_date),
		submit=False,
		ignore_permissions=False,
		row_name=row.name,
	)
	row.invoice_name = invoice.name
	row.invoiced = 1
	customer_doc.save(ignore_permissions=True)

	return invoice.name


def _next_invoice_row(customer):
	"""Return the soonest un-invoiced schedule row, or None."""
	candidates = sorted(
		(row for row in customer.get(INVOICES_FIELD) or [] if row.invoice_date and not row.invoiced),
		key=lambda r: getdate(r.invoice_date),
	)
	return candidates[0] if candidates else None


def on_sales_invoice_cancel(doc, method=None):
	"""Free the schedule row when its invoice is cancelled."""
	_release_invoice_rows(doc)


def on_sales_invoice_trash(doc, method=None):
	"""Free the schedule row when its (draft) invoice is deleted."""
	_release_invoice_rows(doc)


def _release_invoice_rows(doc):
	"""Reset any customer invoice row pointing at this invoice.

	Clears ``invoice_name`` and sets ``invoiced`` to 0 so the row can be
	re-invoiced. Used on both cancel and delete of the Sales Invoice.
	"""
	row_names = set(
		frappe.get_all(INVOICES_DOCTYPE, filters={"invoice_name": doc.name}, pluck="name")
	)
	if doc.get("custom_auto_invoice_row_name"):
		row_names.add(doc.custom_auto_invoice_row_name)

	for row_name in row_names:
		if frappe.db.exists(INVOICES_DOCTYPE, row_name):
			frappe.db.set_value(
				INVOICES_DOCTYPE, row_name, {"invoice_name": None, "invoiced": 0}
			)


def render_billing_description(template, context=None):
	"""Render a billing item description as a Jinja template.

	Used when an invoice is actually created so placeholders like ``{{ today }}``
	resolve to real values. Extra values can be passed via ``context``
	(e.g. the customer, the invoice row).
	"""
	if not template:
		return template

	render_context = {
		"today": getdate(today()),
		"frappe": frappe,
	}
	if context:
		render_context.update(context)

	return frappe.render_template(template, render_context)


def populate_customer_invoices(doc):
	"""Fill the upcoming invoices table once, only when it is still empty."""
	if doc.get(INVOICES_FIELD):
		return
	_append_schedule(doc, skip_dates=set())


def rebuild_customer_invoices(doc):
	"""Rebuild the schedule after a settings change.

	Already-invoiced rows are preserved (they represent real invoices and must
	never be lost); all other rows are regenerated from the current settings.
	"""
	# Keep the existing invoiced rows in place (same row names, invoice_name and
	# row links intact); only the not-yet-invoiced future rows are regenerated.
	invoiced_rows = [row for row in doc.get(INVOICES_FIELD) or [] if row.invoiced]
	kept_dates = {getdate(row.invoice_date) for row in invoiced_rows if row.invoice_date}

	doc.set(INVOICES_FIELD, invoiced_rows)
	_append_schedule(doc, skip_dates=kept_dates)


def _append_schedule(doc, skip_dates):
	"""Append generated upcoming invoice rows, skipping any date in `skip_dates`."""
	if not _schedule_is_complete(doc):
		return

	months = FREQUENCY_MONTHS[doc.get("custom_invoicing_frequency")]
	dates = generate_invoice_dates(
		getdate(doc.get("custom_invoicing_start_date")),
		getdate(doc.get("custom_invoicing_end_date")),
		int(doc.get("custom_invoice_day")),
		months,
	)
	for invoice_date in dates:
		if invoice_date in skip_dates:
			continue
		doc.append(INVOICES_FIELD, {"invoice_date": invoice_date, "invoiced": 0})


def _schedule_is_complete(doc):
	"""True only when auto invoicing is enabled and every setting is present/valid."""
	return bool(
		doc.get("custom_enabled_auto_invoice")
		and doc.get("custom_invoicing_frequency") in FREQUENCY_MONTHS
		and doc.get("custom_invoicing_start_date")
		and doc.get("custom_invoicing_end_date")
		and doc.get("custom_invoice_day")
	)


def generate_invoice_dates(start_date, end_date, invoice_day, months):
	"""Yield invoice dates on `invoice_day` of each period, upcoming only.

	The day is clamped to the last day of the month for short months (e.g. day 31
	in February). Dates before today are skipped so only upcoming invoices remain.
	"""
	today_date = getdate(today())

	# Anchor on the first day of the start month, then step period by period.
	anchor = datetime.date(start_date.year, start_date.month, 1)

	occurrence = 0
	while True:
		period_start = anchor + relativedelta(months=months * occurrence)
		occurrence += 1

		invoice_date = _clamp_day(period_start, invoice_day)

		if invoice_date > end_date:
			break
		if invoice_date < today_date:
			continue

		yield invoice_date

		# Safety valve against any unexpected non-advancing loop.
		if occurrence > 1000:
			break


def _clamp_day(period_start, day):
	"""Return `period_start` with day set to `day`, clamped to month length."""
	last_day = (period_start + relativedelta(day=31)).day
	return period_start.replace(day=min(day, last_day))


def prevent_invoice_row_deletion(doc):
	"""Disallow removing any invoiced row (server-side safeguard)."""
	before = _get_saved_doc(doc)
	if before is None:
		return

	new_names = {row.name for row in doc.get(INVOICES_FIELD) or [] if row.name}

	for row in before.get(INVOICES_FIELD) or []:
		if row.invoiced and row.name not in new_names:
			frappe.throw(
				_("You cannot delete an invoiced row ({0}).").format(
					row.invoice_name or row.invoice_date
				),
				title=_("Not Allowed"),
			)


def _settings_changed(doc):
	"""True if any scheduling setting differs from the saved version."""
	before = _get_saved_doc(doc)
	if before is None:
		return True
	return any(doc.get(field) != before.get(field) for field in SETTING_FIELDS)


def _get_saved_doc(doc):
	"""Return the database version of this document, or None for new docs."""
	if doc.is_new():
		return None
	before = doc.get_doc_before_save()
	if before is None:
		before = frappe.get_doc(doc.doctype, doc.name)
	return before
