<template>
	<section class="institution-card mb-6 overflow-hidden">
		<div class="grid lg:grid-cols-[1.35fr_0.65fr]">
			<div class="bg-[#303b78] px-6 py-7 text-white sm:px-8">
				<div class="flex items-center gap-3">
					<img
						src="https://unnatidevelopment.in/logo.png"
						alt="Unnati Development Institute"
						class="h-12 w-auto rounded-md bg-white px-2 py-1"
					/>
					<span class="rounded-full border border-white/25 px-3 py-1 text-xs font-semibold uppercase tracking-wide">
						Student learning portal
					</span>
				</div>
				<h1 class="mt-5 max-w-3xl text-2xl font-semibold leading-tight sm:text-3xl">
					Build your career in Linux, Cloud & DevOps
				</h1>
				<p class="mt-3 max-w-3xl text-sm leading-6 text-blue-50/90 sm:text-base">
					Access practical labs, certification preparation, assessments, AI viva practice,
					verified credentials and placement-readiness support in one place.
				</p>
				<div class="mt-5 flex flex-wrap gap-3">
					<router-link :to="{ name: 'Courses' }" class="rounded-md bg-white px-4 py-2 text-sm font-semibold text-[#303b78]">
						Explore courses
					</router-link>
					<router-link :to="{ name: 'ExamCenter' }" class="rounded-md border border-white/30 px-4 py-2 text-sm font-semibold text-white">
						Open exam centre
					</router-link>
				</div>
			</div>
			<div class="grid grid-cols-2 gap-px bg-[#dce1ef]">
				<div v-for="item in highlights" :key="item.label" class="bg-white p-5">
					<component :is="item.icon" class="size-5 text-[#303b78]" />
					<div class="mt-3 font-semibold text-ink-gray-9">{{ item.label }}</div>
					<div class="mt-1 text-xs leading-5 text-ink-gray-6">{{ item.text }}</div>
				</div>
			</div>
		</div>
	</section>
</template>

<script setup>
import { markRaw } from 'vue'
import { Award, FlaskConical, Headphones, ShieldCheck } from 'lucide-vue-next'

const highlights = [
	{ label: 'Practical labs', text: 'Server, cloud and container practice.', icon: markRaw(FlaskConical) },
	{ label: 'Exam readiness', text: 'Mock tests and practical checkpoints.', icon: markRaw(Award) },
	{ label: 'Mentor support', text: 'Faculty-led doubt and review sessions.', icon: markRaw(Headphones) },
	{ label: 'Trusted proof', text: 'Privacy-safe verified credentials.', icon: markRaw(ShieldCheck) },
]
</script>
