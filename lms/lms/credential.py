"""Tamper-evident credential proof demonstration for Unnati LMS.

This module deliberately keeps the ledger inside Frappe.  It demonstrates the
hashing, policy and verification properties of a credential blockchain without
claiming that records are published to a public network.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any

import frappe
from frappe import _
from frappe.utils import cint, now_datetime


CONTRACT_VERSION = "pramitya-credential-policy-v1"
FRAUDULENT_DEMO_TOKEN = "fraudulent-demo-credential"
ISSUER_ROLES = {"System Manager", "Moderator", "Course Creator", "Batch Evaluator"}


def _normalise(value: Any) -> str:
	if value is None:
		return ""
	if hasattr(value, "isoformat"):
		return value.isoformat()
	return str(value).strip()


def _site_secret() -> bytes:
	secret = frappe.local.conf.get("encryption_key") or frappe.local.site
	return str(secret).encode("utf-8")


def member_commitment(member: str) -> str:
	"""Create a site-bound, non-public commitment instead of hashing an email directly."""
	return hmac.new(_site_secret(), member.encode("utf-8"), hashlib.sha256).hexdigest()


def certificate_payload(certificate: Any) -> dict[str, str]:
	"""Return the canonical private payload used to detect later changes."""
	issuer = frappe.db.get_single_value("Website Settings", "app_name") or "Unnati Development LMS"
	return {
		"version": CONTRACT_VERSION,
		"certificate": _normalise(certificate.name),
		"member_commitment": member_commitment(certificate.member),
		"course": _normalise(certificate.course),
		"course_title": _normalise(certificate.course_title),
		"batch": _normalise(certificate.batch_name),
		"batch_title": _normalise(certificate.batch_title),
		"issue_date": _normalise(certificate.issue_date),
		"expiry_date": _normalise(certificate.expiry_date),
		"issuer": _normalise(issuer),
	}


def canonical_hash(payload: dict[str, Any]) -> str:
	encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
	return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _block_hash(
	chain_index: int,
	credential_hash: str,
	previous_hash: str,
	anchored_at: str,
) -> str:
	return canonical_hash(
		{
			"chain_index": chain_index,
			"contract_version": CONTRACT_VERSION,
			"credential_hash": credential_hash,
			"previous_hash": previous_hash,
			"anchored_at": anchored_at,
		}
	)


def _latest_passed_viva(certificate: Any) -> str | None:
	if not certificate.course or not frappe.db.exists("DocType", "LMS AI Viva Session"):
		return None
	rows = frappe.get_all(
		"LMS AI Viva Session",
		filters={
			"course": certificate.course,
			"member": certificate.member,
			"status": "Completed",
			"passed": 1,
		},
		pluck="name",
		order_by="completed_at desc",
		limit_page_length=1,
	)
	return rows[0] if rows else None


def _validate_policy(certificate: Any) -> None:
	if not certificate.member or not certificate.issue_date or not certificate.template:
		frappe.throw(_("Credential policy rejected an incomplete certificate."), frappe.ValidationError)
	if not certificate.course and not certificate.batch_name:
		frappe.throw(_("Credential policy requires a course or batch."), frappe.ValidationError)


def issue_credential_proof(certificate_name: str, enforce_permissions: bool = True) -> Any:
	"""Run the policy contract and append one proof to the local hash chain."""
	if not frappe.db.exists("DocType", "LMS Credential Proof"):
		return None
	if enforce_permissions and not ISSUER_ROLES.intersection(frappe.get_roles()):
		frappe.throw(_("Only an authorised institution role can anchor credentials."), frappe.PermissionError)

	existing = frappe.db.get_value("LMS Credential Proof", {"certificate": certificate_name}, "name")
	if existing:
		return frappe.get_doc("LMS Credential Proof", existing)

	certificate = frappe.get_doc("LMS Certificate", certificate_name)
	_validate_policy(certificate)
	last = frappe.get_all(
		"LMS Credential Proof",
		fields=["chain_index", "block_hash"],
		order_by="chain_index desc",
		limit_page_length=1,
	)
	chain_index = cint(last[0].chain_index) + 1 if last else 1
	previous_hash = last[0].block_hash if last else "0" * 64
	anchored_at = _normalise(now_datetime())
	credential_hash = canonical_hash(certificate_payload(certificate))

	proof = frappe.get_doc(
		{
			"doctype": "LMS Credential Proof",
			"certificate": certificate.name,
			"public_token": frappe.generate_hash(length=32),
			"chain_index": chain_index,
			"credential_hash": credential_hash,
			"previous_hash": previous_hash,
			"block_hash": _block_hash(chain_index, credential_hash, previous_hash, anchored_at),
			"anchored_at": anchored_at,
			"contract_version": CONTRACT_VERSION,
			"ai_viva_session": _latest_passed_viva(certificate),
		}
	)
	proof.insert(ignore_permissions=True)
	return proof


def anchor_certificate_after_insert(doc: Any, method: str | None = None) -> None:
	"""Document-event adapter; avoids modifying certificate issuance logic."""
	if frappe.flags.in_install or frappe.flags.in_migrate:
		return
	issue_credential_proof(doc.name, enforce_permissions=False)


def backfill_credential_proofs() -> int:
	if not frappe.db.exists("DocType", "LMS Credential Proof"):
		return 0
	created = 0
	for certificate_name in frappe.get_all("LMS Certificate", pluck="name", order_by="creation asc"):
		if not frappe.db.exists("LMS Credential Proof", {"certificate": certificate_name}):
			issue_credential_proof(certificate_name, enforce_permissions=False)
			created += 1
	return created


def _mask_name(name: str | None) -> str:
	parts = [part for part in (name or "Learner").split() if part]
	return " ".join(f"{part[0]}{'•' * max(2, len(part) - 1)}" for part in parts)


def _verification_result(token: str) -> dict[str, Any]:
	proof_name = frappe.db.get_value("LMS Credential Proof", {"public_token": token}, "name")
	if not proof_name:
		return {
			"status": "fraudulent",
			"title": _("Credential not found"),
			"message": _("No anchored proof matches this reference."),
			"credential": None,
			"proof": None,
		}

	proof = frappe.get_doc("LMS Credential Proof", proof_name)
	certificate = frappe.get_doc("LMS Certificate", proof.certificate)
	current_credential_hash = canonical_hash(certificate_payload(certificate))
	expected_block_hash = _block_hash(
		cint(proof.chain_index),
		proof.credential_hash,
		proof.previous_hash,
		_normalise(proof.anchored_at),
	)
	previous_valid = proof.previous_hash == "0" * 64 or bool(
		frappe.db.exists("LMS Credential Proof", {"block_hash": proof.previous_hash})
	)
	valid = (
		hmac.compare_digest(current_credential_hash, proof.credential_hash)
		and hmac.compare_digest(expected_block_hash, proof.block_hash)
		and previous_valid
	)
	status = "genuine" if valid else "modified"
	issuer = frappe.db.get_single_value("Website Settings", "app_name") or "Unnati Development LMS"
	return {
		"status": status,
		"title": _("Credential verified") if valid else _("Credential has changed"),
		"message": (
			_("The current credential matches its anchored proof.")
			if valid
			else _("The current credential no longer matches its anchored proof.")
		),
		"credential": {
			"id": certificate.name,
			"learner": _mask_name(certificate.member_name),
			"course": certificate.course_title or certificate.batch_title,
			"issuer": issuer,
			"issue_date": _normalise(certificate.issue_date),
		},
		"proof": {
			"anchored_at": _normalise(proof.anchored_at),
			"chain_index": cint(proof.chain_index),
			"credential_hash": proof.credential_hash,
			"block_hash": proof.block_hash,
			"contract_version": proof.contract_version,
		},
	}


@frappe.whitelist(allow_guest=True)
def verify_credential(token: str) -> dict[str, Any]:
	token = (token or "").strip()
	if not token or len(token) > 80:
		return _verification_result(FRAUDULENT_DEMO_TOKEN)
	return _verification_result(token)


@frappe.whitelist()
def get_credential_trust_dashboard() -> dict[str, Any]:
	if frappe.session.user == "Guest":
		frappe.throw(_("Login required"), frappe.PermissionError)

	completed = frappe.db.count("LMS AI Viva Session", {"status": "Completed"})
	passed = frappe.db.count("LMS AI Viva Session", {"status": "Completed", "passed": 1})
	scores = frappe.get_all(
		"LMS AI Viva Session",
		filters={"status": "Completed", "score": ["is", "set"]},
		pluck="score",
	)
	proof_count = frappe.db.count("LMS Credential Proof")
	linked_count = frappe.db.count("LMS Credential Proof", {"ai_viva_session": ["is", "set"]})
	proofs = frappe.get_all(
		"LMS Credential Proof",
		fields=["public_token", "certificate", "chain_index", "credential_hash", "block_hash"],
		order_by="chain_index asc",
		limit_page_length=20,
	)
	verified = []
	for proof in proofs:
		result = _verification_result(proof.public_token)
		if result["status"] == "genuine":
			verified.append({**proof, "case": "Genuine", "status": "genuine"})
		elif result["status"] == "modified":
			verified.append({**proof, "case": "Modified", "status": "modified"})

	return {
		"metrics": {
			"attempts": frappe.db.count("LMS AI Viva Session"),
			"completed": completed,
			"pass_rate": round((passed / completed * 100), 1) if completed else 0,
			"average_score": round(sum(float(score) for score in scores) / len(scores), 1) if scores else 0,
			"proofs": proof_count,
			"ai_linked": linked_count,
		},
		"demo_cases": {
			"genuine": next((row for row in verified if row["status"] == "genuine"), None),
			"modified": next((row for row in verified if row["status"] == "modified"), None),
			"fraudulent": {
				"case": "Fraudulent",
				"status": "fraudulent",
				"public_token": FRAUDULENT_DEMO_TOKEN,
			},
		},
		"proofs": verified,
	}


@frappe.whitelist()
def get_certificate_proofs(member: str) -> dict[str, str]:
	"""Return public tokens for certificates visible on a signed-in profile."""
	if frappe.session.user == "Guest":
		frappe.throw(_("Login required"), frappe.PermissionError)
	roles = set(frappe.get_roles())
	if member != frappe.session.user and not ISSUER_ROLES.intersection(roles):
		certificate_names = frappe.get_all(
			"LMS Certificate", {"member": member, "published": 1}, pluck="name"
		)
	else:
		certificate_names = frappe.get_all("LMS Certificate", {"member": member}, pluck="name")
	if not certificate_names:
		return {}
	rows = frappe.get_all(
		"LMS Credential Proof",
		filters={"certificate": ["in", certificate_names]},
		fields=["certificate", "public_token"],
	)
	return {row.certificate: row.public_token for row in rows}


@frappe.whitelist()
def anchor_credential(certificate: str) -> dict[str, Any]:
	proof = issue_credential_proof(certificate, enforce_permissions=True)
	return {"name": proof.name, "public_token": proof.public_token}
