# Copyright (c) 2026, Pramitya and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class LMSAIVivaSession(Document):
	def validate(self):
		self.validate_member_matches_session_user_on_student_write()

	def before_insert(self):
		if frappe.session.user == "Guest":
			frappe.throw(_("Login required"))

	def validate_member_matches_session_user_on_student_write(self):
		user_roles = set(frappe.get_roles(frappe.session.user))
		previleged = {"System Manager", "Moderator", "Course Creator"}
		if not user_roles.intersection(previleged) and frappe.session.user != self.member:
			frappe.throw(_("You can only create AI Viva sessions for yourself"))
