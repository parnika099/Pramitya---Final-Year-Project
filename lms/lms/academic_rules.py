"""Pure rules for student identity, batches, fees, and access checks.

This module does not import Frappe so the rules can be tested without a site.
"""

from __future__ import annotations

import datetime
import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

STUDENT_ID_PATTERN = re.compile(r"^UNN-\d{4}-\d{5}$")
BATCH_ID_PATTERN = re.compile(r"^BTH-\d{4}-\d{4}$")

SEMESTERS = (
	"Semester 1",
	"Semester 2",
	"Semester 3",
	"Semester 4",
	"Semester 5",
	"Semester 6",
	"Semester 7",
	"Semester 8",
	"Year 1",
	"Year 2",
	"Year 3",
	"Year 4",
)

PAYMENT_METHODS = ("Cash", "UPI", "Card", "Bank Transfer", "Cheque", "Other")
FEE_STATUSES = ("Paid", "Partially Paid", "Pending", "Overdue")
REPORTS = ("students", "batches", "fees", "activity", "mine")

SUPER_ADMIN_ROLES = {"System Manager"}
ADMIN_ROLES = {"Moderator"}
FACULTY_ROLES = {"Batch Evaluator", "Course Creator"}
STUDENT_ROLES = {"LMS Student"}


class AcademicRuleError(ValueError):
	pass


def access_level(roles) -> str:
	role_set = set(roles or [])
	if "Administrator" in role_set or role_set & SUPER_ADMIN_ROLES:
		return "super_admin"
	if role_set & ADMIN_ROLES:
		return "admin"
	if role_set & FACULTY_ROLES:
		return "faculty"
	if role_set & STUDENT_ROLES:
		return "student"
	return "none"


def can_manage_fees(roles) -> bool:
	return access_level(roles) in {"super_admin", "admin"}


def can_manage_roles(roles) -> bool:
	return access_level(roles) in {"super_admin", "admin"}


def can_view_student(viewer_roles, viewer: str, student: str, faculty_students=None) -> bool:
	if not viewer or viewer == "Guest" or not student:
		return False
	if viewer == student:
		return True
	level = access_level(viewer_roles)
	if level in {"super_admin", "admin"}:
		return True
	if level == "faculty":
		return student in set(faculty_students or [])
	return False


def can_change_role(actor_roles, target_roles, role: str) -> bool:
	if access_level(actor_roles) not in {"super_admin", "admin"}:
		return False
	if role == "System Manager":
		return False
	target = set(target_roles or [])
	actor_is_super = access_level(actor_roles) == "super_admin"
	if "System Manager" in target and not actor_is_super:
		return False
	return role in {"LMS Student", "Course Creator", "Batch Evaluator", "Moderator"}


def can_access_report(roles, report: str) -> bool:
	if report not in REPORTS:
		return False
	level = access_level(roles)
	if report == "mine":
		return level != "none"
	if report == "activity":
		return level in {"super_admin", "admin"}
	return level in {"super_admin", "admin", "faculty"}


def locked_value(previous, submitted):
	if previous:
		return previous
	return submitted


def other_active_enrollments(active_names, current_name, make_active: bool) -> list:
	if not make_active:
		return []
	return [name for name in active_names if name and name != current_name]


def money(value, allow_zero: bool = True) -> Decimal:
	if isinstance(value, bool) or value is None:
		raise AcademicRuleError("Amount is required")
	if isinstance(value, str):
		value = value.strip().replace(",", "")
		if not value:
			raise AcademicRuleError("Amount is required")
	try:
		amount = Decimal(str(value))
	except (InvalidOperation, ValueError):
		raise AcademicRuleError("Enter a valid amount")
	if amount < 0:
		raise AcademicRuleError("Amount cannot be negative")
	if not allow_zero and amount == 0:
		raise AcademicRuleError("Amount must be greater than zero")
	quantized = amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
	if amount != quantized:
		raise AcademicRuleError("Use at most 2 decimal places")
	return quantized


def stored_money(value) -> Decimal:
	"""Normalize a stored amount. User input still goes through money()."""
	if isinstance(value, bool):
		raise AcademicRuleError("Enter a valid amount")
	if value is None or value == "":
		value = 0
	try:
		amount = Decimal(str(value))
	except (InvalidOperation, ValueError):
		raise AcademicRuleError("Enter a valid amount")
	if amount < 0:
		raise AcademicRuleError("Amount cannot be negative")
	return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def remaining_amount(total, paid) -> Decimal:
	total_amount = stored_money(total)
	paid_amount = stored_money(paid)
	if paid_amount > total_amount:
		raise AcademicRuleError("Paid amount cannot be greater than total fees")
	return total_amount - paid_amount


def as_date(value):
	if value is None or value == "":
		return None
	if isinstance(value, datetime.datetime):
		return value.date()
	if isinstance(value, datetime.date):
		return value
	text = str(value).strip()[:10]
	try:
		return datetime.date.fromisoformat(text)
	except ValueError:
		raise AcademicRuleError("Enter a valid date")


def fee_status(total, paid, due_date, today) -> str:
	pending = remaining_amount(total, paid)
	if pending == 0:
		return "Paid"
	due = as_date(due_date)
	current = as_date(today)
	if due and current and due < current:
		return "Overdue"
	if stored_money(paid) > 0:
		return "Partially Paid"
	return "Pending"


def validate_payment_date(payment_date, today):
	paid_on = as_date(payment_date)
	if not paid_on:
		raise AcademicRuleError("Payment date is required")
	current = as_date(today)
	if current and paid_on > current:
		raise AcademicRuleError("Payment date cannot be in the future")
	return paid_on


def clean_label(value, field: str, required: bool = False, max_length: int = 140) -> str:
	text = "" if value is None else str(value).strip()
	if required and not text:
		raise AcademicRuleError(f"{field} is required")
	if len(text) > max_length:
		raise AcademicRuleError(f"{field} is too long")
	if any(character in text for character in "<>"):
		raise AcademicRuleError(f"{field} contains invalid characters")
	return text


def validate_semester(value, required: bool = False) -> str:
	text = clean_label(value, "Semester", required=required, max_length=40)
	if text and text not in SEMESTERS:
		raise AcademicRuleError("Select a valid semester or year")
	return text


def validate_payment_method(value) -> str:
	text = clean_label(value, "Payment method", required=True, max_length=40)
	if text not in PAYMENT_METHODS:
		raise AcademicRuleError("Select a valid payment method")
	return text


def series_year(academic_year=None, start_date=None, today=None) -> str:
	match = re.search(r"\d{4}", str(academic_year or ""))
	if match:
		return match.group(0)
	parsed = None
	if start_date:
		try:
			parsed = as_date(start_date)
		except AcademicRuleError:
			parsed = None
	if parsed:
		return str(parsed.year)
	current = as_date(today) if today else datetime.date.today()
	return str(current.year)


def csv_cell(value) -> str:
	text = "" if value is None else str(value)
	if text[:1] in {"=", "+", "-", "@"}:
		text = "'" + text
	return text
