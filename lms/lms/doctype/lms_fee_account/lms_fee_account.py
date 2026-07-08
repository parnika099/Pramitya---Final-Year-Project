# Copyright (c) 2026, Unnati Development Institute and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.naming import make_autoname
from frappe.utils import flt, nowdate

from lms.lms.academic import log_audit, require_fee_manager
from lms.lms.academic_rules import AcademicRuleError, fee_status, remaining_amount, stored_money, validate_semester


class LMSFeeAccount(Document):
	def autoname(self):
		self.name = make_autoname("FEE-.YYYY.-.#####")

	def before_validate(self):
		if not self.currency and frappe.db.exists("Currency", "INR"):
			self.currency = "INR"
		if self.student:
			self.validate_identity()

	def validate(self):
		if not frappe.flags.in_migrate and not frappe.flags.in_import:
			require_fee_manager()
		self.validate_identity()
		if not self.student_id:
			frappe.throw(_("This student does not have a Student ID yet."))
		self.validate_amounts()
		self.validate_duplicate()

	def validate_identity(self):
		from lms.lms.academic import batch_snapshot, student_snapshot

		if not self.is_new():
			previous = self.get_doc_before_save()
			if previous and previous.student and previous.student != self.student:
				frappe.throw(_("The student on a fee record cannot be changed."))
			if previous and previous.batch and previous.batch != self.batch:
				frappe.throw(_("The batch on a fee record cannot be changed."))
		student = student_snapshot(self.student)
		batch = batch_snapshot(self.batch)
		self.batch = batch.get("name") or self.batch
		self.student_id = student.student_id
		self.student_name = student.full_name
		self.batch_code = batch.get("batch_code")
		if not self.academic_year:
			self.academic_year = batch.get("academic_year")
		if not self.department:
			self.department = batch.get("department")
		if not self.semester:
			self.semester = batch.get("semester")
		try:
			self.semester = validate_semester(self.semester, required=True)
			if not self.academic_year:
				raise AcademicRuleError("Academic year is required")
		except AcademicRuleError as exc:
			frappe.throw(str(exc), frappe.ValidationError)
		if not self.due_date:
			frappe.throw(_("Due date is required."))
		if not self.currency:
			self.currency = "INR" if frappe.db.exists("Currency", "INR") else None
		if not self.currency:
			frappe.throw(_("Currency is required."))

	def validate_amounts(self):
		try:
			total = stored_money(self.total_fees)
			paid = stored_money(self.amount_paid or 0)
			pending = remaining_amount(total, paid)
		except AcademicRuleError as exc:
			frappe.throw(str(exc), frappe.ValidationError)
		self.total_fees = flt(total, 2)
		self.amount_paid = flt(paid, 2)
		self.pending_amount = flt(pending, 2)
		self.status = fee_status(total, paid, self.due_date, nowdate())

	def validate_duplicate(self):
		filters = {
			"student": self.student,
			"batch": self.batch,
			"academic_year": self.academic_year,
			"semester": self.semester,
			"name": ["!=", self.name],
		}
		if frappe.db.exists("LMS Fee Account", filters):
			frappe.throw(
				_("A fee record already exists for this student, batch, academic year, and semester.")
			)

	def recalculate_from_transactions(self):
		total_paid = frappe.db.sql(
			"""
			SELECT IFNULL(SUM(amount), 0)
			FROM `tabLMS Fee Transaction`
			WHERE fee_account = %s
			""",
			self.name,
		)[0][0]
		self.amount_paid = total_paid or 0
		self.validate_amounts()

	def on_update(self):
		if frappe.flags.get("fee_recalculate") or frappe.flags.get("skip_academic_audit"):
			return
		previous = self.get_doc_before_save()
		if not previous:
			log_audit(
				"Fee record created",
				"LMS Fee Account",
				self.name,
				_("Fee record {0} created for {1}").format(self.name, self.student_id),
				{
					"student_id": self.student_id,
					"batch_code": self.batch_code,
					"total_fees": self.total_fees,
					"due_date": str(self.due_date),
					"status": self.status,
				},
			)
			return
		watched = ("total_fees", "due_date", "academic_year", "semester", "department", "status")
		changed = {
			field: {"from": previous.get(field), "to": self.get(field)}
			for field in watched
			if str(previous.get(field)) != str(self.get(field))
		}
		if changed:
			changed["student_id"] = self.student_id
			log_audit(
				"Fee record updated",
				"LMS Fee Account",
				self.name,
				_("Fee record {0} updated").format(self.name),
				changed,
			)

	def on_trash(self):
		if frappe.db.exists("LMS Fee Transaction", {"fee_account": self.name}):
			frappe.throw(_("This fee record has payment history and cannot be deleted."))
		log_audit(
			"Fee record removed",
			"LMS Fee Account",
			self.name,
			_("Fee record {0} removed").format(self.name),
			{"student_id": self.student_id, "batch_code": self.batch_code},
		)
