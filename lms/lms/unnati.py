"""Unnati Development Institute profile, exam centre, and demo catalogue.

Public organization facts in this module are sourced from
https://unnatidevelopment.in/. Demo accounts deliberately use the reserved
``.test`` domain and are not intended to represent private staff identities.
"""

import os

import frappe
from frappe.utils import add_days, cint, getdate, nowdate
from frappe.utils.password import update_password


UNNATI_PROFILE = {
	"name": "Unnati Development Institute",
	"short_name": "Unnati",
	"website": "https://unnatidevelopment.in/",
	"logo": "https://unnatidevelopment.in/logo.png",
	"email": "training@unnatidevelopment.in",
	"phone": "+91 9028451002",
	"whatsapp": "https://wa.me/919028451002",
	"hours": "Monday–Saturday, 9:00 AM–2:00 PM and 5:00 PM–9:00 PM",
	"headline": "Build Your Career in Linux, Cloud & DevOps",
	"description": (
		"Hands-on Linux, Red Hat, cloud, containers, DevOps, data engineering, "
		"and generative AI education with practical labs, certification preparation, "
		"and placement assistance."
	),
	"recognition": [
		"Red Hat authorized training",
		"ISO 9001:2015 certified",
		"Hands-on server and cloud labs",
		"Certification and placement preparation",
	],
	"metrics": [
		{"label": "Alumni", "value": "15,000+"},
		{"label": "Hiring partners", "value": "350+"},
		{"label": "Learning model", "value": "70–100% practical"},
		{"label": "Lab access", "value": "24/7"},
	],
	"faculty": [
		{
			"name": "Ashutosh S. Bhakare",
			"role": "Director & Corporate Trainer",
			"experience": "25+ years",
			"specialties": "RHCI, RHCA, Linux, cloud, Kubernetes and enterprise training",
			"image": "https://unnatidevelopment.in/ashutosh-bhakare.jpg",
		},
		{
			"name": "Pavan Wankhade",
			"role": "CIO & Lead DevOps Consultant",
			"experience": "14+ years",
			"specialties": "DevOps, Python automation, Linux architecture and cloud engineering",
			"image": "https://unnatidevelopment.in/trainers/pavan-wankhade.jpg",
		},
		{
			"name": "Rachana Bhakare",
			"role": "Senior Faculty & Security Chapter Leader",
			"experience": "14+ years",
			"specialties": "Application security, OWASP, Linux, cloud and DevSecOps",
			"image": "https://unnatidevelopment.in/trainers/rachana-bhakare.jpg",
		},
		{
			"name": "Ankush Kathar",
			"role": "Senior Red Hat & OpenShift Specialist",
			"experience": "18+ years",
			"specialties": "RHCSA, RHCE, Kubernetes, OpenShift and Ansible",
			"image": "https://unnatidevelopment.in/trainers/ankush-kathar.jpg",
		},
	],
	"campuses": [
		{
			"name": "CIDCO Office",
			"city": "Chhatrapati Sambhajinagar",
			"address": "Shiv-Sawali, 2nd Floor, N-7, CIDCO R-28, Plot 60, opposite Baliram Patil High School",
			"phone": "+91 9028451002 · 0240-2485766",
		},
		{
			"name": "Bypass Office",
			"city": "Chhatrapati Sambhajinagar",
			"address": "Shiv-Sawali, Plot 13, GUT 70, near Alpine Hospital, Maharashtra 431001",
			"phone": "+91 8669331002 · 0240-2985766",
		},
		{
			"name": "Wakad Office",
			"city": "Pune",
			"address": "Office 222–223, Survey 153/1A, off Mumbai Expressway, behind TipTop International Hotel, Wakad",
			"phone": "+91 8669311002 · +91 9561191113",
		},
		{
			"name": "Hadapsar Office",
			"city": "Pune",
			"address": "501, Dosti Greenscapes, Hadapsar",
			"phone": "+91 8669311002 · +91 9561191113",
		},
		{
			"name": "Nashik Centre",
			"city": "Nashik",
			"address": "Coming soon",
			"phone": "+91 9028451002",
		},
	],
}


EXAM_TRACKS = [
	{
		"code": "EX200",
		"name": "Red Hat Certified System Administrator (RHCSA)",
		"course": "RHCSA / Certified Linux Administrator",
		"format": "Performance-based practical exam",
		"readiness": ["Linux administration labs", "Timed mock exam", "Troubleshooting review"],
	},
	{
		"code": "EX294",
		"name": "Red Hat Certified Engineer (RHCE)",
		"course": "RHCE - Red Hat Certified Engineer (Ansible)",
		"format": "Performance-based Ansible exam",
		"readiness": ["Playbooks and roles", "Jinja2 and Vault", "Timed automation lab"],
	},
	{
		"code": "LX102 · EX188",
		"name": "Linux and container certification pathway",
		"course": "KuCL 2.5 – The Ultimate DevOps Diploma Course",
		"format": "Theory plus hands-on container assessment",
		"readiness": ["Linux foundation", "Docker and Podman labs", "Container troubleshooting"],
	},
	{
		"code": "SAA-C03",
		"name": "AWS Certified Solutions Architect – Associate",
		"course": "AWS Certified Solutions Architect – Associate (SAA-C03)",
		"format": "Cloud architecture certification exam",
		"readiness": ["Architecture scenarios", "Well-Architected review", "Practice tests"],
	},
	{
		"code": "ACE",
		"name": "Google Cloud Associate Cloud Engineer",
		"course": "Google Cloud Certified Associate Cloud Engineer (ACE)",
		"format": "Google Cloud certification exam",
		"readiness": ["IAM and networking", "GKE operations", "Practice tests"],
	},
	{
		"code": "CKA",
		"name": "Certified Kubernetes Administrator",
		"course": "CCA & CKA – Container and Kubernetes Administration",
		"format": "Performance-based Kubernetes exam",
		"readiness": ["Cluster operations", "Workloads and services", "Timed kubectl lab"],
	},
]


UNNATI_COURSES = [
	{
		"title": "Next Gen DevOps — All-in-One Career Program",
		"category": "DevOps",
		"duration": "8 months",
		"level": "Advanced",
		"exam": "4 global certification pathways",
		"tags": "Unnati, DevOps, Linux, Cloud, GenAI",
		"short_introduction": "An end-to-end career program from Linux foundations to cloud-native DevOps and GenAI automation.",
		"chapters": [
			("Linux & Automation Foundation", ["Linux administration and shell workflows", "Git, Python and infrastructure automation"]),
			("Cloud-native Delivery", ["Containers, Kubernetes and OpenShift", "CI/CD, observability and GenAI-assisted operations"]),
		],
	},
	{
		"title": "FDE Career Accelerator - FCA Course",
		"category": "Data Engineering",
		"duration": "110 hours · 2 months",
		"level": "Advanced",
		"exam": "10-hour capstone assessment",
		"tags": "Unnati, Data Engineering, Python, SQL, ETL, RAG",
		"short_introduction": "A practical data engineering accelerator covering Python, SQL, ETL, cloud, DevOps and AI/RAG.",
		"chapters": [
			("Data Foundations", ["Python, SQL and ETL pipelines", "BigQuery and production data quality"]),
			("Platform Delivery", ["Docker, Kubernetes and Terraform", "CI/CD, AI/RAG and the capstone project"]),
		],
	},
	{
		"title": "RHCSA / Certified Linux Administrator",
		"category": "Linux",
		"duration": "4 months",
		"level": "Beginner",
		"exam": "RHCSA / CLA certification preparation",
		"tags": "Unnati, Red Hat, RHCSA, Linux, CLA",
		"short_introduction": "Build job-ready Linux administration skills through guided server labs and exam-focused practice.",
		"chapters": [
			("Linux Essentials", ["Command line, files and permissions", "Users, services and software management"]),
			("System Administration", ["Storage, networking and security", "Troubleshooting and RHCSA mock lab"]),
		],
	},
	{
		"title": "KuCL 2.5 – The Ultimate DevOps Diploma Course",
		"category": "DevOps",
		"duration": "8 months",
		"level": "Advanced",
		"exam": "LX102 · EX188",
		"tags": "Unnati, KuCL, Kubernetes, OpenShift, DevOps",
		"short_introduction": "A diploma pathway spanning Linux, containers, Kubernetes, OpenShift, cloud and delivery automation.",
		"chapters": [
			("Containers & Kubernetes", ["Docker, Podman, Buildah and Containerd", "Kubernetes administration and security"]),
			("Enterprise DevOps", ["OpenShift, ACM and virtualization", "Argo CD, Istio, Jenkins and Terraform"]),
		],
	},
	{
		"title": "RHCE - Red Hat Certified Engineer (Ansible)",
		"category": "Linux",
		"duration": "2 months",
		"level": "Advanced",
		"exam": "EX294",
		"tags": "Unnati, Red Hat, RHCE, Ansible, EX294",
		"short_introduction": "Prepare for EX294 through repeatable Ansible automation labs, roles, templates and Vault.",
		"chapters": [
			("Ansible Core", ["Inventories, ad-hoc commands and playbooks", "Variables, facts and handlers"]),
			("Exam Automation", ["Roles, collections, Jinja2 and Vault", "Timed EX294 simulation"]),
		],
	},
	{
		"title": "AWS Certified Solutions Architect – Associate (SAA-C03)",
		"category": "Cloud",
		"duration": "4 weeks",
		"level": "Intermediate",
		"exam": "SAA-C03",
		"tags": "Unnati, AWS, Cloud, SAA-C03",
		"short_introduction": "Design secure, resilient and cost-aware AWS architectures and prepare for SAA-C03.",
		"chapters": [
			("AWS Architecture", ["Identity, compute, networking and storage", "Databases, resilience and scaling"]),
			("Serverless & Exam Prep", ["Serverless and CloudFormation", "Architecture scenarios and practice tests"]),
		],
	},
	{
		"title": "Google Cloud Certified Associate Cloud Engineer (ACE)",
		"category": "Cloud",
		"duration": "4 weeks",
		"level": "Intermediate",
		"exam": "Google Cloud ACE",
		"tags": "Unnati, Google Cloud, GCP, ACE",
		"short_introduction": "Deploy and operate workloads on Google Cloud with IAM, GKE, operations and Terraform practice.",
		"chapters": [
			("Google Cloud Foundation", ["IAM, compute, networking and storage", "Databases and managed services"]),
			("Operations & Readiness", ["GKE, monitoring and security", "Terraform and ACE practice tests"]),
		],
	},
	{
		"title": "CCA & CKA – Container and Kubernetes Administration",
		"category": "Containers",
		"duration": "2 months",
		"level": "Advanced",
		"exam": "CCA · CKA",
		"tags": "Unnati, Docker, Kubernetes, CKA, Containers",
		"short_introduction": "Master container tooling and Kubernetes administration through performance-based labs.",
		"chapters": [
			("Container Administration", ["Docker, Podman and Buildah", "Images, registries and Containerd"]),
			("Kubernetes Administration", ["Cluster operations and workloads", "Networking, storage and troubleshooting"]),
		],
	},
	{
		"title": "Configuration Management with Ansible & Terraform",
		"category": "DevOps",
		"duration": "8 weeks",
		"level": "Advanced",
		"exam": "Practical automation assessment",
		"tags": "Unnati, Ansible, Terraform, Infrastructure as Code",
		"short_introduction": "Automate configuration and cloud infrastructure with reusable Ansible and Terraform workflows.",
		"chapters": [
			("Configuration Management", ["Ansible inventories, playbooks and roles", "Secrets, templates and reusable automation"]),
			("Infrastructure as Code", ["Terraform state, modules and providers", "Plan, review and delivery workflows"]),
		],
	},
	{
		"title": "Multi-Cloud Generative AI Practitioner",
		"category": "Artificial Intelligence",
		"duration": "30 hours",
		"level": "Intermediate",
		"exam": "Labs and capstone demonstration",
		"tags": "Unnati, Generative AI, AWS, GCP, Azure, Agents",
		"short_introduction": "Build practical generative and agentic AI applications across AWS, Google Cloud and Azure.",
		"chapters": [
			("Multi-cloud AI", ["Foundation models across AWS, GCP and Azure", "Prompting, retrieval and responsible AI"]),
			("Agentic Applications", ["Tools, agents and workflow automation", "Capstone build and demonstration"]),
		],
	},
]


FACULTY_USERS = [
	("ashutosh.bhakare@unnati.test", "Ashutosh", "Bhakare", ["Moderator", "Course Creator", "Batch Evaluator"]),
	("pavan.wankhade@unnati.test", "Pavan", "Wankhade", ["Moderator", "Course Creator", "Batch Evaluator"]),
	("rachana.bhakare@unnati.test", "Rachana", "Bhakare", ["Moderator", "Course Creator", "Batch Evaluator"]),
	("ankush.kathar@unnati.test", "Ankush", "Kathar", ["Moderator", "Course Creator", "Batch Evaluator"]),
]
STUDENT_USERS = [
	("learner@unnati.test", "Unnati", "Learner"),
	("devops.student@unnati.test", "Aarav", "Patil"),
	("cloud.student@unnati.test", "Diya", "Sharma"),
	("linux.student@unnati.test", "Kabir", "Joshi"),
]


@frappe.whitelist(allow_guest=True)
def get_institute_profile():
	return UNNATI_PROFILE


@frappe.whitelist(allow_guest=True)
def get_exam_center():
	data = {
		"tracks": EXAM_TRACKS,
		"support": {
			"mock_exams": True,
			"practical_labs": True,
			"ai_viva": True,
			"credential_verification": True,
		},
		"learner": None,
		"operations": None,
	}
	if frappe.session.user == "Guest":
		return data

	user = frappe.session.user
	data["learner"] = {
		"enrollments": _safe_count("LMS Enrollment", {"member": user}),
		"quiz_attempts": _safe_count("LMS Quiz Submission", {"member": user}),
		"certificates": _safe_count("LMS Certificate", {"member": user}),
		"ai_vivas": _safe_count("LMS AI Viva Session", {"member": user}),
	}
	if {"System Manager", "Moderator", "Course Creator", "Batch Evaluator"}.intersection(
		frappe.get_roles(user)
	):
		members = frappe.get_all("LMS Enrollment", pluck="member") if frappe.db.exists("DocType", "LMS Enrollment") else []
		data["operations"] = {
			"active_students": len(set(members)),
			"published_courses": _safe_count("LMS Course", {"published": 1}),
			"active_batches": _safe_count("LMS Batch", {"published": 1}),
			"quiz_attempts": _safe_count("LMS Quiz Submission"),
			"certificates": _safe_count("LMS Certificate"),
		}
	return data


def _safe_count(doctype, filters=None):
	if not frappe.db.exists("DocType", doctype):
		return 0
	return frappe.db.count(doctype, filters or {})


def seed_unnati_demo():
	"""Create an idempotent Unnati-branded working demonstration dataset."""
	from lms.demo.demo_data import (
		append_unique_child,
		create_progress,
		enroll_student_in_course,
		ensure_assessment_lesson,
		ensure_course_assignment,
		ensure_course_evaluator,
		ensure_course_quiz,
		ensure_showcase_batch,
	)
	from lms.lms.utils import create_user

	_configure_branding()
	users = _ensure_demo_users(create_user)
	for category in {course["category"] for course in UNNATI_COURSES}:
		_ensure_named_doc("LMS Category", "category", category)
	for source in ["Unnati Website", "Walk-in Counselling", "Corporate Training", "Student Referral"]:
		_ensure_named_doc("LMS Source", "source", source)

	courses = {}
	for index, spec in enumerate(UNNATI_COURSES):
		course = _ensure_course(spec, users[FACULTY_USERS[index % len(FACULTY_USERS)][0]])
		courses[spec["title"]] = course

	assessments = {}
	for title, course in courses.items():
		chapter = _ensure_chapter(course, "Certification Readiness")
		quiz = ensure_course_quiz(course, f"{title} Knowledge Check")
		assignment = ensure_course_assignment(course, f"{title} Practical Lab Submission")
		quiz_lesson = ensure_assessment_lesson(course, chapter, f"{title} Mock Test", "quiz", quiz.name)
		assignment_lesson = ensure_assessment_lesson(
			course, chapter, f"{title} Lab Assessment", "assignment", assignment.name
		)
		frappe.db.set_value("LMS Quiz", quiz.name, {"lesson": quiz_lesson.name, "course": course.name})
		frappe.db.set_value("LMS Assignment", assignment.name, "course", course.name)
		assessments[course.name] = {
			"quiz": quiz,
			"assignment": assignment,
			"quiz_lesson": quiz_lesson,
			"assignment_lesson": assignment_lesson,
			"exercise": None,
			"exercise_lesson": None,
		}

	student_emails = [item[0] for item in STUDENT_USERS]
	for course_index, course in enumerate(courses.values()):
		for student_index, email in enumerate(student_emails):
			student = users[email]
			enroll_student_in_course(student, course)
			if student_index == 0 or course_index < 2:
				create_progress(course, student, limit=None if student_index == 0 else 2)

	batch_users = dict(users)
	batch_users["instructor@pramitya.test"] = users["ashutosh.bhakare@unnati.test"]
	evaluator = ensure_course_evaluator(users["ankush.kathar@unnati.test"])
	batches = [
		ensure_showcase_batch(
			title="RHCSA Practical Lab & EX200 Preparation",
			description="Instructor-led Linux administration labs, progress tracking and a timed RHCSA mock exam.",
			courses=[courses["RHCSA / Certified Linux Administrator"], courses["RHCE - Red Hat Certified Engineer (Ansible)"]],
			users=batch_users,
			evaluator=evaluator,
			assessments=assessments,
			start_offset=3,
		),
		ensure_showcase_batch(
			title="DevOps, Kubernetes & Cloud Weekend Cohort",
			description="Weekend delivery for container, Kubernetes, AWS and Google Cloud certification pathways.",
			courses=[courses["Next Gen DevOps — All-in-One Career Program"], courses["CCA & CKA – Container and Kubernetes Administration"], courses["AWS Certified Solutions Architect – Associate (SAA-C03)"]],
			users=batch_users,
			evaluator=evaluator,
			assessments=assessments,
			start_offset=10,
		),
	]
	for batch in batches:
		for email in student_emails:
			_enroll_batch(users[email], batch, users["ashutosh.bhakare@unnati.test"])

	_program = _ensure_program(courses, users, append_unique_child)
	_ensure_jobs()
	_unpublish_legacy_courses()
	return {
		"organization": UNNATI_PROFILE["name"],
		"courses": len(courses),
		"students": len(student_emails),
		"faculty": len(FACULTY_USERS),
		"batches": len(batches),
		"program": _program.name,
	}


def _configure_branding():
	frappe.db.set_single_value("System Settings", "app_name", "Pramitya")
	frappe.db.set_single_value("Website Settings", "app_name", "Pramitya")
	settings = {
		"allow_guest_access": 1,
		"contact_us_email": UNNATI_PROFILE["email"],
		"contact_us_url": "https://unnatidevelopment.in/contact",
		"meta_description": "Unnati Development Institute LMS for Linux, Red Hat, cloud, DevOps, data engineering and AI training.",
		"meta_keywords": "Unnati Development Institute, Linux, Red Hat, RHCSA, RHCE, DevOps, Kubernetes, AWS, GCP, LMS",
	}
	meta = frappe.get_meta("LMS Settings")
	for field, value in settings.items():
		if meta.has_field(field):
			frappe.db.set_single_value("LMS Settings", field, value)


def _ensure_demo_users(create_user):
	users = {}
	password = os.environ.get("UNNATI_DEMO_PASSWORD") or os.environ.get("PRAMITYA_DEMO_PASSWORD") or os.environ.get("DEMO_PASSWORD")
	for email, first_name, last_name, roles in FACULTY_USERS:
		user = create_user(
			email=email,
			first_name=first_name,
			last_name=last_name,
			full_name=f"{first_name} {last_name}",
			user_image="/assets/lms/images/instructor.png",
			roles=roles,
		)
		for role in roles:
			if role not in frappe.get_roles(user.name):
				user.add_roles(role)
		users[email] = frappe.get_doc("User", email)
	for email, first_name, last_name in STUDENT_USERS:
		user = create_user(
			email=email,
			first_name=first_name,
			last_name=last_name,
			full_name=f"{first_name} {last_name}",
			user_image="/assets/lms/images/student.jpg",
			roles=["LMS Student"],
		)
		if "LMS Student" not in frappe.get_roles(user.name):
			user.add_roles("LMS Student")
		if password:
			update_password(user.name, password)
		users[email] = frappe.get_doc("User", email)
	return users


def _ensure_course(spec, instructor):
	name = frappe.db.get_value("LMS Course", {"title": spec["title"]}, "name")
	course = frappe.get_doc("LMS Course", name) if name else frappe.new_doc("LMS Course")
	course.update(
		{
			"title": spec["title"],
			"category": spec["category"],
			"tags": spec["tags"],
			"published": 1,
			"published_on": course.published_on or nowdate(),
			"featured": 1,
			"short_introduction": spec["short_introduction"],
			"description": (
				f"<p>{spec['short_introduction']}</p><p><b>Duration:</b> {spec['duration']} &nbsp; "
				f"<b>Level:</b> {spec['level']} &nbsp; <b>Assessment:</b> {spec['exam']}</p>"
			),
			"image": "/assets/lms/images/course_card.jpeg",
			"enable_ai_viva": 1,
			"ai_viva_pass_score": 60,
			"ai_viva_max_attempts": 3,
			"ai_viva_instructions": (
				f"Run a concise practical viva for {spec['title']}. Ask only about the published modules and "
				"finish with EXACT_OUTPUT VIVA_SCORE:NN, where NN is 0–100."
			),
			"enable_certification": 1,
			"disable_self_learning": 0,
		}
	)
	if not any(row.instructor == instructor.name for row in course.instructors):
		course.append("instructors", {"instructor": instructor.name})
	course.save(ignore_permissions=True)
	for chapter_title, lessons in spec["chapters"]:
		chapter = _ensure_chapter(course, chapter_title)
		for lesson_title in lessons:
			_ensure_lesson(course, chapter, lesson_title, spec)
	return course


def _ensure_chapter(course, title):
	from lms.demo.demo_data import prepare_chapter

	return prepare_chapter(course, title)


def _ensure_lesson(course, chapter, title, spec):
	from lms.demo.demo_data import create_lesson
	import json

	content = json.dumps(
		{
			"time": 1788950000000,
			"blocks": [
				{
					"id": frappe.generate_hash(length=10),
					"type": "paragraph",
					"data": {
						"text": f"{title} is part of Unnati's {spec['title']} pathway. Complete the guided lab, record evidence, and use the knowledge check to confirm readiness."
					},
				}
			],
			"version": "2.29.0",
		}
	)
	return create_lesson(course, chapter, title, content)


def _enroll_batch(student, batch, instructor):
	if frappe.db.exists("LMS Batch Enrollment", {"batch": batch.name, "member": student.name}):
		return
	original_user = frappe.session.user
	frappe.session.user = instructor.name
	try:
		doc = frappe.new_doc("LMS Batch Enrollment")
		doc.member = student.name
		doc.batch = batch.name
		if frappe.db.exists("LMS Source", "Unnati Website"):
			doc.source = "Unnati Website"
		doc.insert(ignore_permissions=True)
	finally:
		frappe.session.user = original_user or "Administrator"


def _ensure_program(courses, users, append_unique_child):
	title = "Unnati Linux, Cloud & DevOps Career Path"
	name = frappe.db.exists("LMS Program", {"title": title})
	program = frappe.get_doc("LMS Program", name) if name else frappe.new_doc("LMS Program")
	program.title = title
	program.published = 1
	program.enforce_course_order = 1
	for course in courses.values():
		append_unique_child(program, "program_courses", "course", course.name)
	for email, _first_name, _last_name in STUDENT_USERS:
		append_unique_child(program, "program_members", "member", users[email].name)
	program.save(ignore_permissions=True)
	return program


def _ensure_jobs():
	if not frappe.db.exists("DocType", "Job Opportunity"):
		return
	jobs = [
		("Linux Support Engineer — Placement Practice", "Chhatrapati Sambhajinagar", "Hybrid"),
		("DevOps Trainee — Placement Practice", "Pune", "Hybrid"),
		("Cloud Operations Intern — Placement Practice", "India", "Remote"),
	]
	meta = frappe.get_meta("Job Opportunity")
	for title, location, work_mode in jobs:
		name = frappe.db.get_value("Job Opportunity", {"job_title": title}, "name")
		doc = frappe.get_doc("Job Opportunity", name) if name else frappe.new_doc("Job Opportunity")
		values = {
			"job_title": title,
			"status": "Open",
			"company_name": "Unnati Placement Cell",
			"company_website": UNNATI_PROFILE["website"],
			"company_email_address": UNNATI_PROFILE["email"],
			"company_logo": "/assets/lms/images/lms-logo.png",
			"type": "Full Time",
			"work_mode": work_mode,
			"location": location,
			"country": "India",
			"description": "<p>Demonstration opportunity for learner readiness, application tracking and mock interview workflows. This is not a live employment guarantee.</p>",
		}
		for field, value in values.items():
			if meta.has_field(field):
				doc.set(field, value)
		doc.save(ignore_permissions=True)


def _unpublish_legacy_courses():
	legacy = [
		"Getting Started with Pramitya",
		"Web Development Foundations",
		"Data Literacy Basics",
		"AI Interview Readiness",
		"Python Programming Primer",
		"Cloud Deployment on Azure",
		"Product Analytics for Educators",
		"Communication for Placement Interviews",
	]
	for name in frappe.get_all("LMS Course", {"title": ["in", legacy]}, pluck="name"):
		frappe.db.set_value("LMS Course", name, "published", 0)


def _ensure_named_doc(doctype, fieldname, value):
	name = frappe.db.exists(doctype, value) or frappe.db.exists(doctype, {fieldname: value})
	if name:
		return frappe.get_doc(doctype, name)
	doc = frappe.new_doc(doctype)
	doc.set(fieldname, value)
	doc.insert(ignore_permissions=True)
	return doc
