# Copyright (c) 2026, Pramitya and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class LMSCredentialProof(Document):
	protected_fields = {
		"certificate",
		"public_token",
		"chain_index",
		"credential_hash",
		"previous_hash",
		"block_hash",
		"anchored_at",
		"contract_version",
		"ai_viva_session",
	}

	def validate(self):
		if self.is_new():
			return
		before = self.get_doc_before_save()
		if before and any(self.get(field) != before.get(field) for field in self.protected_fields):
			frappe.throw(_("Credential proof records are immutable."), frappe.PermissionError)

	def on_trash(self):
		frappe.throw(_("Credential proof records cannot be deleted."), frappe.PermissionError)

