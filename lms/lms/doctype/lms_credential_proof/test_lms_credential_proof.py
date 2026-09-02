import frappe

from lms.lms.credential import FRAUDULENT_DEMO_TOKEN, verify_credential
from lms.lms.test_helpers import BaseTestUtils


class TestLMSCredentialProof(BaseTestUtils):
	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")
		suffix = frappe.generate_hash(length=8)
		self.instructor = self._create_user(
			f"credential-instructor-{suffix}@example.com",
			"Credential",
			"Instructor",
			["Moderator", "Course Creator"],
		)
		self.student = self._create_user(
			f"credential-student-{suffix}@example.com",
			"Private",
			"Learner",
			["LMS Student"],
		)
		self.course = self._create_course(
			f"Credential Verification {suffix}", instructor=self.instructor.name
		)
		self._create_enrollment(self.student.name, self.course.name)
		self.certificate = self._create_certificate(self.course.name, self.student.name)
		proof_name = frappe.db.get_value(
			"LMS Credential Proof", {"certificate": self.certificate.name}, "name"
		)
		self.proof = frappe.get_doc("LMS Credential Proof", proof_name)

	def tearDown(self):
		frappe.db.delete("LMS Credential Proof", {"certificate": self.certificate.name})
		frappe.set_user("Administrator")
		super().tearDown()

	def test_genuine_proof_and_private_response(self):
		result = verify_credential(self.proof.public_token)
		self.assertEqual(result["status"], "genuine")
		serialised = frappe.as_json(result)
		self.assertNotIn(self.student.email, serialised)
		self.assertNotIn("transcript", serialised)

	def test_modified_credential_is_detected(self):
		frappe.db.set_value(
			"LMS Certificate",
			self.certificate.name,
			"course_title",
			"Changed after anchoring",
			update_modified=False,
		)
		result = verify_credential(self.proof.public_token)
		self.assertEqual(result["status"], "modified")

	def test_unknown_token_is_fraudulent(self):
		result = verify_credential(FRAUDULENT_DEMO_TOKEN)
		self.assertEqual(result["status"], "fraudulent")
		self.assertIsNone(result["credential"])

	def test_proof_fields_are_immutable(self):
		self.proof.block_hash = "0" * 64
		with self.assertRaises(frappe.PermissionError):
			self.proof.save(ignore_permissions=True)
