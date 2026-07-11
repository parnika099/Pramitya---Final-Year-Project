# Copyright (c) 2026, Unnati Development Institute and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.naming import make_autoname
from frappe.utils import flt, nowdate

from lms.lms.academic import log_audit, require_fee_manager
from lms.lms.academic_rules import (
	AcademicRuleError,
	clean_label,
	money,
	remaining_amount,
	validate_payment_date,
	validate_payment_method,
)

LOCKED_FIELDS = ("amount", "payment_date", "payment_method", "transaction_id", "fee_account", "student")


class LMSFeeTransaction(Document):
	def autoname(self):
		self.name = make_autoname("PAY-.YYYY.-.#####")

	def validate(self):
		if not self.is_new():
			previous = self.get_doc_before_save()
			if previous and any(self.get(field) != previous.get(field) for field in LOCKED_FIELDS):
				frappe.throw(
					_("Payment history cannot be overwritten. Record a new payment instead."),
					frappe.ValidationError,
				)
			return
		if not frappe.flags.in_import:
			require_fee_manager()
		self.validate_payment()

	def validate_payment(self):
		if not self.fee_account or not frappe.db.exists("LMS Fee Account", self.fee_account):
			frappe.throw(_("Select a valid fee record."))
		account = frappe.db.get_value(
			"LMS Fee Account",
			self.fee_account,
			[
				"student",
				"student_id",
				"batch",
				"batch_code",
				"academic_year",
				"semester",
				"total_fees",
				"amount_paid",
			],
			as_dict=True,
		)
		try:
			amount = money(self.amount, allow_zero=False)
			method = validate_payment_method(self.payment_method)
			paid_on = validate_payment_date(self.payment_date, nowdate())
			reference = clean_label(self.transaction_id, "Transaction reference", max_length=140)
			note = clean_label(self.remarks, "Remarks", max_length=280)
			pending = remaining_amount(account.total_fees, account.amount_paid)
			if amount > pending:
				raise AcademicRuleError("Payment cannot be greater than the outstanding amount")
		except AcademicRuleError as exc:
			frappe.throw(str(exc), frappe.ValidationError)
		if reference and frappe.db.exists(
			"LMS Fee Transaction",
			{"fee_account": self.fee_account, "transaction_id": reference, "name": ["!=", self.name]},
		):
			frappe.throw(_("This transaction reference is already recorded for this fee record."))
		self.amount = flt(amount, 2)
		self.payment_method = method
		self.payment_date = paid_on
		self.transaction_id = reference
		self.remarks = note
		self.student = account.student
		self.student_id = account.student_id
		self.batch = account.batch
		self.batch_code = account.batch_code
		self.academic_year = account.academic_year
		self.semester = account.semester

	def after_insert(self):
		frappe.flags.fee_recalculate = True
		try:
			account = frappe.get_doc("LMS Fee Account", self.fee_account)
			account.recalculate_from_transactions()
			account.save(ignore_permissions=True)
		finally:
			frappe.flags.fee_recalculate = False
		log_audit(
			"Fee payment recorded",
			"LMS Fee Transaction",
			self.name,
			_("Payment of {0} recorded for {1}").format(self.amount, self.student_id),
			{
				"student_id": self.student_id,
				"batch_code": self.batch_code,
				"fee_account": self.fee_account,
				"amount": self.amount,
				"payment_method": self.payment_method,
				"transaction_id": self.transaction_id,
				"payment_date": str(self.payment_date),
			},
		)

	def on_trash(self):
		roles = frappe.get_roles()
		if frappe.session.user != "Administrator" and "System Manager" not in roles:
			frappe.throw(_("Payment history cannot be deleted."), frappe.PermissionError)
		self.flags.deleted_account = self.fee_account
		self.flags.deleted_snapshot = {
			"student_id": self.student_id,
			"amount": self.amount,
			"transaction_id": self.transaction_id,
			"fee_account": self.fee_account,
		}

	def after_delete(self):
		account_name = self.flags.get("deleted_account")
		if account_name and frappe.db.exists("LMS Fee Account", account_name):
			frappe.flags.fee_recalculate = True
			try:
				account = frappe.get_doc("LMS Fee Account", account_name)
				account.recalculate_from_transactions()
				account.save(ignore_permissions=True)
			finally:
				frappe.flags.fee_recalculate = False
		log_audit(
			"Fee payment removed",
			"LMS Fee Transaction",
			self.name,
			_("Payment {0} removed by Super Admin").format(self.name),
			self.flags.get("deleted_snapshot") or {},
		)
