# Copyright (c) 2026, Unnati Development Institute and contributors
# For license information, please see license.txt

"""Student ID, batch identity, academic fees, access checks, and reports.

Course checkout continues to use LMS Payment. This module is the academic ledger.
"""

from __future__ import annotations

import csv
import io
import json

import frappe
from frappe import _
from frappe.model.naming import make_autoname
from frappe.utils import cint, now_datetime, nowdate

from lms.lms.academic_rules import (
	AcademicRuleError,
	FEE_STATUSES,
	PAYMENT_METHODS,
	REPORTS,
	SEMESTERS,
	access_level,
	can_access_report,
	can_change_role,
	can_manage_fees,
	can_view_student,
	clean_label,
	csv_cell,
	fee_status,
	money,
	remaining_amount,
	series_year,
	validate_payment_date,
	validate_payment_method,
	validate_semester,
)

USER_FIELDS = {
	"User": [
		{
			"fieldname": "student_id",
			"label": "Student ID",
			"fieldtype": "Data",
			"insert_after": "username",
			"unique": 1,
			"read_only": 1,
			"no_copy": 1,
			"in_standard_filter": 1,
			"translatable": 0,
			"module": "LMS",
			"description": "Permanent student identifier. Assigned once and never changed.",
		},
		{
			"fieldname": "active_batch",
			"label": "Active Batch",
			"fieldtype": "Link",
			"options": "LMS Batch",
			"insert_after": "student_id",
			"read_only": 1,
			"in_standard_filter": 1,
			"module": "LMS",
			"description": "The student's current academic batch.",
		},
	]
}

SORT_ORDERS = {"asc", "desc"}
STUDENT_SORTS = {
	"student_id": "u.student_id",
	"full_name": "u.full_name",
	"batch_code": "b.batch_code",
	"academic_year": "b.academic_year",
	"department": "b.department",
}
BATCH_SORTS = {
	"batch_code": "batch_code",
	"title": "title",
	"academic_year": "academic_year",
	"department": "department",
	"active_students": "active_students",
}
FEE_SORTS = {
	"student_id": "student_id",
	"batch_code": "batch_code",
	"due_date": "due_date",
	"status": "status",
	"pending_amount": "pending_amount",
	"total_fees": "total_fees",
}


def ensure_academic_setup():
	"""Create identity fields and fill missing IDs. Safe to run more than once."""
	from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

	create_custom_fields(USER_FIELDS, update=True)
	frappe.flags.skip_academic_audit = True
	try:
		backfill_student_ids()
		backfill_batch_codes()
		normalize_active_batches()
	finally:
		frappe.flags.skip_academic_audit = False


def schema_ready() -> bool:
	return bool(
		frappe.get_meta("User").has_field("student_id")
		and frappe.get_meta("LMS Batch").has_field("batch_code")
		and frappe.db.exists("DocType", "LMS Fee Account")
	)


def require_schema():
	if not schema_ready():
		frappe.throw(
			_("Academic records are not ready yet. Run bench migrate, then try again."),
			frappe.ValidationError,
		)


def allocate_student_id() -> str:
	return make_autoname(f"UNN-{now_datetime().year}-.#####")


def allocate_batch_code(academic_year=None, start_date=None) -> str:
	year = series_year(academic_year, start_date, nowdate())
	return make_autoname(f"BTH-{year}-.####")


def assign_student_id_if_missing(user: str):
	if not user or user in {"Guest", "Administrator"}:
		return
	if not frappe.get_meta("User").has_field("student_id"):
		return
	if frappe.db.get_value("User", user, "student_id"):
		return
	if not frappe.db.exists("Has Role", {"parent": user, "parenttype": "User", "role": "LMS Student"}):
		return
	student_id = allocate_student_id()
	frappe.db.set_value("User", user, "student_id", student_id, update_modified=False)
	log_audit(
		"Student ID assigned",
		"User",
		user,
		_("Student ID {0} assigned").format(student_id),
		{"student_id": student_id},
	)


def backfill_student_ids():
	if not frappe.get_meta("User").has_field("student_id"):
		return
	users = frappe.get_all(
		"Has Role",
		filters={"role": "LMS Student", "parenttype": "User"},
		pluck="parent",
	)
	for user in users:
		assign_student_id_if_missing(user)


def backfill_batch_codes():
	if not frappe.get_meta("LMS Batch").has_field("batch_code"):
		return
	rows = frappe.db.sql(
		"""
		SELECT name, academic_year, start_date
		FROM `tabLMS Batch`
		WHERE IFNULL(batch_code, '') = ''
		""",
		as_dict=True,
	)
	for row in rows:
		if not row.academic_year and row.start_date:
			year = series_year(None, row.start_date, nowdate())
			frappe.db.set_value("LMS Batch", row.name, "academic_year", year, update_modified=False)
			row.academic_year = year
		frappe.db.set_value(
			"LMS Batch",
			row.name,
			"batch_code",
			allocate_batch_code(row.academic_year, row.start_date),
			update_modified=False,
		)


def normalize_active_batches():
	if not frappe.get_meta("LMS Batch Enrollment").has_field("active"):
		return
	rows = frappe.db.sql(
		"""
		SELECT member, SUM(IFNULL(active, 0)) AS active_count
		FROM `tabLMS Batch Enrollment`
		GROUP BY member
		""",
		as_dict=True,
	)
	has_active_batch = frappe.get_meta("User").has_field("active_batch")
	for row in rows:
		if cint(row.active_count) == 1:
			batch = frappe.db.get_value(
				"LMS Batch Enrollment", {"member": row.member, "active": 1}, "batch"
			)
		else:
			latest = frappe.db.sql(
				"""
				SELECT name, batch
				FROM `tabLMS Batch Enrollment`
				WHERE member = %s
				ORDER BY creation DESC
				LIMIT 1
				""",
				row.member,
				as_dict=True,
			)
			if not latest:
				continue
			frappe.db.sql(
				"UPDATE `tabLMS Batch Enrollment` SET active = 0 WHERE member = %s",
				row.member,
			)
			frappe.db.set_value(
				"LMS Batch Enrollment", latest[0].name, "active", 1, update_modified=False
			)
			batch = latest[0].batch
		if has_active_batch:
			frappe.db.set_value("User", row.member, "active_batch", batch, update_modified=False)


def log_audit(action: str, document_type: str, document_name: str, subject: str, details: dict | None = None):
	if frappe.flags.get("skip_academic_audit") or frappe.flags.in_migrate or frappe.flags.in_install:
		return
	if not frappe.db.exists("DocType", "LMS Audit Log"):
		return
	try:
		entry = frappe.get_doc(
			{
				"doctype": "LMS Audit Log",
				"action": (action or "")[:140],
				"actor": frappe.session.user if frappe.session.user != "Guest" else None,
				"document_type": document_type,
				"document_name": document_name,
				"subject": (subject or "")[:140],
				"details": json.dumps(details or {}, default=str)[:4000],
			}
		)
		entry.insert(ignore_permissions=True)
	except Exception:
		frappe.log_error(title="LMS audit log failed")


def roles_of(user: str | None = None) -> list[str]:
	user = user or frappe.session.user
	if not user or user == "Guest":
		return []
	return frappe.get_roles(user)


def current_level() -> str:
	return access_level(roles_of())


def require_fee_manager():
	if frappe.session.user == "Administrator":
		return
	if not can_manage_fees(roles_of()):
		frappe.throw(_("You are not allowed to change fee records."), frappe.PermissionError)


def require_role_manager():
	if not can_change_role(roles_of(), [], "LMS Student") and "System Manager" not in roles_of():
		if access_level(roles_of()) not in {"super_admin", "admin"}:
			frappe.throw(_("You are not allowed to change roles."), frappe.PermissionError)


def assert_role_change(target: str, role: str):
	target_roles = frappe.get_roles(target)
	if not can_change_role(roles_of(), target_roles, role):
		frappe.throw(
			_("You are not allowed to change this user's roles."),
			frappe.PermissionError,
		)


def faculty_batches(user: str | None = None) -> list[str]:
	user = user or frappe.session.user
	return frappe.get_all(
		"Course Instructor",
		filters={"parenttype": "LMS Batch", "instructor": user},
		pluck="parent",
	)


def faculty_students(user: str | None = None) -> list[str]:
	batches = faculty_batches(user)
	if not batches:
		return []
	return list(
		dict.fromkeys(
			frappe.get_all(
				"LMS Batch Enrollment",
				filters={"batch": ["in", batches]},
				pluck="member",
			)
		)
	)


def visible_students(user: str | None = None):
	"""None means every student. A list is the only students this user may see."""
	user = user or frappe.session.user
	level = access_level(roles_of(user))
	if level in {"super_admin", "admin"}:
		return None
	if level == "faculty":
		return faculty_students(user)
	if level == "student":
		return [user]
	return []


def visible_batches(user: str | None = None):
	user = user or frappe.session.user
	level = access_level(roles_of(user))
	if level in {"super_admin", "admin"}:
		return None
	if level == "faculty":
		return faculty_batches(user)
	return []


def viewer_can_see_student(student: str, user: str | None = None) -> bool:
	user = user or frappe.session.user
	scope = visible_students(user)
	faculty_scope = scope if access_level(roles_of(user)) == "faculty" else None
	if access_level(roles_of(user)) == "faculty":
		faculty_scope = scope
	return can_view_student(roles_of(user), user, student, faculty_scope if faculty_scope is not None else scope)


def raise_rule(exc: AcademicRuleError):
	frappe.throw(str(exc), frappe.ValidationError)


def apply_money(value, allow_zero: bool = True):
	try:
		return money(value, allow_zero=allow_zero)
	except AcademicRuleError as exc:
		raise_rule(exc)


def format_stored(value) -> str:
	from lms.lms.academic_rules import stored_money

	try:
		return f"{stored_money(value):.2f}"
	except AcademicRuleError:
		return "0.00"


def present_fee(row: dict) -> dict:
	from lms.lms.academic_rules import stored_money

	try:
		pending = remaining_amount(row.get("total_fees") or 0, row.get("amount_paid") or 0)
		status = fee_status(row.get("total_fees") or 0, row.get("amount_paid") or 0, row.get("due_date"), nowdate())
		total_text = f"{stored_money(row.get('total_fees') or 0):.2f}"
		paid_text = f"{stored_money(row.get('amount_paid') or 0):.2f}"
		pending_text = f"{pending:.2f}"
	except AcademicRuleError:
		status = row.get("status") or "Pending"
		total_text = "0.00"
		paid_text = "0.00"
		pending_text = "0.00"
	presented = dict(row)
	presented["total_fees"] = total_text
	presented["amount_paid"] = paid_text
	presented["pending_amount"] = pending_text
	presented["status"] = status
	for key in ("due_date", "payment_date", "creation", "modified"):
		if presented.get(key) is not None:
			presented[key] = str(presented[key])
	return presented


def parse_filters(filters) -> dict:
	if not filters:
		return {}
	if isinstance(filters, str):
		try:
			filters = json.loads(filters)
		except json.JSONDecodeError:
			frappe.throw(_("Filters are not valid."), frappe.ValidationError)
	if not isinstance(filters, dict):
		frappe.throw(_("Filters are not valid."), frappe.ValidationError)
	return filters


def page_window(page, page_size) -> tuple[int, int, int]:
	page = max(cint(page) or 1, 1)
	page_size = min(max(cint(page_size) or 20, 1), 100)
	return page, page_size, (page - 1) * page_size


def like_term(value: str) -> str:
	cleaned = str(value or "").replace("\\", "").replace("%", "").replace("_", "").strip()[:80]
	return f"%{cleaned}%"


def resolve_batch(batch: str) -> str:
	batch = clean_text(batch, "Batch", required=True)
	if frappe.db.exists("LMS Batch", batch):
		return batch
	if frappe.get_meta("LMS Batch").has_field("batch_code"):
		found = frappe.db.get_value("LMS Batch", {"batch_code": batch}, "name")
		if found:
			return found
	frappe.throw(_("Select a valid batch."), frappe.ValidationError)


def batch_snapshot(batch: str) -> dict:
	batch = resolve_batch(batch)
	fields = ["name", "title"]
	meta = frappe.get_meta("LMS Batch")
	for field in ("batch_code", "academic_year", "department", "semester"):
		if meta.has_field(field):
			fields.append(field)
	return frappe.db.get_value("LMS Batch", batch, fields, as_dict=True) or {}


def student_snapshot(student: str) -> dict:
	if not student or not frappe.db.exists("User", student):
		frappe.throw(_("Select a valid student."), frappe.ValidationError)
	if not frappe.db.exists("Has Role", {"parent": student, "parenttype": "User", "role": "LMS Student"}):
		frappe.throw(_("Fee records can only be created for students."), frappe.ValidationError)
	fields = ["name", "full_name", "username"]
	if frappe.get_meta("User").has_field("student_id"):
		fields.append("student_id")
	row = frappe.db.get_value("User", student, fields, as_dict=True) or {}
	if not row.get("student_id"):
		assign_student_id_if_missing(student)
		row["student_id"] = frappe.db.get_value("User", student, "student_id")
	if not row.get("student_id"):
		frappe.throw(_("This student does not have a Student ID yet."), frappe.ValidationError)
	return row


def resolve_student(student: str = "", student_id: str = "") -> str:
	student_id = clean_text(student_id, "Student ID")
	student = clean_text(student, "Student")
	if student_id:
		found = frappe.db.get_value("User", {"student_id": student_id}, "name")
		if not found:
			frappe.throw(_("No student was found for that Student ID."), frappe.ValidationError)
		if student and student != found:
			frappe.throw(_("Student ID does not match the selected student."), frappe.ValidationError)
		return found
	if not student:
		frappe.throw(_("Student ID is required."), frappe.ValidationError)
	return student


def clean_text(value, field: str, required: bool = False, max_length: int = 140) -> str:
	try:
		return clean_label(value, field, required=required, max_length=max_length)
	except AcademicRuleError as exc:
		raise_rule(exc)


def academic_profile(student: str) -> dict:
	if not frappe.get_meta("User").has_field("student_id"):
		return {}
	if not viewer_can_see_student(student):
		return {}
	fields = ["name", "full_name", "student_id", "active_batch"]
	row = frappe.db.get_value("User", student, fields, as_dict=True)
	if not row or not row.student_id:
		return {}
	profile = {
		"student_id": row.student_id,
		"batch": row.active_batch,
		"batch_code": None,
		"batch_title": None,
		"academic_year": None,
		"department": None,
		"semester": None,
	}
	if row.active_batch and frappe.db.exists("LMS Batch", row.active_batch):
		batch = batch_snapshot(row.active_batch)
		profile.update(
			{
				"batch_code": batch.get("batch_code"),
				"batch_title": batch.get("title"),
				"academic_year": batch.get("academic_year"),
				"department": batch.get("department"),
				"semester": batch.get("semester"),
			}
		)
	if frappe.db.exists("DocType", "LMS Fee Account") and (
		frappe.session.user == student or can_manage_fees(roles_of()) or current_level() == "faculty"
	):
		accounts = frappe.get_all(
			"LMS Fee Account",
			filters={"student": student},
			fields=["total_fees", "amount_paid", "pending_amount", "status", "due_date", "name"],
			order_by="due_date asc",
			limit=20,
		)
		presented = [present_fee(account) for account in accounts]
		outstanding = sum(money(account["pending_amount"]) for account in presented)
		profile["fee_status"] = _combined_fee_status(presented)
		profile["pending_amount"] = f"{outstanding:.2f}"
		if frappe.session.user == student or can_manage_fees(roles_of()):
			profile["fee_accounts"] = len(presented)
	return profile


def _combined_fee_status(accounts: list[dict]) -> str:
	if not accounts:
		return "Pending"
	statuses = {account["status"] for account in accounts}
	if statuses == {"Paid"}:
		return "Paid"
	if "Overdue" in statuses:
		return "Overdue"
	if "Partially Paid" in statuses or ("Paid" in statuses and "Pending" in statuses):
		return "Partially Paid"
	return "Pending"


def audit_batch_change(batch):
	previous = batch.get_doc_before_save()
	watched = ("batch_code", "academic_year", "department", "semester", "title")
	if not previous:
		log_audit(
			"Batch created",
			"LMS Batch",
			batch.name,
			_("Batch {0} created").format(batch.get("batch_code") or batch.title),
			{field: batch.get(field) for field in watched},
		)
		return
	changed = {
		field: {"from": previous.get(field), "to": batch.get(field)}
		for field in watched
		if previous.get(field) != batch.get(field)
	}
	if changed:
		log_audit(
			"Batch updated",
			"LMS Batch",
			batch.name,
			_("Batch {0} updated").format(batch.get("batch_code") or batch.name),
			changed,
		)


def refresh_overdue_fee_status():
	if not frappe.db.exists("DocType", "LMS Fee Account"):
		return
	frappe.db.sql(
		"""
		UPDATE `tabLMS Fee Account`
		SET status = 'Overdue'
		WHERE status IN ('Pending', 'Partially Paid')
		AND due_date IS NOT NULL
		AND due_date < %s
		AND IFNULL(pending_amount, 0) > 0
		""",
		nowdate(),
	)


def has_fee_permission(doc, ptype="read", user=None):
	user = user or frappe.session.user
	if not doc or not getattr(doc, "student", None):
		return None
	roles = roles_of(user)
	if user == "Administrator" or access_level(roles) in {"super_admin", "admin"}:
		return True
	if ptype != "read":
		return False
	return viewer_can_see_student(doc.student, user)


def fee_permission_query(user=None):
	user = user or frappe.session.user
	if user == "Administrator" or access_level(roles_of(user)) in {"super_admin", "admin"}:
		return ""
	scope = visible_students(user)
	if not scope:
		return "1=0"
	escaped = ", ".join(frappe.db.escape(name) for name in scope)
	return f"`tabLMS Fee Account`.student in ({escaped})"


def fee_transaction_permission_query(user=None):
	condition = fee_permission_query(user)
	if not condition:
		return ""
	if condition == "1=0":
		return "1=0"
	return condition.replace("`tabLMS Fee Account`.student", "`tabLMS Fee Transaction`.student")


def has_audit_permission(doc=None, ptype="read", user=None):
	user = user or frappe.session.user
	if ptype != "read":
		return user == "Administrator" or "System Manager" in roles_of(user)
	return access_level(roles_of(user)) in {"super_admin", "admin"}


def audit_permission_query(user=None):
	user = user or frappe.session.user
	if access_level(roles_of(user)) in {"super_admin", "admin"}:
		return ""
	return "1=0"


@frappe.whitelist()
def get_my_academic_card() -> dict:
	if frappe.session.user == "Guest":
		frappe.throw(_("Please log in."), frappe.PermissionError)
	if not frappe.get_meta("User").has_field("student_id"):
		return {}
	assign_student_id_if_missing(frappe.session.user)
	return academic_profile(frappe.session.user)


@frappe.whitelist()
def search_students(
	query: str = "",
	batch: str = "",
	page: int = 1,
	page_size: int = 20,
) -> dict:
	require_schema()
	if current_level() not in {"super_admin", "admin", "faculty"}:
		frappe.throw(_("You are not allowed to search students."), frappe.PermissionError)
	return _student_report(
		{"query": query, "batch_id": batch},
		*page_window(page, page_size)[:2],
		"full_name",
		"asc",
	)


@frappe.whitelist()
def get_fee_account(name: str) -> dict:
	require_schema()
	if not frappe.db.exists("LMS Fee Account", name):
		frappe.throw(_("Fee record not found."), frappe.DoesNotExistError)
	account = frappe.db.get_value(
		"LMS Fee Account",
		name,
		[
			"name",
			"student",
			"student_id",
			"student_name",
			"batch",
			"batch_code",
			"academic_year",
			"semester",
			"department",
			"total_fees",
			"amount_paid",
			"pending_amount",
			"status",
			"due_date",
			"currency",
		],
		as_dict=True,
	)
	if not viewer_can_see_student(account.student):
		frappe.throw(_("You are not allowed to view this fee record."), frappe.PermissionError)
	transactions = frappe.get_all(
		"LMS Fee Transaction",
		filters={"fee_account": name},
		fields=[
			"name",
			"amount",
			"payment_date",
			"payment_method",
			"transaction_id",
			"remarks",
			"creation",
		],
		order_by="payment_date asc, creation asc",
		limit=200,
	)
	presented = present_fee(account)
	presented.pop("student", None)
	presented["transactions"] = [_present_transaction(row) for row in transactions]
	return presented


def _present_transaction(row) -> dict:
	presented = dict(row)
	presented["amount"] = format_stored(row.amount)
	presented["payment_date"] = str(row.payment_date) if row.payment_date else None
	presented["creation"] = str(row.creation) if row.creation else None
	return presented


@frappe.whitelist()
def list_fee_accounts(
	query: str = "",
	batch: str = "",
	status: str = "",
	academic_year: str = "",
	semester: str = "",
	page: int = 1,
	page_size: int = 20,
) -> dict:
	require_schema()
	if current_level() == "none":
		frappe.throw(_("You are not allowed to view fee records."), frappe.PermissionError)
	filters = {
		"student_id": query,
		"batch_id": batch,
		"payment_status": status,
		"academic_year": academic_year,
		"semester": semester,
	}
	if current_level() == "student":
		filters = {"student_user": frappe.session.user}
	page, page_size = page_window(page, page_size)[:2]
	return _fee_report(filters, page, page_size, "due_date", "asc")


@frappe.whitelist()
def create_fee_account(
	student: str = "",
	student_id: str = "",
	batch: str = "",
	academic_year: str = "",
	semester: str = "",
	total_fees: str = "",
	due_date: str = "",
	department: str = "",
) -> dict:
	require_schema()
	require_fee_manager()
	from lms.lms.academic_rules import as_date

	try:
		total = apply_money(total_fees)
		semester = validate_semester(semester, required=True)
		academic_year = clean_label(academic_year, "Academic year", required=True, max_length=20)
		department = clean_label(department, "Department", max_length=140)
		parsed_due = as_date(due_date)
	except AcademicRuleError as exc:
		raise_rule(exc)
	if not parsed_due:
		frappe.throw(_("Due date is required."), frappe.ValidationError)
	student_name = resolve_student(student, student_id)
	batch_name = resolve_batch(batch)
	if not viewer_can_see_student(student_name):
		frappe.throw(_("You are not allowed to create a fee record for this student."), frappe.PermissionError)
	doc = frappe.get_doc(
		{
			"doctype": "LMS Fee Account",
			"student": student_name,
			"batch": batch_name,
			"academic_year": academic_year,
			"semester": semester,
			"department": department,
			"total_fees": total,
			"due_date": parsed_due,
		}
	)
	doc.insert()
	return get_fee_account(doc.name)


@frappe.whitelist()
def record_fee_payment(
	fee_account: str,
	amount: str,
	payment_date: str,
	payment_method: str,
	transaction_id: str = "",
	remarks: str = "",
) -> dict:
	require_schema()
	require_fee_manager()
	if not frappe.db.exists("LMS Fee Account", fee_account):
		frappe.throw(_("Fee record not found."), frappe.DoesNotExistError)
	student = frappe.db.get_value("LMS Fee Account", fee_account, "student")
	if not viewer_can_see_student(student):
		frappe.throw(_("You are not allowed to update this fee record."), frappe.PermissionError)
	try:
		paid = apply_money(amount, allow_zero=False)
		method = validate_payment_method(payment_method)
		paid_on = validate_payment_date(payment_date, nowdate())
		reference = clean_label(transaction_id, "Transaction reference", max_length=140)
		note = clean_label(remarks, "Remarks", max_length=280)
	except AcademicRuleError as exc:
		raise_rule(exc)
	doc = frappe.get_doc(
		{
			"doctype": "LMS Fee Transaction",
			"fee_account": fee_account,
			"amount": paid,
			"payment_date": paid_on,
			"payment_method": method,
			"transaction_id": reference,
			"remarks": note,
		}
	)
	doc.insert()
	return get_fee_account(fee_account)


@frappe.whitelist()
def get_report(
	report: str,
	filters: dict | str | None = None,
	page: int = 1,
	page_size: int = 20,
	sort_by: str = "",
	sort_order: str = "desc",
) -> dict:
	require_schema()
	report = (report or "").strip()
	if report not in REPORTS or not can_access_report(roles_of(), report):
		frappe.throw(_("You are not allowed to view this report."), frappe.PermissionError)
	page, page_size, = page_window(page, page_size)[:2]
	sort_order = sort_order if sort_order in SORT_ORDERS else "desc"
	parsed = parse_filters(filters)
	if report == "mine":
		return _mine_report()
	if report == "students":
		return _student_report(parsed, page, page_size, sort_by or "student_id", sort_order)
	if report == "batches":
		return _batch_report(parsed, page, page_size, sort_by or "batch_code", sort_order)
	if report == "fees":
		if current_level() == "faculty":
			pass
		return _fee_report(parsed, page, page_size, sort_by or "due_date", sort_order)
	return _activity_report(parsed, page, page_size)


@frappe.whitelist()
def export_report(report: str, filters: dict | str | None = None) -> dict:
	report = (report or "").strip()
	if report not in REPORTS or not can_access_report(roles_of(), report):
		frappe.throw(_("You are not allowed to export this report."), frappe.PermissionError)
	require_schema()
	if report == "mine":
		payload = _mine_report()
	else:
		rows, columns = _export_rows(report, parse_filters(filters))
		payload = {"columns": columns, "rows": rows}
	buffer = io.StringIO()
	writer = csv.writer(buffer)
	headers = [column["label"] for column in payload["columns"]]
	keys = [column["key"] for column in payload["columns"]]
	writer.writerow(headers)
	for row in payload["rows"]:
		writer.writerow([csv_cell(row.get(key)) for key in keys])
	filename = f"{report}-report.csv"
	return {"filename": filename, "mime": "text/csv", "content": buffer.getvalue()}


def _export_rows(report: str, filters: dict) -> tuple[list, list]:
	collected = []
	columns = []
	for page in range(1, 51):
		if report == "students":
			chunk = _student_report(filters, page, 100, "student_id", "asc")
		elif report == "batches":
			chunk = _batch_report(filters, page, 100, "batch_code", "asc")
		elif report == "fees":
			chunk = _fee_report(filters, page, 100, "due_date", "asc")
		elif report == "activity":
			chunk = _activity_report(filters, page, 100)
		else:
			break
		columns = chunk["columns"]
		collected.extend(chunk["rows"])
		if len(collected) >= chunk["total"] or not chunk["rows"]:
			break
	return collected[:5000], columns


def _mine_report() -> dict:
	card = academic_profile(frappe.session.user) or {}
	accounts = []
	if frappe.db.exists("DocType", "LMS Fee Account"):
		raw = frappe.get_all(
			"LMS Fee Account",
			filters={"student": frappe.session.user},
			fields=[
				"name",
				"student_id",
				"batch_code",
				"academic_year",
				"semester",
				"total_fees",
				"amount_paid",
				"pending_amount",
				"status",
				"due_date",
			],
			limit=50,
		)
		accounts = [present_fee(row) for row in raw]
	return {
		"report": "mine",
		"summary": [
			{"label": "Student ID", "value": card.get("student_id") or "—"},
			{"label": "Batch ID", "value": card.get("batch_code") or "—"},
			{"label": "Fee status", "value": card.get("fee_status") or "—"},
			{"label": "Outstanding", "value": card.get("pending_amount") or "0.00"},
		],
		"columns": _fee_columns(),
		"rows": accounts,
		"total": len(accounts),
		"page": 1,
		"page_size": len(accounts) or 1,
		"profile": card,
	}


def _student_report(filters, page, page_size, sort_by, sort_order) -> dict:
	if current_level() not in {"super_admin", "admin", "faculty"}:
		frappe.throw(_("You are not allowed to view student reports."), frappe.PermissionError)
	page, page_size, offset = page_window(page, page_size)
	sort_col = STUDENT_SORTS.get(sort_by, "u.student_id")
	direction = "ASC" if sort_order == "asc" else "DESC"
	conditions, values = _student_conditions(filters)
	where = " AND ".join(conditions)
	total = frappe.db.sql(
		f"""
		SELECT COUNT(*)
		FROM `tabUser` u
		INNER JOIN `tabHas Role` r ON r.parent = u.name AND r.parenttype = 'User' AND r.role = 'LMS Student'
		LEFT JOIN `tabLMS Batch` b ON b.name = u.active_batch
		WHERE {where}
		""",
		values,
	)[0][0]
	rows = frappe.db.sql(
		f"""
		SELECT u.name, u.full_name, u.username, u.student_id,
			b.name AS batch, b.batch_code, b.title AS batch_title,
			b.academic_year, b.department, b.semester
		FROM `tabUser` u
		INNER JOIN `tabHas Role` r ON r.parent = u.name AND r.parenttype = 'User' AND r.role = 'LMS Student'
		LEFT JOIN `tabLMS Batch` b ON b.name = u.active_batch
		WHERE {where}
		ORDER BY {sort_col} {direction}
		LIMIT %(limit)s OFFSET %(offset)s
		""",
		{**values, "limit": page_size, "offset": offset},
		as_dict=True,
	)
	distribution = frappe.db.sql(
		f"""
		SELECT IFNULL(NULLIF(b.department, ''), 'Unassigned') AS department, COUNT(*) AS students
		FROM `tabUser` u
		INNER JOIN `tabHas Role` r ON r.parent = u.name AND r.parenttype = 'User' AND r.role = 'LMS Student'
		LEFT JOIN `tabLMS Batch` b ON b.name = u.active_batch
		WHERE {where}
		GROUP BY IFNULL(NULLIF(b.department, ''), 'Unassigned')
		ORDER BY students DESC
		LIMIT 20
		""",
		values,
		as_dict=True,
	)
	safe_rows = []
	for row in rows:
		safe_rows.append(
			{
				"full_name": row.full_name,
				"username": row.username,
				"student_id": row.student_id,
				"batch": row.batch,
				"batch_code": row.batch_code,
				"batch_title": row.batch_title,
				"academic_year": row.academic_year,
				"department": row.department,
				"semester": row.semester,
			}
		)
	return {
		"report": "students",
		"summary": [
			{"label": "Students", "value": total},
			{"label": "Departments", "value": len(distribution)},
		],
		"distribution": distribution,
		"columns": [
			{"key": "student_id", "label": "Student ID"},
			{"key": "full_name", "label": "Name"},
			{"key": "batch_code", "label": "Batch ID"},
			{"key": "batch_title", "label": "Batch"},
			{"key": "department", "label": "Department"},
			{"key": "academic_year", "label": "Academic year"},
			{"key": "semester", "label": "Semester"},
		],
		"rows": safe_rows,
		"total": total,
		"page": page,
		"page_size": page_size,
	}


def _student_conditions(filters: dict) -> tuple[list[str], dict]:
	conditions = ["u.enabled = 1", "IFNULL(u.student_id, '') != ''"]
	values = {}
	scope = visible_students()
	if scope is not None:
		if not scope:
			conditions.append("1=0")
		else:
			conditions.append("u.name in %(scope)s")
			values["scope"] = scope
	query = filters.get("query") or filters.get("student_id") or ""
	if query:
		values["query"] = like_term(query)
		conditions.append(
			"(u.student_id LIKE %(query)s OR u.full_name LIKE %(query)s OR u.username LIKE %(query)s)"
		)
	batch_id = filters.get("batch_id") or ""
	if batch_id:
		values["batch_like"] = like_term(batch_id)
		values["batch_exact"] = str(batch_id).strip()[:140]
		conditions.append("(b.batch_code LIKE %(batch_like)s OR b.name = %(batch_exact)s)")
	for field, column in (
		("department", "b.department"),
		("academic_year", "b.academic_year"),
		("semester", "b.semester"),
	):
		if filters.get(field):
			values[field] = str(filters[field]).strip()[:140]
			conditions.append(f"{column} = %({field})s")
	return conditions, values


def _batch_report(filters, page, page_size, sort_by, sort_order) -> dict:
	if current_level() not in {"super_admin", "admin", "faculty"}:
		frappe.throw(_("You are not allowed to view batch reports."), frappe.PermissionError)
	page, page_size, offset = page_window(page, page_size)
	sort_col = BATCH_SORTS.get(sort_by, "batch_code")
	direction = "ASC" if sort_order == "asc" else "DESC"
	conditions, values = _batch_conditions(filters)
	where = " AND ".join(conditions)
	count = frappe.db.sql(
		f"SELECT COUNT(*) FROM `tabLMS Batch` b WHERE {where}",
		values,
	)[0][0]
	rows = frappe.db.sql(
		f"""
		SELECT b.name, b.batch_code, b.title, b.academic_year, b.department, b.semester,
			b.start_date, b.end_date,
			SUM(CASE WHEN e.active = 1 THEN 1 ELSE 0 END) AS active_students,
			COUNT(e.name) AS enrolled_students
		FROM `tabLMS Batch` b
		LEFT JOIN `tabLMS Batch Enrollment` e ON e.batch = b.name
		WHERE {where}
		GROUP BY b.name, b.batch_code, b.title, b.academic_year, b.department, b.semester, b.start_date, b.end_date
		ORDER BY {sort_col} {direction}
		LIMIT %(limit)s OFFSET %(offset)s
		""",
		{**values, "limit": page_size, "offset": offset},
		as_dict=True,
	)
	for row in rows:
		row["start_date"] = str(row.start_date) if row.start_date else None
		row["end_date"] = str(row.end_date) if row.end_date else None
		row["active_students"] = cint(row.active_students)
		row["enrolled_students"] = cint(row.enrolled_students)
	year_rows = frappe.db.sql(
		f"""
		SELECT IFNULL(NULLIF(b.academic_year, ''), 'Unassigned') AS academic_year, COUNT(*) AS batches
		FROM `tabLMS Batch` b
		WHERE {where}
		GROUP BY academic_year
		ORDER BY batches DESC
		LIMIT 20
		""",
		values,
		as_dict=True,
	)
	active_total = frappe.db.sql(
		f"""
		SELECT COUNT(e.name)
		FROM `tabLMS Batch Enrollment` e
		INNER JOIN `tabLMS Batch` b ON b.name = e.batch
		WHERE e.active = 1 AND {where}
		""",
		values,
	)[0][0]
	return {
		"report": "batches",
		"summary": [
			{"label": "Batches", "value": count},
			{"label": "Active students", "value": active_total},
		],
		"distribution": year_rows,
		"columns": [
			{"key": "batch_code", "label": "Batch ID"},
			{"key": "title", "label": "Batch"},
			{"key": "academic_year", "label": "Academic year"},
			{"key": "department", "label": "Department"},
			{"key": "semester", "label": "Semester"},
			{"key": "active_students", "label": "Active students"},
			{"key": "enrolled_students", "label": "Enrolled"},
		],
		"rows": rows,
		"total": count,
		"page": page,
		"page_size": page_size,
	}


def _batch_conditions(filters: dict) -> tuple[list[str], dict]:
	conditions = ["1=1"]
	values = {}
	scope = visible_batches()
	if scope is not None:
		if not scope:
			conditions.append("1=0")
		else:
			conditions.append("b.name in %(batches)s")
			values["batches"] = scope
	if filters.get("batch_id"):
		values["batch_like"] = like_term(filters["batch_id"])
		values["batch_exact"] = str(filters["batch_id"]).strip()[:140]
		conditions.append("(b.batch_code LIKE %(batch_like)s OR b.name = %(batch_exact)s)")
	for field in ("department", "academic_year", "semester"):
		if filters.get(field):
			values[field] = str(filters[field]).strip()[:140]
			conditions.append(f"b.{field} = %({field})s")
	return conditions, values


def _fee_columns() -> list[dict]:
	return [
		{"key": "student_id", "label": "Student ID"},
		{"key": "student_name", "label": "Student"},
		{"key": "batch_code", "label": "Batch ID"},
		{"key": "academic_year", "label": "Academic year"},
		{"key": "semester", "label": "Semester"},
		{"key": "total_fees", "label": "Total"},
		{"key": "amount_paid", "label": "Paid"},
		{"key": "pending_amount", "label": "Outstanding"},
		{"key": "status", "label": "Status"},
		{"key": "due_date", "label": "Due date"},
	]


def _fee_report(filters, page, page_size, sort_by, sort_order) -> dict:
	level = current_level()
	if level == "none":
		frappe.throw(_("You are not allowed to view fee reports."), frappe.PermissionError)
	if level == "student":
		filters = {**filters, "student_user": frappe.session.user}
	elif level == "faculty" and filters.get("student_user") not in (None, "", frappe.session.user):
		if not viewer_can_see_student(filters["student_user"]):
			frappe.throw(_("You are not allowed to view this student's fees."), frappe.PermissionError)
	page, page_size, offset = page_window(page, page_size)
	sort_col = FEE_SORTS.get(sort_by, "due_date")
	direction = "ASC" if sort_order == "asc" else "DESC"
	conditions, values = _fee_conditions(filters)
	where = " AND ".join(conditions)
	raw_rows = frappe.db.sql(
		f"""
		SELECT name, student, student_id, student_name, batch, batch_code, academic_year, semester,
			department, total_fees, amount_paid, pending_amount, status, due_date, currency
		FROM `tabLMS Fee Account`
		WHERE {where}
		ORDER BY {sort_col} {direction}
		LIMIT %(limit)s OFFSET %(offset)s
		""",
		{**values, "limit": page_size, "offset": offset},
		as_dict=True,
	)
	total = frappe.db.sql(
		f"SELECT COUNT(*) FROM `tabLMS Fee Account` WHERE {where}",
		values,
	)[0][0]
	rows = []
	for row in raw_rows:
		presented = present_fee(row)
		presented.pop("student", None)
		rows.append(presented)
	summary_row = frappe.db.sql(
		f"""
		SELECT
			IFNULL(SUM(amount_paid), 0) AS collected,
			IFNULL(SUM(pending_amount), 0) AS pending,
			SUM(CASE WHEN status = 'Paid' THEN 1 ELSE 0 END) AS paid_count,
			SUM(CASE WHEN status = 'Partially Paid' THEN 1 ELSE 0 END) AS partial_count,
			SUM(CASE WHEN status = 'Pending' THEN 1 ELSE 0 END) AS pending_count,
			SUM(CASE WHEN status = 'Overdue' THEN 1 ELSE 0 END) AS overdue_count,
			IFNULL(SUM(CASE WHEN amount_paid > 0 AND pending_amount > 0 THEN pending_amount ELSE 0 END), 0) AS partial_outstanding
		FROM `tabLMS Fee Account`
		WHERE {where}
		""",
		values,
		as_dict=True,
	)[0]
	batch_rows = frappe.db.sql(
		f"""
		SELECT IFNULL(batch_code, 'Unassigned') AS batch_code,
			IFNULL(SUM(amount_paid), 0) AS collected,
			IFNULL(SUM(pending_amount), 0) AS pending,
			COUNT(*) AS records
		FROM `tabLMS Fee Account`
		WHERE {where}
		GROUP BY batch_code
		ORDER BY collected DESC
		LIMIT 30
		""",
		values,
		as_dict=True,
	)
	payment_conditions, payment_values = _payment_conditions(filters)
	payments = frappe.db.sql(
		f"""
		SELECT name, student_id, batch_code, amount, payment_date, payment_method, transaction_id, academic_year, semester
		FROM `tabLMS Fee Transaction`
		WHERE {" AND ".join(payment_conditions)}
		ORDER BY payment_date DESC, creation DESC
		LIMIT 100
		""",
		payment_values,
		as_dict=True,
	)
	for payment in payments:
		payment["amount"] = format_stored(payment.amount)
		payment["payment_date"] = str(payment.payment_date) if payment.payment_date else None
	date_rows = frappe.db.sql(
		f"""
		SELECT payment_date, IFNULL(SUM(amount), 0) AS collected, COUNT(*) AS payments
		FROM `tabLMS Fee Transaction`
		WHERE {" AND ".join(payment_conditions)}
		GROUP BY payment_date
		ORDER BY payment_date DESC
		LIMIT 60
		""",
		payment_values,
		as_dict=True,
	)
	for row in date_rows:
		row["payment_date"] = str(row.payment_date) if row.payment_date else None
		row["collected"] = format_stored(row.collected)
	for row in batch_rows:
		row["collected"] = format_stored(row.collected)
		row["pending"] = format_stored(row.pending)
	return {
		"report": "fees",
		"summary": [
			{"label": "Collected", "value": format_stored(summary_row.collected)},
			{"label": "Outstanding", "value": format_stored(summary_row.pending)},
			{"label": "Partially paid outstanding", "value": format_stored(summary_row.partial_outstanding)},
			{"label": "Paid", "value": cint(summary_row.paid_count)},
			{"label": "Partially paid", "value": cint(summary_row.partial_count)},
			{"label": "Pending", "value": cint(summary_row.pending_count)},
			{"label": "Overdue", "value": cint(summary_row.overdue_count)},
		],
		"distribution": batch_rows,
		"collections": date_rows,
		"payments": payments,
		"columns": _fee_columns(),
		"rows": rows,
		"total": total,
		"page": page,
		"page_size": page_size,
		"statuses": list(FEE_STATUSES),
		"payment_methods": list(PAYMENT_METHODS),
		"semesters": list(SEMESTERS),
	}


def _fee_conditions(filters: dict) -> tuple[list[str], dict]:
	conditions = ["1=1"]
	values = {}
	level = current_level()
	if level == "student" or filters.get("student_user"):
		student = frappe.session.user if level == "student" else filters.get("student_user")
		if level == "student":
			student = frappe.session.user
		conditions.append("student = %(student)s")
		values["student"] = student
	elif level == "faculty":
		scope = visible_students() or ["__none__"]
		conditions.append("student in %(scope)s")
		values["scope"] = scope
	elif level not in {"super_admin", "admin"}:
		conditions.append("1=0")
	if filters.get("student_id"):
		values["student_like"] = like_term(filters["student_id"])
		conditions.append("student_id LIKE %(student_like)s")
	if filters.get("batch_id"):
		values["batch_like"] = like_term(filters["batch_id"])
		values["batch_exact"] = str(filters["batch_id"]).strip()[:140]
		conditions.append("(batch_code LIKE %(batch_like)s OR batch = %(batch_exact)s)")
	if filters.get("payment_status") in FEE_STATUSES:
		values["status"] = filters["payment_status"]
		conditions.append("status = %(status)s")
	for field in ("department", "academic_year", "semester"):
		if filters.get(field):
			values[field] = str(filters[field]).strip()[:140]
			conditions.append(f"{field} = %({field})s")
	if filters.get("date_from"):
		values["date_from"] = str(filters["date_from"])[:10]
		conditions.append("due_date >= %(date_from)s")
	if filters.get("date_to"):
		values["date_to"] = str(filters["date_to"])[:10]
		conditions.append("due_date <= %(date_to)s")
	return conditions, values


def _payment_conditions(filters: dict) -> tuple[list[str], dict]:
	conditions, values = _fee_account_scope_for_payments(filters)
	if filters.get("date_from"):
		values["date_from"] = str(filters["date_from"])[:10]
		conditions.append("payment_date >= %(date_from)s")
	if filters.get("date_to"):
		values["date_to"] = str(filters["date_to"])[:10]
		conditions.append("payment_date <= %(date_to)s")
	if filters.get("student_id"):
		values["student_like"] = like_term(filters["student_id"])
		conditions.append("student_id LIKE %(student_like)s")
	if filters.get("batch_id"):
		values["batch_like"] = like_term(filters["batch_id"])
		conditions.append("batch_code LIKE %(batch_like)s")
	return conditions, values


def _fee_account_scope_for_payments(filters: dict) -> tuple[list[str], dict]:
	conditions = ["1=1"]
	values = {}
	level = current_level()
	if level == "student":
		conditions.append("student = %(student)s")
		values["student"] = frappe.session.user
	elif level == "faculty":
		scope = visible_students() or ["__none__"]
		conditions.append("student in %(scope)s")
		values["scope"] = scope
	elif level not in {"super_admin", "admin"}:
		conditions.append("1=0")
	return conditions, values


def _activity_report(filters, page, page_size) -> dict:
	if not can_access_report(roles_of(), "activity"):
		frappe.throw(_("You are not allowed to view activity reports."), frappe.PermissionError)
	page, page_size, offset = page_window(page, page_size)
	conditions = ["1=1"]
	values = {}
	if filters.get("date_from"):
		values["date_from"] = str(filters["date_from"])[:10]
		conditions.append("DATE(creation) >= %(date_from)s")
	if filters.get("date_to"):
		values["date_to"] = str(filters["date_to"])[:10]
		conditions.append("DATE(creation) <= %(date_to)s")
	if filters.get("query"):
		values["query"] = like_term(filters["query"])
		conditions.append("(action LIKE %(query)s OR subject LIKE %(query)s OR document_name LIKE %(query)s)")
	where = " AND ".join(conditions)
	total = frappe.db.sql(f"SELECT COUNT(*) FROM `tabLMS Audit Log` WHERE {where}", values)[0][0]
	rows = frappe.db.sql(
		f"""
		SELECT name, creation, action, actor, document_type, document_name, subject
		FROM `tabLMS Audit Log`
		WHERE {where}
		ORDER BY creation DESC
		LIMIT %(limit)s OFFSET %(offset)s
		""",
		{**values, "limit": page_size, "offset": offset},
		as_dict=True,
	)
	for row in rows:
		row["creation"] = str(row.creation) if row.creation else None
	by_action = frappe.db.sql(
		f"""
		SELECT action, COUNT(*) AS total
		FROM `tabLMS Audit Log`
		WHERE {where}
		GROUP BY action
		ORDER BY total DESC
		LIMIT 20
		""",
		values,
		as_dict=True,
	)
	logins = []
	if "System Manager" in roles_of() or frappe.session.user == "Administrator":
		try:
			login_filters = {"operation": "Login"}
			if filters.get("date_from") and filters.get("date_to"):
				login_filters["creation"] = ["between", [filters["date_from"], filters["date_to"]]]
			logins = frappe.get_list(
				"Activity Log",
				filters=login_filters,
				fields=["owner", "creation", "operation", "subject"],
				order_by="creation desc",
				limit=page_size,
			)
			for login in logins:
				login["creation"] = str(login.creation) if login.creation else None
		except frappe.PermissionError:
			logins = []
	return {
		"report": "activity",
		"summary": [
			{"label": "Administrative actions", "value": total},
			{"label": "Logins shown", "value": len(logins)},
		],
		"distribution": by_action,
		"logins": logins,
		"columns": [
			{"key": "creation", "label": "When"},
			{"key": "action", "label": "Action"},
			{"key": "actor", "label": "Actor"},
			{"key": "subject", "label": "Subject"},
			{"key": "document_type", "label": "Record type"},
			{"key": "document_name", "label": "Record"},
		],
		"rows": rows,
		"total": total,
		"page": page,
		"page_size": page_size,
	}


@frappe.whitelist()
def list_access_directory(query: str = "", page: int = 1, page_size: int = 20) -> dict:
	require_schema()
	if access_level(roles_of()) not in {"super_admin", "admin"}:
		frappe.throw(_("You are not allowed to manage access."), frappe.PermissionError)
	page, page_size, offset = page_window(page, page_size)
	values = {}
	search = ""
	if query:
		values["query"] = like_term(query)
		search = "AND (u.full_name LIKE %(query)s OR u.username LIKE %(query)s OR IFNULL(u.student_id, '') LIKE %(query)s OR u.name LIKE %(query)s)"
	total = frappe.db.sql(
		f"""
		SELECT COUNT(DISTINCT u.name)
		FROM `tabUser` u
		INNER JOIN `tabHas Role` r ON r.parent = u.name AND r.parenttype = 'User'
			AND r.role IN ('LMS Student', 'Course Creator', 'Batch Evaluator', 'Moderator', 'System Manager')
		WHERE u.enabled = 1 AND u.name != 'Guest' {search}
		""",
		values,
	)[0][0]
	users = frappe.db.sql(
		f"""
		SELECT u.name, u.full_name, u.username, u.student_id
		FROM `tabUser` u
		INNER JOIN `tabHas Role` r ON r.parent = u.name AND r.parenttype = 'User'
			AND r.role IN ('LMS Student', 'Course Creator', 'Batch Evaluator', 'Moderator', 'System Manager')
		WHERE u.enabled = 1 AND u.name != 'Guest' {search}
		GROUP BY u.name, u.full_name, u.username, u.student_id
		ORDER BY u.full_name ASC
		LIMIT %(limit)s OFFSET %(offset)s
		""",
		{**values, "limit": page_size, "offset": offset},
		as_dict=True,
	)
	if users:
		role_rows = frappe.get_all(
			"Has Role",
			filters={
				"parent": ["in", [user.name for user in users]],
				"parenttype": "User",
				"role": ["in", ["LMS Student", "Course Creator", "Batch Evaluator", "Moderator", "System Manager"]],
			},
			fields=["parent", "role"],
			limit=500,
		)
	else:
		role_rows = []
	roles_by_user = {}
	for role in role_rows:
		roles_by_user.setdefault(role.parent, []).append(role.role)
	actor_is_super = access_level(roles_of()) == "super_admin"
	directory = []
	for user in users:
		user_roles = roles_by_user.get(user.name, [])
		directory.append(
			{
				"name": user.name,
				"full_name": user.full_name,
				"username": user.username,
				"student_id": user.student_id,
				"roles": user_roles,
				"access_level": access_level(user_roles),
				"can_edit": can_change_role(roles_of(), user_roles, "LMS Student") or (
					actor_is_super and "System Manager" in user_roles
				),
			}
		)
	recent = frappe.get_all(
		"LMS Audit Log",
		filters={"action": ["in", ["Role granted", "Role removed"]]},
		fields=["creation", "actor", "subject", "document_name"],
		order_by="creation desc",
		limit=8,
	)
	for entry in recent:
		entry["creation"] = str(entry.creation)
	return {
		"hierarchy": [
			{"role": "Super Admin", "maps_to": "System Manager", "summary": "Full access, including roles and permissions."},
			{"role": "Admin", "maps_to": "Moderator", "summary": "Students, batches, fees, and reports. Cannot change Super Admin access."},
			{"role": "Faculty / Staff", "maps_to": "Batch Evaluator, Course Creator", "summary": "Assigned batches and learners. No fee changes or role changes."},
			{"role": "Student", "maps_to": "LMS Student", "summary": "Own profile, Student ID, batch, and fee status only."},
		],
		"rows": directory,
		"recent": recent,
		"total": total,
		"page": page,
		"page_size": page_size,
		"actor_level": access_level(roles_of()),
	}
