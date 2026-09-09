<template>
	<div class="min-h-screen bg-[#f3f5fa]">
		<InstitutionHeader />
		<main class="mx-auto flex max-w-3xl flex-col px-4 py-10 sm:py-16">
			<div class="institution-card overflow-hidden">
				<div class="border-b border-[#dce1ef] px-6 py-5 sm:px-8">
					<div class="flex items-center gap-3">
						<ShieldCheck class="size-7 text-[#303b78]" />
						<div><h1 class="text-xl font-semibold text-ink-gray-9">Credential verification</h1><p class="text-sm text-ink-gray-6">Unnati institutional proof ledger</p></div>
					</div>
				</div>
				<div v-if="verification.loading" class="p-10 text-center text-ink-gray-6">Checking the proof chain…</div>
				<div v-else-if="verification.data" class="p-6 sm:p-8">
					<div class="rounded-lg border p-5" :class="statusStyle.panel">
						<div class="flex items-start gap-3">
							<component :is="statusStyle.icon" class="mt-0.5 size-6 shrink-0" />
							<div><h2 class="text-lg font-semibold">{{ verification.data.title }}</h2><p class="mt-1 text-sm leading-6">{{ verification.data.message }}</p></div>
						</div>
					</div>
					<dl v-if="verification.data.credential" class="mt-6 divide-y divide-[#e6e9f2] rounded-lg border border-[#dce1ef]">
						<div v-for="row in credentialRows" :key="row.label" class="grid grid-cols-[120px_1fr] gap-4 px-4 py-3 text-sm sm:grid-cols-[160px_1fr]"><dt class="text-ink-gray-6">{{ row.label }}</dt><dd class="font-medium text-ink-gray-9">{{ row.value || '—' }}</dd></div>
					</dl>
					<div v-if="verification.data.proof" class="mt-6 rounded-lg bg-[#f7f8fc] p-4 text-xs text-ink-gray-6">
						<div class="mb-2 font-semibold text-ink-gray-8">Proof details</div>
						<div class="grid gap-2 sm:grid-cols-2"><span>Block #{{ verification.data.proof.chain_index }}</span><span>{{ verification.data.proof.contract_version }}</span></div>
						<div class="mt-3 break-all font-mono">{{ verification.data.proof.block_hash }}</div>
					</div>
					<div class="mt-6 flex flex-wrap gap-3">
						<router-link v-if="isLoggedIn" :to="{ name: 'CredentialTrust' }" class="institution-button">View trust dashboard</router-link>
						<router-link :to="{ name: 'Courses' }" class="inline-flex items-center rounded-lg border border-[#cbd2e8] px-4 py-2 text-sm font-semibold text-[#303b78]">Browse courses</router-link>
					</div>
				</div>
			</div>
			<p class="mx-auto mt-5 max-w-xl text-center text-xs leading-5 text-ink-gray-5">This public result intentionally hides email addresses, internal member IDs, AI transcripts, prompts, and answers.</p>
		</main>
	</div>
</template>

<script setup>
import { computed, markRaw } from 'vue'
import { createResource, usePageMeta } from 'frappe-ui'
import { CircleAlert, CircleCheck, ShieldX } from 'lucide-vue-next'
import InstitutionHeader from '@/components/InstitutionHeader.vue'
import { sessionStore } from '@/stores/session'

const props = defineProps({ token: { type: String, required: true } })
const { isLoggedIn } = sessionStore()
const verification = createResource({ url: 'lms.lms.credential.verify_credential', params: { token: props.token }, auto: true })

const statusStyle = computed(() => ({
	genuine: { panel: 'border-green-200 bg-green-50 text-green-900', icon: markRaw(CircleCheck) },
	modified: { panel: 'border-amber-200 bg-amber-50 text-amber-900', icon: markRaw(CircleAlert) },
	fraudulent: { panel: 'border-red-200 bg-red-50 text-red-900', icon: markRaw(ShieldX) },
}[verification.data?.status] || { panel: 'border-gray-200 bg-gray-50', icon: markRaw(CircleAlert) }))

const credentialRows = computed(() => {
	const item = verification.data?.credential || {}
	return [
		{ label: 'Credential ID', value: item.id },
		{ label: 'Learner', value: item.learner },
		{ label: 'Course or batch', value: item.course },
		{ label: 'Issuer', value: item.issuer },
		{ label: 'Issued on', value: item.issue_date },
	]
})

usePageMeta(() => ({ title: 'Verify Credential' }))
</script>
