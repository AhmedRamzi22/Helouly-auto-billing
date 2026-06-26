# Copyright (c) 2026, ramzi and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class AutoBillingSetting(Document):
	def validate(self):
		self._validate_day_before()
		self._dedupe_global_users()

	def _validate_day_before(self):
		if self.enable_notifications and (self.day_before_invoice or 0) < 0:
			frappe.throw(_("Day Before Invoice cannot be negative."))

	def _dedupe_global_users(self):
		seen = set()
		for row in self.global_users or []:
			if not row.user:
				continue
			if row.user in seen:
				frappe.throw(
					_("User {0} is listed more than once in Global Users.").format(
						frappe.bold(row.user)
					)
				)
			seen.add(row.user)
