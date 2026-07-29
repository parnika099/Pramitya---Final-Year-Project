"""Academic identity, fee, and access rules.

Run without a bench: python -m unittest lms.lms.test_academic
"""

import datetime
import unittest

from lms.lms.academic_rules import (
	AcademicRuleError,
	access_level,
	can_access_report,
	can_change_role,
	can_manage_fees,
	can_view_student,
	fee_status,
	locked_value,
	money,
	other_active_enrollments,
	remaining_amount,
	validate_payment_method,
)


TODAY = datetime.date(2026, 10, 1)


class TestAcademicRules(unittest.TestCase):
	def test_fee_status_follows_payment_and_due_date(self):
		self.assertEqual(fee_status("1000.00", "1000.00", "2026-09-01", TODAY), "Paid")
		self.assertEqual(fee_status("1000", "0", "2026-10-15", TODAY), "Pending")
		self.assertEqual(fee_status("1000", "400", "2026-10-15", TODAY), "Partially Paid")
		self.assertEqual(fee_status("1000", "0", "2026-09-01", TODAY), "Overdue")
		self.assertEqual(fee_status("1000", "400", "2026-09-01", TODAY), "Overdue")
		self.assertEqual(fee_status("0", "0", "2026-09-01", TODAY), "Paid")

	def test_remaining_amount_and_money_validation(self):
		self.assertEqual(remaining_amount("1500.50", "500.25"), money("1000.25"))
		with self.assertRaises(AcademicRuleError):
			money("-1")
		with self.assertRaises(AcademicRuleError):
			money("10.555")
		with self.assertRaises(AcademicRuleError):
			money("abc")
		with self.assertRaises(AcademicRuleError):
			remaining_amount("100", "150")
		with self.assertRaises(AcademicRuleError):
			money("0", allow_zero=False)

	def test_student_cannot_read_another_students_record(self):
		roles = ["LMS Student"]
		self.assertTrue(can_view_student(roles, "learner@unnati.test", "learner@unnati.test"))
		self.assertFalse(
			can_view_student(roles, "learner@unnati.test", "other@unnati.test", [])
		)
		self.assertFalse(can_access_report(roles, "students"))
		self.assertFalse(can_access_report(roles, "fees"))
		self.assertFalse(can_access_report(roles, "activity"))
		self.assertTrue(can_access_report(roles, "mine"))

	def test_faculty_is_limited_to_assigned_students_and_cannot_change_fees(self):
		roles = ["Batch Evaluator", "LMS Student"]
		self.assertEqual(access_level(roles), "faculty")
		self.assertFalse(can_manage_fees(roles))
		self.assertTrue(
			can_view_student(roles, "faculty@unnati.test", "learner@unnati.test", ["learner@unnati.test"])
		)
		self.assertFalse(
			can_view_student(roles, "faculty@unnati.test", "other@unnati.test", ["learner@unnati.test"])
		)
		self.assertTrue(can_access_report(roles, "fees"))
		self.assertFalse(can_access_report(roles, "activity"))

	def test_admin_cannot_change_super_admin_roles(self):
		self.assertFalse(
			can_change_role(["Moderator"], ["System Manager", "Moderator"], "Moderator")
		)
		self.assertFalse(can_change_role(["Moderator"], ["LMS Student"], "System Manager"))
		self.assertTrue(can_change_role(["Moderator"], ["LMS Student"], "Batch Evaluator"))
		self.assertTrue(
			can_change_role(["System Manager"], ["System Manager"], "Moderator")
		)
		self.assertTrue(can_manage_fees(["Moderator"]))
		self.assertTrue(can_access_report(["System Manager"], "activity"))

	def test_identity_and_batch_assignment_stay_stable(self):
		self.assertEqual(locked_value("UNN-2026-00001", "UNN-2026-99999"), "UNN-2026-00001")
		self.assertEqual(locked_value("", "UNN-2026-00002"), "UNN-2026-00002")
		self.assertEqual(
			other_active_enrollments(["ENR-1", "ENR-2"], "ENR-2", True),
			["ENR-1"],
		)
		self.assertEqual(other_active_enrollments(["ENR-1"], "ENR-2", False), [])

	def test_payment_method_is_restricted(self):
		self.assertEqual(validate_payment_method("UPI"), "UPI")
		with self.assertRaises(AcademicRuleError):
			validate_payment_method("Crypto")


if __name__ == "__main__":
	unittest.main()
