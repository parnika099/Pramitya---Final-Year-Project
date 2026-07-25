import frappe


def execute():
	frappe.flags.skip_academic_audit = True
	try:
		from lms.lms.academic import ensure_academic_setup

		ensure_academic_setup()
	finally:
		frappe.flags.skip_academic_audit = False
