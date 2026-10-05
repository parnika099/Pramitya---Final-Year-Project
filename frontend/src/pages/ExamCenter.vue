<template>
	<div class="mx-auto w-full max-w-[1440px] px-4 py-6 sm:px-7 sm:py-8">
		<section class="institution-card overflow-hidden">
			<div class="border-b border-[#dce1ef] bg-[#303b78] px-6 py-7 text-white sm:px-8">
				<div class="flex flex-col justify-between gap-5 lg:flex-row lg:items-end">
					<div><p class="text-sm font-semibold uppercase tracking-[0.14em] text-blue-100">Certification operations</p><h1 class="mt-2 text-3xl font-semibold">Exam Centre</h1><p class="mt-3 max-w-3xl leading-7 text-blue-50/90">Prepare, schedule, assess and verify practical certification readiness without exposing confidential learner records.</p></div>
					<router-link :to="{ name: 'CredentialTrust' }" class="w-fit rounded-md bg-white px-4 py-2 text-sm font-semibold text-[#303b78]">Credential trust dashboard</router-link>
				</div>
			</div>
			<div class="grid gap-px bg-[#dce1ef] sm:grid-cols-2 lg:grid-cols-4">
				<div v-for="item in capabilities" :key="item.label" class="bg-white p-5"><component :is="item.icon" class="size-5 text-[#303b78]" /><div class="mt-3 font-semibold">{{ item.label }}</div><div class="mt-1 text-xs leading-5 text-ink-gray-6">{{ item.text }}</div></div>
			</div>
		</section>

		<section v-if="exam.data?.operations || exam.data?.learner" class="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
			<div v-for="metric in dashboardMetrics" :key="metric.label" class="institution-card p-4"><div class="text-sm text-ink-gray-6">{{ metric.label }}</div><div class="mt-2 text-2xl font-semibold text-[#303b78]">{{ metric.value }}</div></div>
		</section>

		<section class="mt-7">
			<div class="mb-3"><h2 class="text-xl font-semibold">Certification pathways</h2><p class="mt-1 text-sm text-ink-gray-6">Course-to-exam mapping and practical readiness checklist.</p></div>
			<div class="grid gap-4 lg:grid-cols-2">
				<article v-for="track in exam.data?.tracks" :key="track.code" class="institution-card p-5">
					<div class="flex items-start justify-between gap-4"><div><div class="text-sm font-semibold text-[#4559a6]">{{ track.code }}</div><h3 class="mt-1 text-lg font-semibold text-ink-gray-9">{{ track.name }}</h3></div><ClipboardCheck class="size-6 shrink-0 text-[#303b78]" /></div>
					<div class="mt-3 rounded-md bg-[#f3f5fa] px-3 py-2 text-sm text-ink-gray-7">{{ track.course }}</div>
					<p class="mt-3 text-sm text-ink-gray-6">{{ track.format }}</p>
					<ul class="mt-4 grid gap-2 sm:grid-cols-3"><li v-for="item in track.readiness" :key="item" class="flex gap-2 text-xs leading-5 text-ink-gray-7"><CheckCircle2 class="mt-0.5 size-3.5 shrink-0 text-green-600" />{{ item }}</li></ul>
				</article>
			</div>
		</section>

		<section class="institution-card mt-7 p-6">
			<h2 class="text-xl font-semibold">Student exam workflow</h2>
			<div class="mt-5 grid gap-3 md:grid-cols-5">
				<div v-for="(step, index) in workflow" :key="step.title" class="relative rounded-lg border border-[#dce1ef] p-4"><div class="text-xs font-bold text-[#4559a6]">0{{ index + 1 }}</div><div class="mt-2 font-semibold">{{ step.title }}</div><p class="mt-1 text-xs leading-5 text-ink-gray-6">{{ step.text }}</p></div>
			</div>
		</section>
	</div>
</template>

<script setup>
import { computed, markRaw } from 'vue'
import { createResource, usePageMeta } from 'frappe-ui'
import { Bot, CheckCircle2, ClipboardCheck, FlaskConical, QrCode, ShieldCheck } from 'lucide-vue-next'

const exam = createResource({ url: 'lms.lms.unnati.get_exam_center', auto: true })

const capabilities = [
	{ label: 'Practical labs', text: 'Hands-on tasks aligned with the course pathway.', icon: markRaw(FlaskConical) },
	{ label: 'Mock tests', text: 'Repeatable knowledge and timing checks.', icon: markRaw(ClipboardCheck) },
	{ label: 'AI viva', text: 'Oral concept checks with measurable scores.', icon: markRaw(Bot) },
	{ label: 'Verified proof', text: 'QR-based, privacy-safe credential verification.', icon: markRaw(QrCode) },
]

const dashboardMetrics = computed(() => {
	const source = exam.data?.operations || exam.data?.learner || {}
	if (exam.data?.operations) return [
		{ label: 'Active students', value: source.active_students || 0 },
		{ label: 'Published courses', value: source.published_courses || 0 },
		{ label: 'Active batches', value: source.active_batches || 0 },
		{ label: 'Quiz attempts', value: source.quiz_attempts || 0 },
		{ label: 'Certificates', value: source.certificates || 0 },
	]
	return [
		{ label: 'My enrollments', value: source.enrollments || 0 },
		{ label: 'Quiz attempts', value: source.quiz_attempts || 0 },
		{ label: 'AI vivas', value: source.ai_vivas || 0 },
		{ label: 'Certificates', value: source.certificates || 0 },
	]
})

const workflow = [
	{ title: 'Enroll', text: 'Join the mapped course and batch.' },
	{ title: 'Practice', text: 'Complete lessons and guided labs.' },
	{ title: 'Assess', text: 'Take quizzes, assignments and viva.' },
	{ title: 'Review', text: 'Use faculty feedback and mock results.' },
	{ title: 'Verify', text: 'Issue and validate the final credential.' },
]

usePageMeta(() => ({ title: 'Unnati Exam Centre' }))
</script>
