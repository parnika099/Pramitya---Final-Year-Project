"""AI oral exam helpers: Deepgram Voice Agent token + session lifecycle."""

from __future__ import annotations

import json
import os
import re
from typing import Any

import frappe
import requests
from frappe import _

VIVA_SCORE_PATTERN = re.compile(r"VIVA_SCORE\s*:\s*(\d+(?:\.\d+)?)", re.IGNORECASE)

DEFAULT_WS = "wss://agent.deepgram.com/v1/agent/converse"


def get_deepgram_api_key() -> str:
	key = os.environ.get("DEEPGRAM_API_KEY") or frappe.conf.get("deepgram_api_key")
	if not key:
		frappe.throw(
			_("Deepgram API key is not configured. Set DEEPGRAM_API_KEY or site config deepgram_api_key."),
			frappe.ValidationError,
		)
	return key.strip()


def get_agent_websocket_url() -> str:
	return (
		frappe.conf.get("deepgram_agent_ws_url") or os.environ.get("DEEPGRAM_AGENT_WS_URL") or DEFAULT_WS
	)


def extract_viva_score_from_transcript(messages: list[dict[str, Any]]) -> float | None:
	"""Infer numeric score from agent messages mentioning VIVA_SCORE:N."""
	excerpts = []
	for row in messages or []:
		if not isinstance(row, dict):
			continue
		role = row.get("role")
		body = row.get("content") or row.get("text") or ""
		if role == "assistant" or row.get("type") == "assistant":
			if isinstance(body, str) and body.strip():
				excerpts.append(body)
	combined = "\n".join(excerpts)
	match = VIVA_SCORE_PATTERN.search(combined)
	if not match:
		return None
	raw = float(match.group(1))
	return max(0.0, min(100.0, raw))


def _student_gates_waived_in_developer_preview() -> bool:
	"""On benches with developer_mode, waive enrollment / 100% progress for admins to test the viva flow."""
	from frappe.utils import cint

	if not cint(frappe.conf.developer_mode):
		return False
	user = frappe.session.user
	if user == "Guest":
		return False
	if user == "Administrator":
		return True
	try:
		roles = set(frappe.get_roles(user))
	except Exception:
		roles = set()
	return bool({"System Manager", "Moderator"} & roles)


def _course_ai_viva_fields(course_name: str) -> dict[str, Any] | None:
	return frappe.db.get_value(
		"LMS Course",
		course_name,
		[
			"enable_ai_viva",
			"ai_viva_instructions",
			"ai_viva_pass_score",
			"ai_viva_max_attempts",
			"title",
		],
		as_dict=True,
	)


def _has_passed_viva(course: str, member: str) -> bool:
	return bool(
		frappe.db.exists(
			"LMS AI Viva Session",
			{"course": course, "member": member, "passed": 1, "status": "Completed"},
		)
	)


def _count_attempts(course: str, member: str) -> int:
	"""Attempts = completed vivas only (successful end or explicit submit)."""
	return int(
		frappe.db.count(
			"LMS AI Viva Session",
			filters={
				"course": course,
				"member": member,
				"status": "Completed",
			},
		)
	)


def verify_eligibility(course: str) -> dict[str, Any]:
	user = frappe.session.user
	if user == "Guest":
		frappe.throw(_("Login required"), frappe.PermissionError)

	cfg = _course_ai_viva_fields(course)
	if not cfg or not cfg.enable_ai_viva:
		return {
			"eligible": False,
			"reason": "not_enabled",
			"message": _("AI Viva is not enabled for this course."),
		}

	student_gate_bypass = _student_gates_waived_in_developer_preview()

	if not student_gate_bypass:
		if not frappe.db.exists("LMS Enrollment", {"course": course, "member": user}):
			return {
				"eligible": False,
				"reason": "not_enrolled",
				"message": _("You are not enrolled in this course."),
			}

		progress = frappe.db.get_value("LMS Enrollment", {"course": course, "member": user}, "progress") or 0
		if int(progress) < 100:
			return {
				"eligible": False,
				"reason": "incomplete",
				"message": _("Complete the course (100% progress) to unlock the AI Viva."),
			}

	if not student_gate_bypass:
		if _has_passed_viva(course, user):
			return {
				"eligible": False,
				"reason": "already_passed",
				"message": _("You have already passed the AI Viva."),
			}

	max_attempts = int(cfg.ai_viva_max_attempts or 3)
	if not student_gate_bypass and _count_attempts(course, user) >= max_attempts:
		return {
			"eligible": False,
			"reason": "max_attempts",
			"message": _("You have used all AI Viva attempts for this course."),
		}

	out: dict[str, Any] = {
		"eligible": True,
		"reason": None,
		"message": None,
		"max_attempts": max_attempts,
		"attempts_used": _count_attempts(course, user),
		"pass_score": float(cfg.ai_viva_pass_score or 60),
	}
	if student_gate_bypass:
		out["developer_preview_waiver"] = True
	return out


def _build_think_block(
	provider: str,
	model: str,
	temperature: float,
	prompt_text: str,
) -> dict[str, Any]:
	"""Build Voice Agent ``think`` block using Deepgram-managed LLMs only (secrets never shipped to SPA)."""

	p = (provider or "").strip().lower()

	if p in ("google", "gemini", ""):
		m = model.strip() if model.strip() else "gemini-2.5-flash-lite"
		return {
			"provider": {"type": "google", "model": m, "temperature": temperature},
			"prompt": prompt_text,
		}

	if p in ("open_ai", "openai", "gpt"):
		m = model.strip() if model.strip() else "gpt-4.1-nano"
		return {
			"provider": {"type": "open_ai", "model": m, "temperature": temperature},
			"prompt": prompt_text,
		}

	if p in ("cheap", "nano"):
		# Budget OpenAI-compatible tier billed via Deepgram.
		m = model.strip() if model.strip() else "gpt-4.1-nano"
		return {
			"provider": {"type": "open_ai", "model": m, "temperature": temperature},
			"prompt": prompt_text,
		}

	if p == "nvidia":
		m = model.strip() if model.strip() else "nemotron-3-nano-30B-A3B"
		return {
			"provider": {"type": "nvidia", "model": m, "temperature": temperature},
			"prompt": prompt_text,
		}

	if p == "anthropic":
		m = model.strip() if model.strip() else "claude-4-5-haiku-latest"
		return {
			"provider": {"type": "anthropic", "model": m, "temperature": temperature},
			"prompt": prompt_text,
		}

	frappe.throw(_("Unsupported AI Viva think provider: {0}").format(provider), frappe.ValidationError)


def build_agent_settings(course_name: str) -> dict[str, Any]:
	cfg = _course_ai_viva_fields(course_name)
	if not cfg:
		frappe.throw(_("Course not found"))

	instructions = (cfg.ai_viva_instructions or "").strip()
	course_title = cfg.title or course_name

	default_rubric = _(
		"You conduct a concise spoken viva examination for ONE student about the named course only. "
		"Ask one short question at a time and wait for the student's answer. "
		"Keep each turn to one or two short sentences; avoid lectures and lengthy feedback. "
		"Ask three to five substantive questions based on concepts the course title suggests. "
		"If the student asks to finish, assess the answers given so far and conclude. "
		"When you are satisfied you have judged understanding, conclude with ONE line ONLY in this "
		"exact format: EXACT_OUTPUT VIVA_SCORE:NN replacing NN with an integer from 0 to 100."
	)

	base_prompt_parts = [
		str(default_rubric),
		f"Course title: {course_title}.",
	]
	if instructions:
		base_prompt_parts.append(f"Instructor brief: {instructions}")

	# The browser-agent streams raw PCM from a Web Audio AudioContext, which is
	# normally 48kHz in Chrome/Safari even if getUserMedia requests 16kHz.
	input_sample_rate = int(frappe.conf.get("deepgram_input_sample_rate") or 48000)
	# Listening / TTS override via bench set-config keys deepgram_listen_model / deepgram_speak_model (or Docker env wired in init-*).
	listen_model = frappe.conf.get("deepgram_listen_model") or "nova-3"
	speak_model = frappe.conf.get("deepgram_speak_model") or "aura-2-thalia-en"
	# Thinking: Deepgram-managed Google Gemini (no API key shipped to the SPA — avoids leaking secrets on the websocket).
	# Override with bench set-config deepgram_think_model e.g. gemini-3.1-flash-lite-preview | gemini-2.5-flash | gpt-4.1-nano (open_ai).
	think_provider = (frappe.conf.get("deepgram_think_provider") or "google").strip().lower()
	think_model = (frappe.conf.get("deepgram_think_model") or "gemini-2.5-flash-lite").strip()
	think_temperature = float(frappe.conf.get("deepgram_think_temperature") or 0.45)

	think_block = _build_think_block(
		think_provider,
		think_model,
		think_temperature,
		"\n".join(base_prompt_parts),
	)

	return {
		"type": "Settings",
		"tags": ["pramitya", "course_viva", course_name[:32]],
		"audio": {
			"input": {"encoding": "linear16", "sample_rate": input_sample_rate},
			"output": {"encoding": "linear16", "sample_rate": 24000, "container": "none"},
		},
		"agent": {
			"listen": {
				"provider": {"type": "deepgram", "model": listen_model},
			},
			"think": think_block,
			"speak": {
				"provider": {"type": "deepgram", "model": speak_model},
			},
			"greeting": _("Hello — when you are ready, we will begin your short oral examination for this course."),
		},
	}


def request_deepgram_jwt_ttl(ttl_seconds: int = 60) -> dict[str, Any]:
	payload = {}
	if ttl_seconds and ttl_seconds > 0:
		payload["ttl_seconds"] = min(int(ttl_seconds), 3600)

	resp = requests.post(
		"https://api.deepgram.com/v1/auth/grant",
		headers={
			"Authorization": f"Token {get_deepgram_api_key()}",
			"Content-Type": "application/json",
		},
		json=payload,
		timeout=30,
	)
	if not resp.ok:
		frappe.throw(
			_("Deepgram auth failed ({0}). Check API key billing and permissions.").format(resp.status_code),
			frappe.ValidationError,
		)
	data = resp.json()
	if "access_token" not in data:
		frappe.throw(_("Unexpected Deepgram response"), frappe.ValidationError)
	return data


def _get_open_session(course: str, member: str) -> str | None:
	rows = frappe.get_all(
		"LMS AI Viva Session",
		filters={"course": course, "member": member, "status": "In Progress"},
		pluck="name",
		order_by="creation desc",
		limit_page_length=1,
	)
	return rows[0] if rows else None


def get_or_create_in_progress_session(course: str) -> Any:
	check = verify_eligibility(course)
	if not check["eligible"]:
		frappe.throw(check["message"])

	user = frappe.session.user
	open_name = _get_open_session(course, user)
	if open_name:
		return frappe.get_doc("LMS AI Viva Session", open_name)

	doc = frappe.get_doc(
		{
			"doctype": "LMS AI Viva Session",
			"course": course,
			"member": user,
			"status": "In Progress",
			"started_at": frappe.utils.now(),
			"transcript": "[]",
		}
	)
	doc.insert(ignore_permissions=True)

	return doc


def get_eligibility(course: str) -> dict[str, Any]:
	verify = verify_eligibility(course)
	out = {
		"eligible": verify["eligible"],
		"reason": verify.get("reason"),
		"message": verify.get("message"),
		"max_attempts": verify.get("max_attempts"),
		"attempts_used": verify.get("attempts_used"),
		"pass_score": verify.get("pass_score"),
		"websocket_url": get_agent_websocket_url(),
	}
	if verify.get("developer_preview_waiver"):
		out["developer_preview_waiver"] = True
	return out


def get_access_bundle(course: str, ttl_seconds: int = 60) -> dict[str, Any]:
	if frappe.session.user == "Guest":
		frappe.throw(_("Login required"), frappe.PermissionError)

	session_doc = get_or_create_in_progress_session(course)
	tok = request_deepgram_jwt_ttl(ttl_seconds=ttl_seconds)
	settings_payload = build_agent_settings(course)

	return {
		"session": session_doc.name,
		"access_token": tok["access_token"],
		"expires_in": tok.get("expires_in"),
		"websocket_url": get_agent_websocket_url(),
		"settings": settings_payload,
	}


def submit_result(session: str, transcript: list | str | dict) -> dict[str, Any]:
	user = frappe.session.user
	if user == "Guest":
		frappe.throw(_("Login required"), frappe.PermissionError)

	# Serialize retries so two submissions cannot overwrite the same attempt.
	doc = frappe.get_doc("LMS AI Viva Session", session, for_update=True)
	roles = set(frappe.get_roles(user))
	can_review = roles.intersection({"System Manager", "Moderator", "Course Creator"})
	if doc.member != user and not can_review:
		frappe.throw(_("Not permitted"), frappe.PermissionError)

	cfg = _course_ai_viva_fields(doc.course)
	configured_pass_score = (cfg or {}).get("ai_viva_pass_score")
	pass_bar = float(configured_pass_score if configured_pass_score is not None else 60)
	if doc.status == "Completed":
		# A lost response must not turn a successful save into an error on retry.
		return {
			"name": doc.name,
			"score": doc.score,
			"passed": bool(doc.passed),
			"pass_score": pass_bar,
		}
	if doc.status != "In Progress":
		frappe.throw(_("This viva session is not open for submission."), frappe.ValidationError)

	if isinstance(transcript, str):
		try:
			transcript = json.loads(transcript)
		except json.JSONDecodeError:
			frappe.throw(_("Invalid viva transcript. Please retry submitting."), frappe.ValidationError)
	messages = transcript.get("messages") if isinstance(transcript, dict) else transcript

	if not isinstance(messages, list) or not messages or not all(isinstance(row, dict) for row in messages):
		frappe.throw(_("Invalid viva transcript. Please retry submitting."), frappe.ValidationError)
	if not any(
		row.get("role") == "user"
		and isinstance(body := row.get("content") or row.get("text"), str)
		and body.strip()
		for row in messages
	):
		frappe.throw(_("Please answer at least one viva question before submitting."), frappe.ValidationError)

	score = extract_viva_score_from_transcript(messages)
	if score is None:
		frappe.throw(
			_("The examiner has not provided a score yet. Ask the examiner to finish, then submit again."),
			frappe.ValidationError,
		)
	passed = score >= pass_bar

	doc.transcript = json.dumps(messages, ensure_ascii=False)
	doc.score = score
	doc.passed = 1 if passed else 0
	doc.status = "Completed"
	doc.completed_at = frappe.utils.now()
	doc.save(ignore_permissions=True)

	return {
		"name": doc.name,
		"score": score,
		"passed": passed,
		"pass_score": pass_bar,
	}


def augment_course_payload(course_details: Any) -> None:
	if not course_details or frappe.session.user == "Guest":
		course_details.show_ai_viva_cta = 0
		return

	course = course_details.name
	if not frappe.db.get_value("LMS Course", course, "enable_ai_viva"):
		course_details.show_ai_viva_cta = 0
		return

	check = verify_eligibility(course)
	course_details.show_ai_viva_cta = 1 if check.get("eligible") else 0
	if not course_details.show_ai_viva_cta and check.get("message"):
		course_details.ai_viva_block_reason = check["message"]
