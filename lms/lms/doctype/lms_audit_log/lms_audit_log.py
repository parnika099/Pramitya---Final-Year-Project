# Copyright (c) 2026, Unnati Development Institute and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.naming import make_autoname


class LMSAuditLog(Document):
	def autoname(self):
		self.name = make_autoname("AUD-.YYYY.-.#####")

	def validate(self):
		if not self.is_new():
			frappe.throw(_("Audit log entries cannot be changed."), frappe.ValidationError)
		if not self.actor:
			user = frappe.session.user
			self.actor = user if user and user != "Guest" else None

	def on_trash(self):
		if "System Manager" not in frappe.get_roles() and frappe.session.user != "Administrator":
			frappe.throw(_("Audit log entries cannot be deleted."), frappe.PermissionError)
