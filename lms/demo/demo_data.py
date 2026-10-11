import json
import os

import frappe
from frappe.utils import add_days, cint, getdate, now_datetime, nowdate
from frappe.utils.password import update_password

from lms.lms.doctype.lms_certificate.lms_certificate import get_default_certificate_template
from lms.lms.doctype.lms_course.lms_course import update_course_statistics
from lms.lms.doctype.lms_quiz.lms_quiz import submit_quiz
from lms.lms.doctype.lms_quiz_submission.lms_quiz_submission import MaximumAttemptsExceededError
from lms.lms.utils import create_user, get_course_progress

PRIMARY_DEMO_COURSE_TITLE = "Getting Started with Pramitya"
DEMO_LEARNER_EMAIL = "learner@pramitya.test"
DEMO_COURSE_TITLES = [
	PRIMARY_DEMO_COURSE_TITLE,
	"Web Development Foundations",
	"Data Literacy Basics",
	"AI Interview Readiness",
	"Python Programming Primer",
	"Cloud Deployment on Azure",
	"Product Analytics for Educators",
	"Communication for Placement Interviews",
]
DEMO_COURSE_CATEGORIES = [
	"Business",
	"Technology",
	"Analytics",
	"Career",
	"Cloud",
	"Communication",
]
DEMO_QUIZ_TITLES = [
	"Do you know Pramitya?",
	"Web Development Foundations Check",
	"Data Literacy Basics Check",
]
DEMO_COURSE_AI_VIVA_INSTRUCTIONS = (
	"Brief verbal questions on concepts from this demo course only. End with "
	"EXACT_OUTPUT VIVA_SCORE:NN (0-100), where NN is overall performance."
)
SAMPLE_COURSE_SPECS = [
	{
		"title": "Web Development Foundations",
		"category": "Technology",
		"tags": "Pramitya, Web, Demo",
		"short_introduction": "Learn how pages, styles, scripts, and deployment fit together in a small web application.",
		"description": """
			This sample course introduces the building blocks of modern web development: HTML for structure,
			CSS for presentation, JavaScript for interaction, and deployment basics for putting an app online.
		""",
		"chapters": [
			{
				"title": "Web Basics",
				"lessons": [
					("How the Web Works", "Browsers request pages from servers, then render HTML, CSS, and JavaScript."),
					("HTML and Structure", "Semantic HTML helps learners and assistive tools understand page content."),
				],
			},
			{
				"title": "Styling and Interaction",
				"lessons": [
					("CSS Layout", "Responsive layouts use flexible containers, grids, and spacing rules."),
					("JavaScript Events", "Interactive applications respond to clicks, form input, and network results."),
				],
			},
			{
				"title": "Deployment",
				"lessons": [
					("Going Live", "A deployed application needs a server, DNS, HTTPS, logs, and backups."),
				],
			},
		],
		"ai_viva_instructions": "Ask practical questions about HTML, CSS, JavaScript events, and deployment basics.",
	},
	{
		"title": "Data Literacy Basics",
		"category": "Analytics",
		"tags": "Pramitya, Data, Demo",
		"short_introduction": "Build confidence reading tables, charts, metrics, and basic data quality signals.",
		"description": """
			This sample course covers practical data literacy for students: identifying useful metrics,
			spotting unreliable data, comparing chart types, and explaining insights clearly.
		""",
		"chapters": [
			{
				"title": "Reading Data",
				"lessons": [
					("Rows, Columns, and Metrics", "A useful dataset has clear definitions for each field and metric."),
					("Data Quality", "Missing values, duplicates, and inconsistent formats can distort conclusions."),
				],
			},
			{
				"title": "Charts and Interpretation",
				"lessons": [
					("Choosing a Chart", "Bar charts compare categories, line charts show change, and tables support exact lookup."),
					("Explaining Insights", "Good analysis states the finding, evidence, caveat, and recommended action."),
				],
			},
		],
		"ai_viva_instructions": "Ask conceptual questions about metrics, data quality, chart choice, and explaining insights.",
	},
	{
		"title": "AI Interview Readiness",
		"category": "Career",
		"tags": "Pramitya, AI Interviewer, Viva, Demo",
		"short_introduction": "Practice structured answers, technical explanation, and reflection before an AI viva or placement interview.",
		"description": """
			This showcase course prepares learners for the AI interviewer feature. It covers answer framing,
			example selection, follow-up handling, and how learners should close a viva response with evidence.
		""",
		"chapters": [
			{
				"title": "Interview Mindset",
				"lessons": [
					("How AI Viva Works", "The AI interviewer asks concise questions, listens for reasoning, and returns a score when the viva is submitted."),
					("Answer Frameworks", "Strong answers use context, action, evidence, and reflection instead of memorized paragraphs."),
				],
			},
			{
				"title": "Practice Rounds",
				"lessons": [
					("Explaining Projects", "A project answer should name the problem, user, technical decision, and measurable result."),
					("Handling Follow-ups", "When a follow-up is unclear, restate the assumption before answering."),
				],
			},
		],
		"ai_viva_instructions": "Act as a placement viva interviewer. Ask about projects, reasoning, communication, and interview reflection.",
	},
	{
		"title": "Python Programming Primer",
		"category": "Technology",
		"tags": "Pramitya, Python, Programming, Demo",
		"short_introduction": "Learn Python fundamentals through functions, loops, data structures, and small coding exercises.",
		"description": """
			This sample course demonstrates coding-oriented learning with concept lessons, a quiz, an assignment,
			and a programming exercise that can be used in batch assessments.
		""",
		"chapters": [
			{
				"title": "Python Basics",
				"lessons": [
					("Variables and Types", "Python variables reference values such as strings, numbers, lists, and dictionaries."),
					("Functions", "Functions let you name reusable logic and return values to the caller."),
				],
			},
			{
				"title": "Control Flow",
				"lessons": [
					("Loops and Conditions", "Loops repeat work; conditions select the branch of code that should run."),
					("Debugging Small Programs", "Good debugging isolates input, expected output, actual output, and the first mismatch."),
				],
			},
		],
		"ai_viva_instructions": "Ask beginner Python questions about functions, loops, dictionaries, and debugging simple programs.",
	},
	{
		"title": "Cloud Deployment on Azure",
		"category": "Cloud",
		"tags": "Pramitya, Azure, Deployment, Demo",
		"short_introduction": "Understand virtual machines, DNS, HTTPS, containers, logs, and operational checks for a small web app.",
		"description": """
			This sample course mirrors the live Pramitya deployment path and gives learners a practical view of
			VM sizing, container startup, reverse proxies, DNS labels, and deployment verification.
		""",
		"chapters": [
			{
				"title": "Infrastructure Basics",
				"lessons": [
					("VMs and Containers", "A VM provides compute, while containers package app services consistently."),
					("DNS and HTTPS", "DNS maps a friendly name to an IP address, and HTTPS protects browser traffic."),
				],
			},
			{
				"title": "Operating the App",
				"lessons": [
					("Logs and Health Checks", "Useful deployment checks include HTTP status, process state, error logs, and memory use."),
					("Cost-aware Scaling", "A demo can start small, then scale when traffic or background workers require it."),
				],
			},
		],
		"ai_viva_instructions": "Ask about VM sizing, containers, DNS, HTTPS, app logs, and basic deployment verification.",
	},
	{
		"title": "Product Analytics for Educators",
		"category": "Analytics",
		"tags": "Pramitya, Product Analytics, Educators, Demo",
		"short_introduction": "Use learner activity, completion, assessment, and feedback data to improve a course.",
		"description": """
			This course demonstrates how an instructor can interpret completion rates, quiz scores, batch engagement,
			and learner feedback to improve lessons and interventions.
		""",
		"chapters": [
			{
				"title": "Learning Metrics",
				"lessons": [
					("Completion and Drop-off", "Completion rates show where learners finish; drop-off shows where they stop."),
					("Assessment Signals", "Quiz and assignment results are useful when linked to the learning objective they measure."),
				],
			},
			{
				"title": "Course Improvement",
				"lessons": [
					("Finding Bottlenecks", "A bottleneck combines low completion, repeated mistakes, and learner confusion."),
					("Action Plans", "A good action plan names the lesson change, support intervention, owner, and success metric."),
				],
			},
		],
		"ai_viva_instructions": "Ask about interpreting learner metrics, diagnosing drop-off, and choosing improvement actions.",
	},
	{
		"title": "Communication for Placement Interviews",
		"category": "Communication",
		"tags": "Pramitya, Communication, Placement, Demo",
		"short_introduction": "Practice concise spoken answers, examples, and follow-up responses for campus placement rounds.",
		"description": """
			This demo course shows soft-skill content alongside technical learning. It is useful for showcasing
			course variety, learner notes, discussions, and oral assessment readiness.
		""",
		"chapters": [
			{
				"title": "Speaking Clearly",
				"lessons": [
					("The First 30 Seconds", "Start with the direct answer, then add one relevant detail and one example."),
					("Avoiding Filler", "Short pauses are better than filler words when you are organizing your answer."),
				],
			},
			{
				"title": "Behavioral Examples",
				"lessons": [
					("STAR Responses", "STAR means situation, task, action, and result; it keeps behavioral answers structured."),
					("Closing Strongly", "A strong close connects the example back to the job or learning objective."),
				],
			},
		],
		"ai_viva_instructions": "Ask spoken interview questions about clarity, examples, STAR answers, and handling follow-ups.",
	},
]


def create_demo_data(args: dict = None):
	ensure_demo_categories()
	course = create_course()
	sample_courses = [course, *create_sample_courses()]
	student = create_user(
		email="ash@ipp.com",
		first_name="Ashley",
		last_name="Ippolito",
		full_name="Ashley Ippolito",
		user_image="/assets/lms/images/student.jpg",
	)
	student1 = create_user(
		email="john.doe@example.com",
		first_name="John",
		last_name="Doe",
		full_name="John Doe",
		user_image="/assets/lms/images/student1.jpeg",
	)
	student2 = create_user(
		email="jane.smith@example.com",
		first_name="Jane",
		last_name="Smith",
		full_name="Jane Smith",
		user_image="/assets/lms/images/student2.jpeg",
	)
	demo_student = create_user(
		email=DEMO_LEARNER_EMAIL,
		first_name="Pramitya",
		last_name="Learner",
		full_name="Pramitya Learner",
		user_image="/assets/lms/images/student.jpg",
	)
	set_demo_learner_password(demo_student)
	create_chapter(course)
	create_lessons(course)
	enroll_student_in_course(student, course)
	enroll_student_in_course(student1, course)
	enroll_student_in_course(student2, course)
	for sample_course in sample_courses:
		enroll_student_in_course(demo_student, sample_course)
	create_reviews(course, student)
	create_progress(course, student, 3)
	create_progress(course, student1, 2)
	create_progress(course, student2, 4)
	create_progress(course, demo_student)
	frappe.db.set_single_value("LMS Settings", "demo_data_present", 1)


SHOWCASE_USERS = [
	{
		"email": "instructor@pramitya.test",
		"first_name": "Isha",
		"last_name": "Menon",
		"full_name": "Isha Menon",
		"user_image": "/assets/lms/images/instructor.png",
		"roles": ["Moderator", "Course Creator", "Batch Evaluator"],
	},
	{
		"email": "evaluator@pramitya.test",
		"first_name": "Rahul",
		"last_name": "Nair",
		"full_name": "Rahul Nair",
		"user_image": "/assets/lms/images/instructor.png",
		"roles": ["Moderator", "Batch Evaluator"],
	},
	{
		"email": "mentor@pramitya.test",
		"first_name": "Nisha",
		"last_name": "Rao",
		"full_name": "Nisha Rao",
		"user_image": "/assets/lms/images/instructor.png",
		"roles": ["Moderator", "Course Creator"],
	},
	{
		"email": "arjun@pramitya.test",
		"first_name": "Arjun",
		"last_name": "Sharma",
		"full_name": "Arjun Sharma",
		"user_image": "/assets/lms/images/student1.jpeg",
		"roles": ["LMS Student"],
	},
	{
		"email": "meera@pramitya.test",
		"first_name": "Meera",
		"last_name": "Iyer",
		"full_name": "Meera Iyer",
		"user_image": "/assets/lms/images/student2.jpeg",
		"roles": ["LMS Student"],
	},
	{
		"email": "riya@pramitya.test",
		"first_name": "Riya",
		"last_name": "Kapoor",
		"full_name": "Riya Kapoor",
		"user_image": "/assets/lms/images/student.jpg",
		"roles": ["LMS Student"],
	},
]

SHOWCASE_SKILLS = [
	"Python",
	"JavaScript",
	"Data Analysis",
	"Cloud Deployment",
	"Product Thinking",
	"Interview Communication",
]
SHOWCASE_INDUSTRIES = ["Education", "Technology", "Analytics", "Cloud Services"]
SHOWCASE_FUNCTIONS = ["Software Engineering", "Data Analyst", "Product Management", "Teaching"]
SHOWCASE_SOURCES = ["Campus Drive", "Pramitya Demo", "Referral", "Workshop"]
SHOWCASE_BADGE_IMAGE = "/assets/lms/images/lms-logo.png"


def create_showcase_demo_data(args: dict = None):
	"""Create a richer end-to-end demo dataset for the hosted Pramitya app."""
	original_user = frappe.session.user
	frappe.session.user = "Administrator"
	try:
		create_demo_data(args)
		ensure_showcase_settings()
		ensure_showcase_reference_data()
		users = ensure_showcase_users()
		courses = get_showcase_courses()
		ensure_showcase_course_flags(courses, users)
		ensure_related_courses(courses)
		ensure_course_mentors(courses, users)
		assessments = ensure_showcase_assessments(courses)
		ensure_showcase_learning_activity(users, courses, assessments)
		batches = ensure_showcase_batches(users, courses, assessments)
		ensure_showcase_program(users, courses)
		ensure_showcase_ai_viva_sessions(users, courses)
		ensure_showcase_certificates(users, courses)
		ensure_showcase_credential_cases(users, courses)
		ensure_showcase_badges(users, courses)
		ensure_showcase_notes_and_discussions(users, courses)
		ensure_showcase_jobs(users)
		from lms.lms.unnati import seed_unnati_demo

		unnati_status = seed_unnati_demo()
		update_course_statistics()
		frappe.db.set_single_value("LMS Settings", "demo_data_present", 1)
		frappe.db.commit()
		status = get_showcase_demo_status()
		status["unnati"] = unnati_status
		return status
	finally:
		frappe.session.user = original_user or "Administrator"


def ensure_showcase_settings():
	settings = {
		"allow_guest_access": 1,
		"show_dashboard": 1,
		"show_courses": 1,
		"show_students": 1,
		"show_assessments": 1,
		"show_live_class": 1,
		"show_discussions": 1,
		"show_emails": 1,
		"courses": 1,
		"batches": 1,
		"jobs": 1,
		"statistics": 1,
		"notifications": 1,
		"programming_exercises": 1,
		"certifications": 1,
		"allow_job_posting": 1,
		"meta_description": "Pramitya demo LMS with AI Viva, courses, batches, assessments, certificates, and jobs.",
		"meta_keywords": "Pramitya, LMS, AI Viva, courses, batches, assessments",
	}
	for field, value in settings.items():
		if frappe.get_meta("LMS Settings").has_field(field):
			frappe.db.set_single_value("LMS Settings", field, value)


def ensure_showcase_reference_data():
	ensure_demo_categories()
	for skill in SHOWCASE_SKILLS:
		ensure_named_doc("User Skill", "skill", skill)
	for industry in SHOWCASE_INDUSTRIES:
		ensure_named_doc("Industry", "industry", industry)
	for function in SHOWCASE_FUNCTIONS:
		ensure_named_doc("Function", "function", function)
	for source in SHOWCASE_SOURCES:
		ensure_named_doc("LMS Source", "source", source)


def ensure_named_doc(doctype, fieldname, value):
	if frappe.db.exists(doctype, value) or frappe.db.exists(doctype, {fieldname: value}):
		return frappe.get_doc(doctype, value)
	doc = frappe.new_doc(doctype)
	doc.set(fieldname, value)
	doc.insert(ignore_permissions=True)
	return doc


def ensure_showcase_users():
	users = {}
	for spec in SHOWCASE_USERS:
		user = create_user(
			email=spec["email"],
			first_name=spec["first_name"],
			last_name=spec["last_name"],
			full_name=spec["full_name"],
			user_image=spec["user_image"],
			roles=spec["roles"],
		)
		user.user_image = spec["user_image"]
		user.enabled = 1
		user.save(ignore_permissions=True)
		ensure_user_roles(user, spec["roles"])
		set_demo_learner_password(user)
		users[spec["email"]] = frappe.get_doc("User", spec["email"])

	for existing in [
		"ash@ipp.com",
		"john.doe@example.com",
		"jane.smith@example.com",
		DEMO_LEARNER_EMAIL,
	]:
		if frappe.db.exists("User", existing):
			users[existing] = frappe.get_doc("User", existing)
			ensure_user_roles(users[existing], ["LMS Student"])
			if existing == DEMO_LEARNER_EMAIL:
				set_demo_learner_password(users[existing])

	return users


def ensure_user_roles(user, roles):
	current_roles = {row.role for row in user.roles}
	for role in roles:
		if role not in current_roles:
			user.add_roles(role)
	user.reload()


def get_showcase_courses():
	courses = {}
	for title in DEMO_COURSE_TITLES:
		name = frappe.db.get_value("LMS Course", {"title": title}, "name")
		if name:
			courses[title] = frappe.get_doc("LMS Course", name)
	return courses


def ensure_showcase_course_flags(courses, users):
	colors = ["Teal", "Cyan", "Amber", "Violet", "Green", "Orange", "Blue", "Pink"]
	for index, course in enumerate(courses.values()):
		course.reload()
		ensure_course_ai_viva(course)
		course.reload()
		course.published = 1
		course.published_on = course.published_on or nowdate()
		course.featured = 1 if index < 5 else 0
		course.enable_certification = 1
		course.card_gradient = colors[index % len(colors)]
		course.disable_self_learning = 0
		if not any(row.instructor == users["instructor@pramitya.test"].name for row in course.instructors):
			course.append("instructors", {"instructor": users["instructor@pramitya.test"].name})
		course.save(ignore_permissions=True)


def ensure_related_courses(courses):
	course_list = list(courses.values())
	for index, course in enumerate(course_list):
		course.reload()
		related = {row.course for row in course.related_courses}
		for related_course in [course_list[(index + 1) % len(course_list)], course_list[(index + 2) % len(course_list)]]:
			if related_course.name != course.name and related_course.name not in related:
				course.append("related_courses", {"course": related_course.name})
		course.save(ignore_permissions=True)


def ensure_course_mentors(courses, users):
	mentor = users["mentor@pramitya.test"]
	for course in courses.values():
		filters = {"course": course.name, "mentor": mentor.name}
		if frappe.db.exists("LMS Course Mentor Mapping", filters):
			continue
		doc = frappe.new_doc("LMS Course Mentor Mapping")
		doc.course = course.name
		doc.mentor = mentor.name
		doc.insert(ignore_permissions=True)


def ensure_showcase_assessments(courses):
	assessments = {}
	for title, course in courses.items():
		chapter = prepare_chapter(course, "Showcase Assessments")
		quiz = ensure_course_quiz(course, f"{title} Knowledge Check")
		assignment = ensure_course_assignment(course, f"{title} Reflection Task")
		quiz_lesson = ensure_assessment_lesson(course, chapter, f"{title} Quiz", "quiz", quiz.name)
		assignment_lesson = ensure_assessment_lesson(
			course, chapter, f"{title} Assignment", "assignment", assignment.name
		)
		frappe.db.set_value("LMS Quiz", quiz.name, {"lesson": quiz_lesson.name, "course": course.name})
		frappe.db.set_value("LMS Assignment", assignment.name, "course", course.name)
		exercise = None
		exercise_lesson = None
		if title == "Python Programming Primer":
			exercise = ensure_programming_exercise()
			exercise_lesson = ensure_assessment_lesson(
				course, chapter, "Python Function Coding Lab", "program", exercise.name
			)
		assessments[course.name] = {
			"quiz": quiz,
			"assignment": assignment,
			"exercise": exercise,
			"quiz_lesson": quiz_lesson,
			"assignment_lesson": assignment_lesson,
			"exercise_lesson": exercise_lesson,
		}
	return assessments


def ensure_course_quiz(course, title):
	if frappe.db.exists("LMS Quiz", {"title": title}):
		return frappe.get_doc("LMS Quiz", {"title": title})

	questions = [
		(
			f"In {course.title}, what should a learner do before answering a viva question?",
			"State assumptions and answer clearly",
			1,
			"Skip the reasoning",
			0,
		),
		(
			f"Which signal shows progress in {course.title}?",
			"Completed lessons and passed assessments",
			1,
			"Only opening the course page",
			0,
		),
		(
			f"What makes a response strong in {course.title}?",
			"Evidence, examples, and a clear conclusion",
			1,
			"Long unrelated explanation",
			0,
		),
	]
	quiz = frappe.new_doc("LMS Quiz")
	quiz.title = title
	quiz.passing_percentage = 70
	quiz.max_attempts = 3
	quiz.show_answers = 1
	quiz.show_submission_history = 1
	quiz.shuffle_questions = 1
	for question in questions:
		quiz.append("questions", {"question": create_quiz_questions(*question).name, "marks": 5})
	quiz.save(ignore_permissions=True)
	return quiz


def ensure_course_assignment(course, title):
	if frappe.db.exists("LMS Assignment", {"title": title}):
		return frappe.get_doc("LMS Assignment", {"title": title})
	assignment = frappe.new_doc("LMS Assignment")
	assignment.update(
		{
			"title": title,
			"type": "Text",
			"course": course.name,
			"grade_assignment": 1,
			"show_answer": 1,
			"question": f"<p>Write a short demo reflection: what did you learn in <b>{course.title}</b>, and how would you apply it?</p>",
			"answer": "<p>A strong answer names one concept, one example, and one next action.</p>",
		}
	)
	assignment.insert(ignore_permissions=True)
	return assignment


def ensure_assessment_lesson(course, chapter, title, block_type, docname):
	data_key = "exercise" if block_type == "program" else block_type
	content = json.dumps(
		{
			"time": 1772450743148,
			"blocks": [
				{
					"id": frappe.generate_hash(length=10),
					"type": block_type,
					"data": {data_key: docname},
				}
			],
			"version": "2.29.0",
		}
	)
	lesson = create_lesson(course, chapter, title, content)
	if not lesson:
		lesson = frappe.get_doc("Course Lesson", {"course": course.name, "chapter": chapter.name, "title": title})
	return lesson


def ensure_programming_exercise():
	title = "Return the Largest Number"
	if frappe.db.exists("LMS Programming Exercise", {"title": title}):
		return frappe.get_doc("LMS Programming Exercise", {"title": title})
	exercise = frappe.new_doc("LMS Programming Exercise")
	exercise.title = title
	exercise.language = "Python"
	exercise.problem_statement = "<p>Write a function <code>largest(a, b)</code> that returns the larger of two numbers.</p>"
	exercise.append("test_cases", {"input": "2\n5", "expected_output": "5"})
	exercise.append("test_cases", {"input": "9\n4", "expected_output": "9"})
	exercise.insert(ignore_permissions=True)
	return exercise


def ensure_showcase_learning_activity(users, courses, assessments):
	learners = [
		users.get(DEMO_LEARNER_EMAIL),
		users.get("ash@ipp.com"),
		users.get("john.doe@example.com"),
		users.get("jane.smith@example.com"),
		users.get("arjun@pramitya.test"),
		users.get("meera@pramitya.test"),
		users.get("riya@pramitya.test"),
	]
	learners = [learner for learner in learners if learner]
	for course_index, course in enumerate(courses.values()):
		for learner_index, learner in enumerate(learners):
			enroll_student_in_course(learner, course)
			total_lessons = frappe.db.count("Course Lesson", {"course": course.name})
			if learner.name in (DEMO_LEARNER_EMAIL, "ash@ipp.com"):
				limit = None
			else:
				limit = max(1, min(total_lessons, total_lessons - ((learner_index + course_index) % 4)))
			create_progress(course, learner, limit=limit)
			if learner_index < 4:
				create_course_review(course, learner, 1 if learner_index == 1 else 0.8, course_index)
			create_lesson_note(course, learner, course_index, learner_index)

		assessment = assessments.get(course.name, {})
		for learner_index, learner in enumerate(learners[:5]):
			create_quiz_submission(assessment.get("quiz"), learner, correct=learner_index < 3)
			create_assignment_submission(
				assessment.get("assignment"),
				assessment.get("assignment_lesson"),
				learner,
				status="Pass" if learner_index < 3 else "Not Graded",
			)
			if assessment.get("exercise") and learner_index < 3:
				create_programming_exercise_submission(assessment["exercise"], learner, passed=learner_index < 2)


def create_course_review(course, learner, rating, seed_index):
	frappe.session.user = learner.name
	try:
		if frappe.db.exists("LMS Course Review", {"course": course.name, "owner": learner.name}):
			return
		review = frappe.new_doc("LMS Course Review")
		review.course = course.name
		review.rating = rating
		review.review = [
			"The lessons are clear and the AI Viva makes revision feel practical.",
			"The assessment flow helps me see exactly what I need to improve.",
			"Good mix of concepts, examples, and practice tasks for a demo.",
		][seed_index % 3]
		review.insert(ignore_permissions=True)
	finally:
		frappe.session.user = "Administrator"


def create_quiz_submission(quiz, learner, correct=True):
	if not quiz or frappe.db.exists("LMS Quiz Submission", {"quiz": quiz.name, "member": learner.name}):
		return
	original_user = frappe.session.user
	frappe.session.user = learner.name
	try:
		results = []
		quiz.reload()
		for row in quiz.questions:
			question = frappe.get_doc("LMS Question", row.question)
			answer = get_question_answer(question, correct)
			results.append({"question_name": question.name, "answer": [answer]})
		submit_quiz(quiz.name, json.dumps(results))
	except MaximumAttemptsExceededError:
		pass
	finally:
		frappe.session.user = original_user or "Administrator"


def get_question_answer(question, correct=True):
	correct_options = []
	incorrect_options = []
	for index in range(1, 5):
		option = question.get(f"option_{index}")
		if not option:
			continue
		if question.get(f"is_correct_{index}"):
			correct_options.append(option)
		else:
			incorrect_options.append(option)
	return (correct_options if correct else incorrect_options or correct_options)[0]


def create_assignment_submission(assignment, lesson, learner, status="Pass"):
	if not assignment or not lesson:
		return
	if frappe.db.exists("LMS Assignment Submission", {"assignment": assignment.name, "member": learner.name}):
		return
	submission = frappe.new_doc("LMS Assignment Submission")
	submission.update(
		{
			"assignment": assignment.name,
			"assignment_title": assignment.title,
			"type": assignment.type,
			"member": learner.name,
			"lesson": lesson.name,
			"answer": f"<p>{learner.full_name} demo submission for {assignment.title}. I learned the core workflow and one practical application.</p>",
			"status": status,
			"comments": "Seeded demo evaluation: clear, concise, and ready for review.",
		}
	)
	submission.insert(ignore_permissions=True)


def create_programming_exercise_submission(exercise, learner, passed=True):
	if frappe.db.exists(
		"LMS Programming Exercise Submission", {"exercise": exercise.name, "member": learner.name}
	):
		return
	submission = frappe.new_doc("LMS Programming Exercise Submission")
	submission.update(
		{
			"exercise": exercise.name,
			"member": learner.name,
			"code": "def largest(a, b):\n    return a if a > b else b",
			"status": "Passed" if passed else "Failed",
		}
	)
	submission.insert(ignore_permissions=True)


def create_lesson_note(course, learner, course_index, learner_index):
	lesson = frappe.db.get_value("Course Lesson", {"course": course.name}, "name", order_by="creation asc")
	if not lesson:
		return
	filters = {
		"lesson": lesson,
		"member": learner.name,
		"highlighted_text": f"Demo highlight {course_index + 1}",
	}
	if frappe.db.exists("LMS Lesson Note", filters):
		return
	note = frappe.new_doc("LMS Lesson Note")
	note.update(
		{
			"lesson": lesson,
			"course": course.name,
			"member": learner.name,
			"color": ["Blue", "Green", "Yellow", "Purple"][learner_index % 4],
			"highlighted_text": filters["highlighted_text"],
			"note": f"<p>{learner.full_name} noted an important concept in {course.title}.</p>",
		}
	)
	note.insert(ignore_permissions=True)


def ensure_showcase_batches(users, courses, assessments):
	evaluator = ensure_course_evaluator(users["evaluator@pramitya.test"])
	batches = [
		ensure_showcase_batch(
			title="Pramitya AI Interviewer Bootcamp",
			description="A guided cohort for learners preparing to demonstrate the AI Viva workflow.",
			courses=[
				courses[PRIMARY_DEMO_COURSE_TITLE],
				courses["AI Interview Readiness"],
				courses["Communication for Placement Interviews"],
			],
			users=users,
			evaluator=evaluator,
			assessments=assessments,
			start_offset=1,
		),
		ensure_showcase_batch(
			title="Cloud and Python Weekend Lab",
			description="A weekend lab combining programming practice, deployment basics, and review tasks.",
			courses=[
				courses["Python Programming Primer"],
				courses["Cloud Deployment on Azure"],
				courses["Data Literacy Basics"],
			],
			users=users,
			evaluator=evaluator,
			assessments=assessments,
			start_offset=7,
		),
	]
	for batch in batches:
		for learner_email in [DEMO_LEARNER_EMAIL, "ash@ipp.com", "arjun@pramitya.test", "meera@pramitya.test"]:
			if users.get(learner_email):
				enroll_student_in_batch(users[learner_email], batch, users["instructor@pramitya.test"])
	return batches


def ensure_course_evaluator(user):
	if frappe.db.exists("Course Evaluator", user.name):
		return frappe.get_doc("Course Evaluator", user.name)
	evaluator = frappe.new_doc("Course Evaluator")
	evaluator.evaluator = user.name
	evaluator.unavailable_from = add_days(nowdate(), 21)
	evaluator.unavailable_to = add_days(nowdate(), 24)
	for day, start, end in [("Monday", "10:00:00", "12:00:00"), ("Wednesday", "14:00:00", "16:00:00")]:
		evaluator.append("schedule", {"day": day, "start_time": start, "end_time": end})
	evaluator.insert(ignore_permissions=True)
	return evaluator


def ensure_showcase_batch(title, description, courses, users, evaluator, assessments, start_offset):
	name = frappe.db.exists("LMS Batch", {"title": title})
	batch = frappe.get_doc("LMS Batch", name) if name else frappe.new_doc("LMS Batch")
	batch.update(
		{
			"title": title,
			"published": 1,
			"allow_self_enrollment": 1,
			"start_date": getdate(add_days(nowdate(), start_offset)),
			"end_date": getdate(add_days(nowdate(), start_offset + 28)),
			"start_time": "09:00:00",
			"end_time": "17:00:00",
			"timezone": "Asia/Kolkata",
			"seat_count": 30,
			"category": "Career" if "Interview" in title else "Cloud",
			"description": description,
			"batch_details": f"<p>{description}</p><p>This seeded batch includes courses, assessments, timetable rows, and enrollments.</p>",
			"evaluation": 1,
			"evaluation_end_date": getdate(add_days(nowdate(), start_offset + 35)),
			"medium": "Online",
			"show_live_class": 1,
		}
	)
	append_unique_child(batch, "instructors", "instructor", users["instructor@pramitya.test"].name)
	for course in courses:
		if not any(row.course == course.name for row in batch.courses):
			batch.append("courses", {"course": course.name, "evaluator": evaluator.name})
	for course in courses:
		assessment = assessments.get(course.name, {})
		if assessment.get("quiz"):
			append_unique_assessment(batch, "LMS Quiz", assessment["quiz"].name)
		if assessment.get("assignment"):
			append_unique_assessment(batch, "LMS Assignment", assessment["assignment"].name)
	append_batch_timetable(batch, courses, assessments, start_offset)
	append_unique_legend(batch, "Course Lesson", "Lessons", "#2563EB")
	append_unique_legend(batch, "LMS Quiz", "Quizzes", "#16A34A")
	append_unique_legend(batch, "LMS Assignment", "Assignments", "#EA580C")
	batch.save(ignore_permissions=True)
	return batch


def append_unique_child(doc, table_field, key, value, row=None):
	if any(child.get(key) == value for child in doc.get(table_field)):
		return
	payload = row or {key: value}
	doc.append(table_field, payload)


def append_unique_assessment(batch, assessment_type, assessment_name):
	if any(
		row.assessment_type == assessment_type and row.assessment_name == assessment_name
		for row in batch.assessment
	):
		return
	batch.append("assessment", {"assessment_type": assessment_type, "assessment_name": assessment_name})


def append_batch_timetable(batch, courses, assessments, start_offset):
	if batch.timetable and all(
		batch.start_date <= row.date <= batch.end_date for row in batch.timetable if row.date
	):
		return
	# Showcase dates move with each deployment; rebuild stale timetable rows so
	# re-seeding remains idempotent instead of failing batch validation.
	batch.set("timetable", [])
	for index, course in enumerate(courses[:4]):
		lesson = frappe.db.get_value("Course Lesson", {"course": course.name}, "name", order_by="creation asc")
		if lesson:
			batch.append(
				"timetable",
				{
					"reference_doctype": "Course Lesson",
					"reference_docname": lesson,
					"date": getdate(add_days(nowdate(), start_offset + index)),
					"start_time": "10:00:00",
					"end_time": "11:00:00",
					"duration": "60",
				},
			)
		assessment = assessments.get(course.name, {})
		if assessment.get("quiz"):
			batch.append(
				"timetable",
				{
					"reference_doctype": "LMS Quiz",
					"reference_docname": assessment["quiz"].name,
					"date": getdate(add_days(nowdate(), start_offset + index + 1)),
					"start_time": "14:00:00",
					"end_time": "15:00:00",
					"duration": "60",
					"milestone": 1,
				},
			)


def append_unique_legend(batch, reference_doctype, label, color):
	if any(row.reference_doctype == reference_doctype for row in batch.timetable_legends):
		return
	batch.append(
		"timetable_legends",
		{"reference_doctype": reference_doctype, "label": label, "color": color},
	)


def enroll_student_in_batch(learner, batch, acting_user):
	if frappe.db.exists("LMS Batch Enrollment", {"batch": batch.name, "member": learner.name}):
		return
	original_user = frappe.session.user
	frappe.session.user = acting_user.name
	try:
		enrollment = frappe.new_doc("LMS Batch Enrollment")
		enrollment.member = learner.name
		enrollment.batch = batch.name
		if frappe.db.exists("LMS Source", "Pramitya Demo"):
			enrollment.source = "Pramitya Demo"
		enrollment.insert(ignore_permissions=True)
	finally:
		frappe.session.user = original_user or "Administrator"


def ensure_showcase_program(users, courses):
	title = "Pramitya Career Launch Program"
	name = frappe.db.exists("LMS Program", {"title": title})
	program = frappe.get_doc("LMS Program", name) if name else frappe.new_doc("LMS Program")
	program.title = title
	program.published = 1
	program.enforce_course_order = 1
	for course in courses.values():
		append_unique_child(program, "program_courses", "course", course.name)
	for member in [DEMO_LEARNER_EMAIL, "ash@ipp.com", "arjun@pramitya.test", "meera@pramitya.test"]:
		if users.get(member):
			append_unique_child(program, "program_members", "member", users[member].name)
	program.save(ignore_permissions=True)
	return program


def ensure_showcase_certificates(users, courses):
	template = get_default_certificate_template()
	if not template:
		return
	for course in list(courses.values())[:4]:
		for learner_email in [DEMO_LEARNER_EMAIL, "ash@ipp.com"]:
			learner = users.get(learner_email)
			if not learner:
				continue
			create_progress(course, learner)
			if frappe.db.exists("LMS Certificate", {"course": course.name, "member": learner.name}):
				continue
			certificate = frappe.new_doc("LMS Certificate")
			certificate.update(
				{
					"course": course.name,
					"member": learner.name,
					"issue_date": nowdate(),
					"template": template,
					"published": 1,
				}
			)
			certificate.insert(ignore_permissions=True)


def ensure_showcase_credential_cases(users, courses):
	"""Keep one real proof valid and one intentionally changed for evaluator demos."""
	from lms.lms.credential import backfill_credential_proofs

	backfill_credential_proofs()
	member = users.get("ash@ipp.com")
	course = courses.get("Python Programming Primer")
	if not member or not course:
		return
	certificate = frappe.db.get_value(
		"LMS Certificate",
		{"member": member.name, "course": course.name},
		["name", "course_title"],
		as_dict=True,
	)
	if not certificate:
		return
	modified_title = f"{course.title} (edited demo)"
	if certificate.course_title != modified_title:
		# Direct DB update is intentional: it demonstrates how verification detects
		# a credential changed after its immutable proof was anchored.
		frappe.db.set_value(
			"LMS Certificate",
			certificate.name,
			"course_title",
			modified_title,
			update_modified=False,
		)


def ensure_showcase_badges(users, courses):
	badges = [
		(
			"Pramitya Course Finisher",
			"Awarded to learners who complete seeded Pramitya demo courses.",
			"LMS Enrollment",
			"member",
			"doc.progress >= 100",
			[DEMO_LEARNER_EMAIL, "ash@ipp.com"],
		),
		(
			"AI Viva Passed",
			"Awarded after a learner passes a seeded AI Viva session.",
			"LMS AI Viva Session",
			"member",
			"doc.passed == 1",
			["ash@ipp.com", "arjun@pramitya.test", "meera@pramitya.test"],
		),
	]
	for title, description, reference_doctype, user_field, condition, members in badges:
		badge = (
			frappe.get_doc("LMS Badge", title)
			if frappe.db.exists("LMS Badge", title)
			else frappe.new_doc("LMS Badge")
		)
		badge.update(
			{
				"title": title,
				"description": description,
				"image": SHOWCASE_BADGE_IMAGE,
				"reference_doctype": reference_doctype,
				"event": "New",
				"user_field": user_field,
				"condition": condition,
				"grant_only_once": 1,
				"enabled": 1,
			}
		)
		badge.save(ignore_permissions=True)
		badge_name = title
		for member in members:
			if users.get(member):
				assign_badge_if_missing(badge_name, users[member].name)


def assign_badge_if_missing(badge, member):
	if frappe.db.exists("LMS Badge Assignment", {"badge": badge, "member": member}):
		return
	badge_doc = frappe.get_doc("LMS Badge", badge)
	assignment = frappe.new_doc("LMS Badge Assignment")
	assignment.badge = badge
	assignment.member = member
	assignment.badge_image = badge_doc.image
	assignment.badge_description = badge_doc.description
	assignment.issued_on = nowdate()
	assignment.insert(ignore_permissions=True)


def ensure_showcase_ai_viva_sessions(users, courses):
	sessions = [
		("AI Interview Readiness", "ash@ipp.com", 86, 1),
		("Python Programming Primer", "john.doe@example.com", 58, 0),
		("Cloud Deployment on Azure", "arjun@pramitya.test", 78, 1),
		("Communication for Placement Interviews", "meera@pramitya.test", 64, 1),
	]
	for course_title, member_email, score, passed in sessions:
		course = courses.get(course_title)
		member = users.get(member_email)
		if not course or not member:
			continue
		if frappe.db.exists(
			"LMS AI Viva Session",
			{"course": course.name, "member": member.name, "status": "Completed"},
		):
			continue
		create_progress(course, member)
		doc = frappe.new_doc("LMS AI Viva Session")
		doc.update(
			{
				"course": course.name,
				"member": member.name,
				"status": "Completed",
				"passed": passed,
				"score": score,
				"started_at": now_datetime(),
				"completed_at": now_datetime(),
				"transcript": json.dumps(
					[
						{"role": "assistant", "content": f"Welcome to the {course.title} viva. Explain one key concept."},
						{"role": "user", "content": "I explained the concept with an example and a practical use case."},
						{"role": "assistant", "content": f"Good. EXACT_OUTPUT VIVA_SCORE:{score}"},
					]
				),
			}
		)
		doc.insert(ignore_permissions=True)


def ensure_showcase_notes_and_discussions(users, courses):
	if not frappe.db.exists("DocType", "Discussion Topic") or not frappe.db.exists(
		"DocType", "Discussion Reply"
	):
		return
	for course in list(courses.values())[:3]:
		lesson = frappe.db.get_value("Course Lesson", {"course": course.name}, "name", order_by="creation asc")
		if not lesson:
			continue
		topic = ensure_discussion_topic("Course Lesson", lesson, f"Questions about {course.title}")
		for member_email, reply in [
			("arjun@pramitya.test", "This lesson helped me understand what to revise before the AI Viva."),
			("meera@pramitya.test", "Can we get another example that connects this topic to placement interviews?"),
		]:
			member = users.get(member_email)
			if member:
				ensure_discussion_reply(topic, member, reply)


def ensure_discussion_topic(reference_doctype, reference_docname, title):
	name = frappe.db.exists(
		"Discussion Topic",
		{"reference_doctype": reference_doctype, "reference_docname": reference_docname, "title": title},
	)
	if name:
		return frappe.get_doc("Discussion Topic", name)
	topic = frappe.new_doc("Discussion Topic")
	topic.update(
		{
			"title": title,
			"reference_doctype": reference_doctype,
			"reference_docname": reference_docname,
		}
	)
	topic.insert(ignore_permissions=True)
	return topic


def ensure_discussion_reply(topic, member, reply):
	if frappe.db.exists("Discussion Reply", {"topic": topic.name, "owner": member.name, "reply": reply}):
		return
	original_user = frappe.session.user
	frappe.session.user = member.name
	try:
		doc = frappe.new_doc("Discussion Reply")
		doc.topic = topic.name
		doc.reply = reply
		doc.insert(ignore_permissions=True)
	finally:
		frappe.session.user = original_user or "Administrator"


def ensure_showcase_jobs(users):
	if not frappe.db.exists("DocType", "Job Opportunity"):
		return
	jobs = [
		{
			"job_title": "Junior Python Developer",
			"type": "Full Time",
			"work_mode": "Remote",
			"location": "Bengaluru",
			"country": "India",
			"description": "<p>Build learning workflows, API integrations, and course assessment tools for Pramitya Demo Labs.</p>",
		},
		{
			"job_title": "AI Interview Operations Intern",
			"type": "Contract",
			"work_mode": "Hybrid",
			"location": "Ahmedabad",
			"country": "India",
			"description": "<p>Review AI Viva transcripts, learner outcomes, and interview quality signals.</p>",
		},
	]
	for job in jobs:
		try:
			doc = ensure_job_opportunity(job)
			for applicant in [users.get("arjun@pramitya.test"), users.get("meera@pramitya.test")]:
				if applicant:
					ensure_job_application(doc, applicant)
		except Exception:
			frappe.log_error(frappe.get_traceback(), "Pramitya demo job seed skipped")


def ensure_job_opportunity(job):
	name = frappe.db.get_value("Job Opportunity", {"job_title": job["job_title"]}, "name")
	doc = frappe.get_doc("Job Opportunity", name) if name else frappe.new_doc("Job Opportunity")
	meta = frappe.get_meta("Job Opportunity")
	values = {
		"job_title": job["job_title"],
		"status": "Open",
		"company_name": "Pramitya Demo Labs",
		"company_website": "https://pramitya.westus2.cloudapp.azure.com/lms",
		"company_email_address": "careers@pramitya.test",
		"company_logo": "/assets/lms/images/lms-logo.png",
		"type": job["type"],
		"work_mode": job["work_mode"],
		"location": job["location"],
		"country": job["country"],
		"description": job["description"],
	}
	for field, value in values.items():
		if meta.has_field(field):
			doc.set(field, value)
	doc.save(ignore_permissions=True)
	return doc


def ensure_job_application(job, applicant):
	if not frappe.db.exists("DocType", "LMS Job Application"):
		return
	if frappe.db.exists("LMS Job Application", {"job": job.name, "user": applicant.name}):
		return
	application = frappe.new_doc("LMS Job Application")
	meta = frappe.get_meta("LMS Job Application")
	values = {
		"job": job.name,
		"user": applicant.name,
		"resume": "/assets/lms/images/course_card.jpeg",
	}
	for field, value in values.items():
		if meta.has_field(field):
			application.set(field, value)
	application.insert(ignore_permissions=True)


def get_showcase_demo_status():
	def count(doctype, filters=None):
		if not frappe.db.exists("DocType", doctype):
			return 0
		return frappe.db.count(doctype, filters or {})

	course_names = frappe.get_all(
		"LMS Course",
		filters={"title": ["in", DEMO_COURSE_TITLES]},
		fields=["name", "title", "enable_ai_viva", "enable_certification"],
		order_by="title asc",
	)
	return {
		"courses": course_names,
		"counts": {
			"courses": len(course_names),
			"lessons": count("Course Lesson", {"course": ["in", [c.name for c in course_names]]}),
			"quizzes": count("LMS Quiz", {"title": ["like", "%Knowledge Check%"]}),
			"assignments": count("LMS Assignment", {"title": ["like", "%Reflection Task%"]}),
			"batches": count("LMS Batch", {"title": ["in", ["Pramitya AI Interviewer Bootcamp", "Cloud and Python Weekend Lab"]]}),
			"programs": count("LMS Program", {"title": "Pramitya Career Launch Program"}),
			"certificates": count("LMS Certificate"),
			"badges": count("LMS Badge"),
			"ai_viva_sessions": count("LMS AI Viva Session"),
			"job_opportunities": count("Job Opportunity"),
		},
	}


def set_demo_learner_password(user):
	password = os.environ.get("PRAMITYA_DEMO_PASSWORD") or os.environ.get("DEMO_PASSWORD")
	if password:
		update_password(user.name, password)


def ensure_demo_categories():
	for category in DEMO_COURSE_CATEGORIES:
		if frappe.db.exists("LMS Category", category):
			continue
		doc = frappe.new_doc("LMS Category")
		doc.category = category
		doc.insert(ignore_permissions=True)


def ensure_course_ai_viva(course, instructions=DEMO_COURSE_AI_VIVA_INSTRUCTIONS):
	"""Turn on AI Viva for sample courses."""
	if course.title not in DEMO_COURSE_TITLES:
		return
	course.reload()
	changed = False
	if not cint(course.enable_ai_viva):
		course.enable_ai_viva = 1
		changed = True
	if not (course.ai_viva_instructions or "").strip():
		course.ai_viva_instructions = instructions
		changed = True
	if course.ai_viva_pass_score in (None, 0):
		course.ai_viva_pass_score = 60
		changed = True
	if not cint(course.ai_viva_max_attempts):
		course.ai_viva_max_attempts = 3
		changed = True
	if changed:
		course.save(ignore_permissions=True)


def ensure_demo_guide_ai_viva(course):
	"""Backward-compatible helper name for older setup scripts."""
	ensure_course_ai_viva(course)


def enable_ai_viva_on_guide_demo_course():
	"""One-off helper: bench execute lms.demo.demo_data.enable_ai_viva_on_guide_demo_course"""
	name = frappe.db.exists("LMS Course", "getting-started-with-pramitya")
	if not name:
		return {"ok": False, "reason": "LMS Course getting-started-with-pramitya not found"}
	doc = frappe.get_doc("LMS Course", "getting-started-with-pramitya")
	ensure_course_ai_viva(doc)
	frappe.db.commit()
	doc.reload()
	return {"ok": True, "name": doc.name, "enable_ai_viva": cint(doc.enable_ai_viva)}


def get_demo_course_status():
	return frappe.get_all(
		"LMS Course",
		fields=["title", "enable_ai_viva", "ai_viva_pass_score", "ai_viva_max_attempts"],
		filters={"title": ["in", DEMO_COURSE_TITLES]},
		order_by="title asc",
	)


def create_course():
	title = PRIMARY_DEMO_COURSE_TITLE
	filters = {"title": title}
	if frappe.db.exists("LMS Course", filters):
		course = frappe.get_doc("LMS Course", filters)
		ensure_course_ai_viva(course)
		return course

	instructor = create_instructor()
	course = frappe.new_doc("LMS Course")
	course.update(
		{
			"title": title,
			"category": "Business",
			"tags": "Pramitya, Demo",
			"published": 1,
			"published_on": frappe.utils.now(),
			"video_link": "VIt_bsbBjLI",
			"instructors": [{"instructor": instructor.name}],
			"short_introduction": "Learn the basics of Pramitya and how to get started with your first course.",
			"image": "/assets/lms/images/course_card.jpeg",
			"enable_ai_viva": 1,
			"ai_viva_pass_score": 60,
			"ai_viva_max_attempts": 3,
			"ai_viva_instructions": DEMO_COURSE_AI_VIVA_INSTRUCTIONS,
		}
	)

	course.description = """
		This course covers the fundamentals of Pramitya, including how to create and manage courses, enroll students, and track progress. You will learn about the following key features of the app:
		<br>
		<h3>Key Features</h3>
		<br>
		1. Structured Learning: Design a course with a 3-level hierarchy, where your courses have chapters, and you can group your lessons within these chapters. This ensures that the context of each lesson is clearly defined by its chapter.
		<br>
		<br>
		2. Live Classes: Group learners into batches based on courses and duration. You can then create Zoom live classes for these batches directly from the app. Learners can view all the live classes they need to attend as part of their batch.
		<br>
		<br>
		3. Quizzes and Assignments: Create quizzes with single-choice, multiple-choice, or open-ended questions. Instructors can also add assignments that learners can submit as PDFs or documents.
		<br>
		<br>
		4. Getting Certified: Once a learner completes the course or batch, you can grant them a certificate. The app provides an inbuilt certificate template that you can use as-is or customize by creating your own template.
 """
	course.save()
	return course


def create_sample_courses():
	courses = []
	for spec in SAMPLE_COURSE_SPECS:
		courses.append(create_sample_course(spec))
	return courses


def create_sample_course(spec):
	filters = {"title": spec["title"]}
	if frappe.db.exists("LMS Course", filters):
		course = frappe.get_doc("LMS Course", filters)
		ensure_course_ai_viva(course, spec["ai_viva_instructions"])
		ensure_sample_course_structure(course, spec)
		return course

	instructor = create_instructor()
	course = frappe.new_doc("LMS Course")
	course.update(
		{
			"title": spec["title"],
			"category": spec["category"],
			"tags": spec["tags"],
			"published": 1,
			"published_on": frappe.utils.now(),
			"instructors": [{"instructor": instructor.name}],
			"short_introduction": spec["short_introduction"],
			"description": spec["description"],
			"image": "/assets/lms/images/course_card.jpeg",
			"enable_ai_viva": 1,
			"ai_viva_pass_score": 60,
			"ai_viva_max_attempts": 3,
			"ai_viva_instructions": spec["ai_viva_instructions"],
		}
	)
	course.save()
	ensure_sample_course_structure(course, spec)
	return course


def ensure_sample_course_structure(course, spec):
	for chapter_spec in spec["chapters"]:
		chapter = prepare_chapter(course, chapter_spec["title"])
		if not chapter:
			chapter = get_chapter(course, chapter_spec["title"])
		for lesson_title, lesson_text in chapter_spec["lessons"]:
			content = json.dumps(
				{
					"time": 1772450743148,
					"blocks": [
						{
							"id": frappe.generate_hash(length=10),
							"type": "paragraph",
							"data": {"text": lesson_text},
						}
					],
					"version": "2.29.0",
				}
			)
			create_lesson(course, chapter, lesson_title, content)


def create_instructor():
	if (
		frappe.db.count(
			"User",
			{
				"name": ["not in", ("Administrator", "Guest")],
			},
		)
		> 0
	):
		user = frappe.get_all(
			"User",
			{
				"name": ["not in", ("Administrator", "Guest")],
			},
			pluck="name",
			limit=1,
		)[0]
		instructor = frappe.get_doc("User", user)
		instructor.user_image = "/assets/lms/images/instructor.png"
		instructor.add_roles("Moderator")
		instructor.save()
		return instructor

	return create_user(
		email="jannat@example.com",
		first_name="Jannat",
		last_name="Patel",
		user_image="/assets/lms/images/instructor.png",
		roles=["Moderator"],
	)


def create_chapter(course):
	prepare_chapter(course, "Introduction")
	prepare_chapter(course, "Adding content to your lessons")
	prepare_chapter(course, "Assessments")


def prepare_chapter(course, chapter_title):
	chapter_exists = check_if_chapter_exists(course, chapter_title)
	if chapter_exists:
		return frappe.get_doc("Course Chapter", chapter_exists)

	chapter1 = frappe.new_doc("Course Chapter")
	chapter1.course = course.name
	chapter1.title = chapter_title
	chapter1.save()
	add_chapter_to_course(course, chapter1)
	return chapter1


def check_if_chapter_exists(course, chapter_title):
	filters = {"course": course.name, "title": chapter_title}
	return frappe.db.exists("Course Chapter", filters)


def add_chapter_to_course(course, chapter):
	course.reload()
	course.append("chapters", {"chapter": chapter.name})
	course.save()


def create_lessons(course):
	create_intro_lesson_1(course)
	create_intro_lesson_2(course)
	create_content_lesson_1(course)
	create_content_lesson_2(course)
	create_assessment_lesson_1(course)


def get_chapter(course, chapter_title):
	filters = {"course": course.name, "title": chapter_title}
	return frappe.get_doc("Course Chapter", filters)


def create_lesson(course, chapter, title, content):
	filters = {"course": course.name, "chapter": chapter.name, "title": title}

	if frappe.db.exists("Course Lesson", filters):
		return frappe.get_doc("Course Lesson", filters)

	lesson = frappe.new_doc("Course Lesson")
	lesson.course = course.name
	lesson.chapter = chapter.name
	lesson.title = title
	lesson.content = content
	lesson.save()
	add_lesson_to_chapter(chapter, lesson)
	return lesson


def add_lesson_to_chapter(chapter, lesson):
	chapter.reload()
	chapter.append("lessons", {"lesson": lesson.name})
	chapter.save()


def create_intro_lesson_1(course):
	title = "What are Learning Management Systems?"
	chapter = get_chapter(course, "Introduction")
	content = """
		{"time":1772449622100,"blocks":[{"id":"vYTdcXYVgI","type":"embed","data":{"service":"youtube","source":"https://www.youtube.com/watch?v=QhA4h6qD4wY","embed":"QhA4h6qD4wY","caption":""}}],"version":"2.29.0"}
	"""
	create_lesson(course, chapter, title, content)


def create_intro_lesson_2(course):
	title = "What is Pramitya?"
	chapter = get_chapter(course, "Introduction")
	content = """
		{"time":1772449622100,"blocks":[{"id":"vYTdcXYVgI","type":"embed","data":{"service":"youtube","source":"https://www.youtube.com/watch?v=gFXVCWmVQvQ","embed":"gFXVCWmVQvQ","caption":""}}],"version":"2.29.0"}
	"""
	create_lesson(course, chapter, title, content)


def create_content_lesson_1(course):
	title = "Video Content"
	chapter = get_chapter(course, "Adding content to your lessons")
	content = json.dumps(get_video_content())
	create_lesson(course, chapter, title, content)


def create_content_lesson_2(course):
	title = "Content from Google Suite"
	chapter = get_chapter(course, "Adding content to your lessons")
	content = json.dumps(get_google_suite_content())
	create_lesson(course, chapter, title, content)


def create_assessment_lesson_1(course):
	quiz = create_quiz()
	title = "Quiz Time"
	chapter = get_chapter(course, "Assessments")
	content = f"""{{
		"time": 1770118649591,
		"blocks": [
			{{
				"id": "3xqARGZqQa",
				"type": "quiz",
				"data": {{ "quiz": "{quiz.name}" }}
			}}
		],
		"version": "2.29.0"
	}}"""
	create_lesson(course, chapter, title, content)


def create_quiz():
	title = "Do you know Pramitya?"
	filters = {"title": title}
	if frappe.db.exists("LMS Quiz", filters):
		return frappe.get_doc("LMS Quiz", filters)

	questions = []
	questions.append(
		create_quiz_questions(
			"What is Pramitya primarily used for?",
			"Project Management",
			False,
			"Learning Management",
			True,
		)
	)
	questions.append(
		create_quiz_questions(
			"Which of the following can be added to a course in Pramitya?",
			"Lessons",
			True,
			"Issues",
			False,
		)
	)
	questions.append(
		create_quiz_questions(
			"What is the top-level structure in Pramitya?", "Chapter", False, "Course", True
		)
	)
	questions.append(
		create_quiz_questions("Can you create quizzes in Pramitya?", "Yes", True, "No", False)
	)
	questions.append(
		create_quiz_questions(
			"Which of the following content can be added to lessons?", "Bugs", False, "Videos", True
		)
	)
	questions.append(
		create_quiz_questions("Can you track learner progress in Pramitya?", "Yes", True, "No", False)
	)
	questions.append(
		create_quiz_questions(
			"What is the purpose of a batch in Pramitya?",
			"To group learners",
			True,
			"To store website themes",
			False,
		)
	)
	questions.append(
		create_quiz_questions(
			"How can you create custom certificates in Pramitya?",
			"Using Server Scripts",
			False,
			"Using Print Formats",
			True,
		)
	)
	quiz = frappe.new_doc("LMS Quiz")
	quiz.update(
		{
			"title": title,
			"passing_percentage": 70,
			"total_marks": 40,
		}
	)
	for question in questions:
		quiz.append(
			"questions",
			{
				"question": question.name,
				"marks": 5,
			},
		)
	quiz.save()
	return quiz


def create_quiz_questions(question, option_1, is_correct_1, option_2, is_correct_2):
	doc = frappe.new_doc("LMS Question")
	doc.update(
		{
			"question": question,
			"type": "Choices",
			"option_1": option_1,
			"is_correct_1": is_correct_1,
			"option_2": option_2,
			"is_correct_2": is_correct_2,
		}
	)
	doc.save()
	return doc


def create_reviews(course, student):
	frappe.session.user = student.name
	try:
		if not frappe.db.exists("LMS Course Review", {"course": course.name, "owner": student.name}):
			review = frappe.new_doc("LMS Course Review")
			review.course = course.name
			review.rating = 0.8
			review.review = "This is a great course to get started with Pramitya. The content is well-structured and easy to follow."
			review.save()
	finally:
		frappe.session.user = "Administrator"
	update_course_statistics()


def enroll_student_in_course(student, course):
	filters = {"member": student.name, "course": course.name}
	if not frappe.db.exists("LMS Enrollment", filters):
		enrollment = frappe.new_doc("LMS Enrollment")
		enrollment.member = student.name
		enrollment.course = course.name
		enrollment.save()


def create_progress(course, student, limit=None):
	lessons = frappe.get_all(
		"Course Lesson", {"course": course.name}, pluck="name", limit=limit, order_by="creation asc"
	)
	for lesson in lessons:
		filters = {"member": student.name, "lesson": lesson, "course": course.name}
		if not frappe.db.exists("LMS Course Progress", filters):
			progress = frappe.new_doc("LMS Course Progress")
			progress.member = student.name
			progress.lesson = lesson
			progress.course = course.name
			progress.status = "Complete"
			progress.save()

	progress = get_course_progress(course.name, student.name)
	frappe.db.set_value(
		"LMS Enrollment", {"member": student.name, "course": course.name}, "progress", progress
	)


def get_video_content():
	return {
		"time": 1772450228627,
		"blocks": [
			{
				"id": "bj6mK0D36z",
				"type": "paragraph",
				"data": {
					"text": "Pramitya allows you to embed videos in lessons using popular video hosting platforms."
				},
			},
			{
				"id": "1ooWPn5Zmq",
				"type": "paragraph",
				"data": {
					"text": "You don't need to upload videos directly into Pramitya - simply copy the video URL from your preferred provider and paste it into the Lesson Editor."
				},
			},
			{
				"id": "tCJD0yMAGd",
				"type": "paragraph",
				"data": {
					"text": "Pramitya automatically detects the video source and embeds it for learners."
				},
			},
			{"id": "KpfuszbA09", "type": "markdown", "data": {"text": ""}},
			{"id": "PZYmdlzQj2", "type": "header", "data": {"text": "YouTube", "level": 2}},
			{
				"id": "mJsIbQSHYO",
				"type": "paragraph",
				"data": {"text": "YouTube videos can be embedded using the standard watch URL."},
			},
			{"id": "-H8fLBsAMk", "type": "paragraph", "data": {"text": "<b>Supported URL format</b>"}},
			{
				"id": "Aiq-BfQkwZ",
				"type": "paragraph",
				"data": {
					"text": '<code class="inline-code">https://www.youtube.com/watch?v=&lt;video-id&gt;</code>'
				},
			},
			{"id": "8hMi323AbM", "type": "paragraph", "data": {"text": "<b>Example</b>"}},
			{
				"id": "3H6BzIshWg",
				"type": "paragraph",
				"data": {
					"text": '<code class="inline-code">https://www.youtube.com/watch?v=SLNSSz41v_o</code>'
				},
			},
			{"id": "yGSuw7Im0i", "type": "markdown", "data": {"text": ""}},
			{"id": "WRVOABPAZO", "type": "header", "data": {"text": "Vimeo", "level": 2}},
			{
				"id": "AabHQjaQvo",
				"type": "paragraph",
				"data": {"text": "Vimeo videos are supported using the video URL."},
			},
			{"id": "q_9aNfNHEP", "type": "paragraph", "data": {"text": "<b>Supported URL format</b>"}},
			{
				"id": "1YYctmoyod",
				"type": "paragraph",
				"data": {"text": '<code class="inline-code">https://vimeo.com/&lt;video-id&gt;</code>'},
			},
			{"id": "OX_NGBxJTY", "type": "paragraph", "data": {"text": "<b>Example</b>"}},
			{
				"id": "KZYnrs_Dnf",
				"type": "paragraph",
				"data": {"text": '<code class="inline-code">https://vimeo.com/825334862</code>'},
			},
			{"id": "-mkC711EdF", "type": "markdown", "data": {"text": ""}},
			{"id": "nSzyGY6f68", "type": "header", "data": {"text": "Cloudflare Stream", "level": 2}},
			{
				"id": "-cpNtfvP5T",
				"type": "paragraph",
				"data": {"text": "Cloudflare Stream provides secure video hosting with adaptive streaming."},
			},
			{"id": "e2fQ-DG6Nd", "type": "paragraph", "data": {"text": "<b>Supported URL format</b>"}},
			{
				"id": "av_Q4P66hb",
				"type": "paragraph",
				"data": {
					"text": '<code class="inline-code">https://customer-&lt;account-id&gt;.cloudflarestream.com/&lt;video-id&gt;/watch</code>'
				},
			},
			{"id": "8KCsx40NpJ", "type": "paragraph", "data": {"text": "<b>Example</b>"}},
			{
				"id": "USi0pW91df",
				"type": "paragraph",
				"data": {
					"text": '<code class="inline-code">https://customer-f33zs165nr7gyfy4.cloudflarestream.com/6b9e68b07dfee8cc2d116e4c51d6a957/watch</code>'
				},
			},
			{"id": "e6I0VuwXx9", "type": "markdown", "data": {"text": ""}},
			{"id": "C-u44GnaTz", "type": "header", "data": {"text": "Bunny Stream", "level": 2}},
			{
				"id": "uR8XZtPVC5",
				"type": "paragraph",
				"data": {"text": "Bunny Stream allows fast, global video delivery with built-in analytics."},
			},
			{"id": "BYkm4Hy_v8", "type": "paragraph", "data": {"text": "<b>Supported URL format</b>"}},
			{
				"id": "TCM9COabp8",
				"type": "paragraph",
				"data": {
					"text": '<code class="inline-code">https://iframe.mediadelivery.net/play/&lt;library-id&gt;/&lt;video-id&gt;</code>'
				},
			},
			{"id": "KCiA6zVRYf", "type": "paragraph", "data": {"text": "<b>Example</b>"}},
			{
				"id": "kYDFL8Dn1v",
				"type": "paragraph",
				"data": {
					"text": '<code class="inline-code">https://iframe.mediadelivery.net/play/579970/54b3e5a1-cf95-4f88-96d3-8387d93dc2f2</code>'
				},
			},
			{"id": "jfnSgNAv5Q", "type": "markdown", "data": {"text": ""}},
			{"id": "NCY3opj8uc", "type": "header", "data": {"text": "Important Notes", "level": 2}},
			{
				"id": "xHWE56ECqw",
				"type": "paragraph",
				"data": {"text": "Paste only the video URL, not iframe embed code"},
			},
			{
				"id": "ZzrV99rSxJ",
				"type": "paragraph",
				"data": {"text": "The URL must match one of the supported formats above"},
			},
			{
				"id": "jjg_inGE2B",
				"type": "paragraph",
				"data": {
					"text": "Video privacy, access control, and streaming limits are managed by the video provider"
				},
			},
		],
		"version": "2.29.0",
	}


def get_google_suite_content():
	return {
		"time": 1772450743148,
		"blocks": [
			{
				"id": "73fFo3DS18",
				"type": "paragraph",
				"data": {
					"text": "You can integrate live Google Docs, Sheets, and Slides into your lessons to provide dynamic, up-to-date documentation and presentations."
				},
			},
			{"id": "Z6I1ZV7Fvr", "type": "markdown", "data": {"text": ""}},
			{
				"id": "hiJVoYEhfN",
				"type": "header",
				"data": {"text": "How to Embed Google Workspace Files", "level": 3},
			},
			{
				"id": "v9_hXM3d8b",
				"type": "list",
				"data": {
					"style": "ordered",
					"items": [
						{"content": "Open your Google Doc, Sheet, or Slide.", "items": []},
						{"content": "Make sure your permissions are set properly", "items": []},
						{"content": "Copy your URL from the top browser address bar", "items": []},
						{"content": "Now paste it in your lesson", "items": []},
					],
				},
			},
			{"id": "ycS1sd-0us", "type": "markdown", "data": {"text": ""}},
			{"id": "NjN6_ixXRW", "type": "header", "data": {"text": "Integration Options", "level": 3}},
			{
				"id": "MgXDT0xV4X",
				"type": "list",
				"data": {
					"style": "unordered",
					"items": [
						{
							"content": "Google Slides:&nbsp;Perfect for presentations. These render with full navigation controls for the student.",
							"items": [],
						},
						{
							"content": "Google Sheets:&nbsp;Useful for sharing live data tables or interactive calculators.",
							"items": [],
						},
						{
							"content": "Google Docs:&nbsp;Best for course handouts, reading material, or live-updating documentation.",
							"items": [],
						},
					],
				},
			},
		],
		"version": "2.29.0",
	}
