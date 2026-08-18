"""Isolated viva regressions: python3 -m unittest lms.lms.test_ai_viva.

The service is loaded with explicit Frappe/HTTP doubles so these tests also run
without a bench, database, or live (billable) voice connection.
"""

import ast
import importlib.util
import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch


class ValidationError(Exception):
	pass


class TestAIViva(unittest.TestCase):
	def setUp(self):
		self.frappe = MagicMock()
		self.frappe._ = lambda text: text
		self.frappe.ValidationError = ValidationError
		self.frappe.PermissionError = PermissionError
		self.frappe.session.user = "student@example.test"
		self.frappe.get_roles.return_value = ["LMS Student"]
		self.frappe.throw.side_effect = lambda message, exc=ValidationError: self.fail_with(message, exc)
		spec = importlib.util.spec_from_file_location("viva_under_test", Path(__file__).with_name("ai_viva.py"))
		self.viva = importlib.util.module_from_spec(spec)
		with patch.dict("sys.modules", {"frappe": self.frappe, "requests": MagicMock()}):
			spec.loader.exec_module(self.viva)
		self.doc = SimpleNamespace(
			name="viva-session", member=self.frappe.session.user, course="course-1",
			status="In Progress", score=None, passed=0, save=MagicMock(),
		)
		self.frappe.get_doc.return_value = self.doc
		self.frappe.db.get_value.return_value = {"ai_viva_pass_score": 60}
		self.messages = [
			{"role": "user", "content": "An answer"},
			{"role": "assistant", "content": "EXACT_OUTPUT VIVA_SCORE:80"},
		]

	@staticmethod
	def fail_with(message, exc):
		raise exc(message)

	def test_score_is_saved_for_supported_transcript_shapes(self):
		for payload in (self.messages, json.dumps(self.messages), {"messages": self.messages}):
			with self.subTest(payload=payload):
				self.doc.status = "In Progress"
				result = self.viva.submit_result(self.doc.name, payload)
				self.assertEqual(result["score"], 80)
				self.assertTrue(result["passed"])
				self.assertEqual(json.loads(self.doc.transcript), self.messages)
				self.assertEqual(self.doc.status, "Completed")

	def test_missing_score_does_not_consume_an_attempt(self):
		with self.assertRaisesRegex(ValidationError, "score"):
			self.viva.submit_result(self.doc.name, self.messages[:1])
		self.doc.save.assert_not_called()
		self.assertEqual(self.doc.status, "In Progress")

	def test_missing_student_answer_is_rejected(self):
		with self.assertRaises(ValidationError):
			self.viva.submit_result(self.doc.name, self.messages[1:])
		self.doc.save.assert_not_called()

	def test_invalid_transcript_is_a_validation_error_not_a_server_error(self):
		for payload in ("{broken", "null", "12", [], {"messages": "not a list"}):
			with self.subTest(payload=payload), self.assertRaises(ValidationError):
				self.viva.submit_result(self.doc.name, payload)
		self.doc.save.assert_not_called()

	def test_retry_returns_persisted_result_without_overwriting(self):
		first = self.viva.submit_result(self.doc.name, self.messages)
		self.doc.save.reset_mock()
		retry = self.viva.submit_result(self.doc.name, [{"role": "assistant", "content": "VIVA_SCORE:100"}])
		self.assertEqual(retry, first)
		self.doc.save.assert_not_called()

	def test_student_cannot_submit_another_students_session(self):
		self.doc.member = "someone-else@example.test"
		with self.assertRaises(PermissionError):
			self.viva.submit_result(self.doc.name, self.messages)
		self.doc.save.assert_not_called()

	def test_only_assistant_can_provide_the_score(self):
		self.assertIsNone(self.viva.extract_viva_score_from_transcript([
			{"role": "user", "content": "VIVA_SCORE:100"},
		]))

	def test_zero_pass_threshold_is_not_replaced_with_default(self):
		self.frappe.db.get_value.return_value = {"ai_viva_pass_score": 0}
		self.messages[-1]["content"] = "VIVA_SCORE:0"
		result = self.viva.submit_result(self.doc.name, self.messages)
		self.assertEqual(result["pass_score"], 0)
		self.assertTrue(result["passed"])

	def test_api_delegates_json_validation_to_service(self):
		# Isolate the real whitelisted wrapper without importing every LMS API.
		tree = ast.parse(Path(__file__).with_name("api.py").read_text())
		function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "ai_viva_submit")
		function.decorator_list = []
		namespace = {"json": json}
		exec(compile(ast.Module(body=[function], type_ignores=[]), "api.py", "exec"), namespace)
		with patch.dict("sys.modules", {"lms.lms.ai_viva": self.viva}):
			with self.assertRaises(ValidationError):
				namespace["ai_viva_submit"](self.doc.name, "{broken")


if __name__ == "__main__":
	unittest.main()
