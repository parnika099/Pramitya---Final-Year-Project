<template>
	<div class="mx-auto w-full max-w-[1440px] px-4 py-6 sm:px-7 sm:py-8">
		<section class="institution-card overflow-hidden">
			<div class="grid lg:grid-cols-[1.25fr_0.75fr]">
				<div class="bg-[#303b78] px-6 py-8 text-white sm:px-9 sm:py-10">
					<img :src="profile.data?.logo" alt="Unnati Development Institute" class="h-14 w-auto rounded-md bg-white px-3 py-2" />
					<p class="mt-6 text-sm font-semibold uppercase tracking-[0.14em] text-blue-100">Central India's Linux & Red Hat training institute</p>
					<h1 class="mt-2 text-3xl font-semibold leading-tight sm:text-4xl">{{ profile.data?.headline }}</h1>
					<p class="mt-4 max-w-3xl leading-7 text-blue-50/90">{{ profile.data?.description }}</p>
					<div class="mt-6 flex flex-wrap gap-3">
						<a :href="profile.data?.website" target="_blank" rel="noopener" class="rounded-md bg-white px-4 py-2 text-sm font-semibold text-[#303b78]">Official website</a>
						<a :href="profile.data?.whatsapp" target="_blank" rel="noopener" class="rounded-md border border-white/30 px-4 py-2 text-sm font-semibold">WhatsApp admissions</a>
					</div>
				</div>
				<div class="grid grid-cols-2 gap-px bg-[#dce1ef]">
					<div v-for="metric in profile.data?.metrics" :key="metric.label" class="bg-white p-6">
						<div class="text-2xl font-semibold text-[#303b78]">{{ metric.value }}</div>
						<div class="mt-1 text-sm text-ink-gray-6">{{ metric.label }}</div>
					</div>
				</div>
			</div>
		</section>

		<section class="mt-6 grid gap-6 xl:grid-cols-[0.75fr_1.25fr]">
			<div class="institution-card p-6">
				<div class="flex items-center gap-2"><BadgeCheck class="size-5 text-[#303b78]" /><h2 class="text-xl font-semibold">Training standards</h2></div>
				<ul class="mt-5 space-y-3">
					<li v-for="item in profile.data?.recognition" :key="item" class="flex gap-3 text-sm leading-6 text-ink-gray-7">
						<CheckCircle2 class="mt-0.5 size-4 shrink-0 text-green-600" />{{ item }}
					</li>
				</ul>
				<div class="mt-6 rounded-lg bg-[#f3f5fa] p-4 text-sm leading-6 text-ink-gray-7">
					<div class="font-semibold text-ink-gray-9">Admissions & learner support</div>
					<div class="mt-2">{{ profile.data?.phone }}</div>
					<div>{{ profile.data?.email }}</div>
					<div class="mt-1 text-xs">{{ profile.data?.hours }}</div>
				</div>
			</div>

			<div>
				<div class="mb-3 flex items-center gap-2"><UsersRound class="size-5 text-[#303b78]" /><h2 class="text-xl font-semibold">Faculty & mentors</h2></div>
				<div class="grid gap-4 md:grid-cols-2">
					<article v-for="person in profile.data?.faculty" :key="person.name" class="institution-card flex gap-4 p-5">
						<img :src="person.image" :alt="person.name" class="size-16 shrink-0 rounded-lg border border-[#dce1ef] object-cover" />
						<div><h3 class="font-semibold text-ink-gray-9">{{ person.name }}</h3><p class="mt-0.5 text-sm font-medium text-[#4559a6]">{{ person.role }}</p><p class="mt-2 text-xs leading-5 text-ink-gray-6">{{ person.experience }} · {{ person.specialties }}</p></div>
					</article>
				</div>
			</div>
		</section>

		<section class="mt-7">
			<div class="mb-3 flex items-center gap-2"><MapPin class="size-5 text-[#303b78]" /><h2 class="text-xl font-semibold">Campuses & support centres</h2></div>
			<div class="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
				<article v-for="campus in profile.data?.campuses" :key="campus.name" class="institution-card p-5">
					<div class="text-xs font-semibold uppercase tracking-wide text-[#4559a6]">{{ campus.city }}</div>
					<h3 class="mt-1 font-semibold text-ink-gray-9">{{ campus.name }}</h3>
					<p class="mt-2 text-sm leading-6 text-ink-gray-6">{{ campus.address }}</p>
					<p class="mt-3 text-sm font-medium text-ink-gray-8">{{ campus.phone }}</p>
				</article>
			</div>
		</section>
	</div>
</template>

<script setup>
import { createResource, usePageMeta } from 'frappe-ui'
import { BadgeCheck, CheckCircle2, MapPin, UsersRound } from 'lucide-vue-next'

const profile = createResource({ url: 'lms.lms.unnati.get_institute_profile', auto: true })
usePageMeta(() => ({ title: 'Unnati Development Institute' }))
</script>
