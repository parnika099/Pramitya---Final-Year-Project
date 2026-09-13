<template>
	<div class="mx-auto w-full max-w-[1440px] px-4 py-6 sm:px-7 sm:py-8">
		<section class="overflow-hidden rounded-xl bg-[#303b78] text-white shadow-lg">
			<div class="grid gap-8 px-6 py-8 lg:grid-cols-[1.25fr_0.75fr] lg:px-10 lg:py-10">
				<div>
					<div class="mb-4 inline-flex items-center gap-2 rounded-full bg-white/10 px-3 py-1 text-sm">
						<ShieldCheck class="size-4" /> Credential trust demonstrator
					</div>
					<h1 class="max-w-3xl text-3xl font-semibold leading-tight sm:text-4xl">
						Measurable learning, portable proof
					</h1>
					<p class="mt-4 max-w-3xl text-base leading-7 text-blue-50/90">
						AI makes oral assessment repeatable at scale. The proof ledger makes an issued
						credential easy to check without publishing confidential student records.
					</p>
				</div>
				<div class="rounded-lg border border-white/15 bg-white/10 p-5 text-sm leading-6 text-blue-50">
					<div class="font-semibold text-white">Demonstration boundary</div>
					<p class="mt-2">
						This is a local, tamper-evident hash chain that demonstrates smart-contract
						policy and blockchain verification. It does not use cryptocurrency or publish
						student data to a public network.
					</p>
				</div>
			</div>
		</section>

		<section v-if="dashboard.loading" class="institution-card mt-5 p-8 text-center text-ink-gray-6">
			Loading credential evidence…
		</section>

		<template v-else-if="dashboard.data">
			<section class="mt-5 grid grid-cols-2 gap-3 lg:grid-cols-6">
				<div v-for="metric in metrics" :key="metric.label" class="institution-card p-4">
					<div class="text-sm text-ink-gray-6">{{ metric.label }}</div>
					<div class="mt-2 text-2xl font-semibold text-[#303b78]">{{ metric.value }}</div>
				</div>
			</section>

			<section class="institution-card mt-5 p-5 sm:p-7">
				<div class="flex flex-col justify-between gap-2 sm:flex-row sm:items-end">
					<div>
						<h2 class="text-xl font-semibold text-ink-gray-9">How the evidence moves</h2>
						<p class="mt-1 text-sm text-ink-gray-6">
							Each stage has one job; private source records stay inside the institution.
						</p>
					</div>
				</div>
				<div class="mt-6 flex snap-x gap-2 overflow-x-auto pb-2">
					<template v-for="(step, index) in architecture" :key="step.title">
						<div class="min-w-[160px] flex-1 snap-start rounded-lg border border-[#dce1ef] bg-[#f7f8fc] p-4">
							<component :is="step.icon" class="size-5 text-[#4559a6]" />
							<div class="mt-3 font-semibold text-ink-gray-9">{{ step.title }}</div>
							<div class="mt-1 text-xs leading-5 text-ink-gray-6">{{ step.text }}</div>
						</div>
						<ChevronRight v-if="index < architecture.length - 1" class="mt-12 size-4 shrink-0 text-[#7b86bd]" />
					</template>
				</div>
			</section>

			<section class="mt-5">
				<div class="mb-3">
					<h2 class="text-xl font-semibold text-ink-gray-9">Try the verification cases</h2>
					<p class="mt-1 text-sm text-ink-gray-6">
						These fixed cases make the evaluation repeatable without changing live data.
					</p>
				</div>
				<div class="grid gap-4 lg:grid-cols-3">
					<div v-for="item in cases" :key="item.status" class="institution-card flex gap-4 p-5">
						<img v-if="qrCodes[item.status]" :src="qrCodes[item.status]" :alt="`${item.label} credential QR code`" class="size-24 rounded border bg-white p-1" />
						<div class="min-w-0 flex-1">
							<div class="flex items-center gap-2">
								<span class="size-2.5 rounded-full" :class="item.dot"></span>
								<h3 class="font-semibold text-ink-gray-9">{{ item.label }}</h3>
							</div>
							<p class="mt-2 text-sm leading-5 text-ink-gray-6">{{ item.description }}</p>
							<router-link :to="{ name: 'CredentialVerify', params: { token: item.token } }" class="mt-3 inline-flex text-sm font-semibold text-[#303b78] hover:underline">
								Open verification
							</router-link>
						</div>
					</div>
				</div>
			</section>

			<section class="institution-card mt-5 overflow-hidden">
				<div class="border-b border-[#dce1ef] px-5 py-4">
					<h2 class="text-lg font-semibold text-ink-gray-9">Recent proof blocks</h2>
				</div>
				<div class="overflow-x-auto">
					<table class="w-full min-w-[760px] text-left text-sm">
						<thead class="bg-[#f3f5fa] text-ink-gray-6">
							<tr><th class="px-5 py-3">Block</th><th class="px-5 py-3">Certificate</th><th class="px-5 py-3">Credential hash</th><th class="px-5 py-3">Result</th></tr>
						</thead>
						<tbody>
							<tr v-for="proof in dashboard.data.proofs" :key="proof.block_hash" class="border-t border-[#e6e9f2]">
								<td class="px-5 py-3 font-medium">#{{ proof.chain_index }}</td>
								<td class="px-5 py-3">{{ proof.certificate }}</td>
								<td class="max-w-[260px] truncate px-5 py-3 font-mono text-xs text-ink-gray-6">{{ proof.credential_hash }}</td>
								<td class="px-5 py-3"><span class="rounded-full px-2 py-1 text-xs font-semibold" :class="proof.status === 'genuine' ? 'bg-green-100 text-green-800' : 'bg-amber-100 text-amber-800'">{{ proof.status }}</span></td>
							</tr>
						</tbody>
					</table>
				</div>
			</section>
		</template>
	</div>
</template>

<script setup>
import { computed, markRaw, ref } from 'vue'
import { createResource, usePageMeta } from 'frappe-ui'
import QRCode from 'qrcode'
import {
	Award,
	BarChart3,
	Blocks,
	Bot,
	ChevronRight,
	GraduationCap,
	QrCode,
	School,
	ShieldCheck,
	UserRound,
} from 'lucide-vue-next'

const qrCodes = ref({})
const dashboard = createResource({
	url: 'lms.lms.credential.get_credential_trust_dashboard',
	auto: true,
	onSuccess: async (data) => {
		for (const [status, item] of Object.entries(data.demo_cases || {})) {
			if (!item?.public_token) continue
			const url = `${window.location.origin}/lms/verify/${item.public_token}`
			qrCodes.value[status] = await QRCode.toDataURL(url, { width: 180, margin: 1, color: { dark: '#303B78', light: '#FFFFFF' } })
		}
	},
})

const metrics = computed(() => {
	const data = dashboard.data?.metrics || {}
	return [
		{ label: 'AI attempts', value: data.attempts || 0 },
		{ label: 'Completed', value: data.completed || 0 },
		{ label: 'Pass rate', value: `${data.pass_rate || 0}%` },
		{ label: 'Average score', value: data.average_score || 0 },
		{ label: 'Proof blocks', value: data.proofs || 0 },
		{ label: 'AI-linked proofs', value: data.ai_linked || 0 },
	]
})

const cases = computed(() => {
	const data = dashboard.data?.demo_cases || {}
	return [
		{ status: 'genuine', label: 'Genuine credential', description: 'Certificate data and every proof hash still match.', token: data.genuine?.public_token, dot: 'bg-green-500' },
		{ status: 'modified', label: 'Modified credential', description: 'A certificate field changed after the proof was anchored.', token: data.modified?.public_token || 'modified-demo-unavailable', dot: 'bg-amber-500' },
		{ status: 'fraudulent', label: 'Fraudulent credential', description: 'The supplied reference has never been anchored.', token: data.fraudulent?.public_token, dot: 'bg-red-500' },
	]
})

const architecture = [
	{ title: 'Student', text: 'Learns and completes an oral assessment.', icon: markRaw(UserRound) },
	{ title: 'Institution', text: 'Owns identity, enrollment and results.', icon: markRaw(School) },
	{ title: 'AI analytics', text: 'Measures attempts, scores and pass outcomes.', icon: markRaw(Bot) },
	{ title: 'Credential', text: 'Creates the institution-issued certificate.', icon: markRaw(Award) },
	{ title: 'Policy contract', text: 'Checks required fields and prevents duplicates.', icon: markRaw(ShieldCheck) },
	{ title: 'Proof ledger', text: 'Links hashes into a tamper-evident chain.', icon: markRaw(Blocks) },
	{ title: 'QR', text: 'Carries only an opaque verification reference.', icon: markRaw(QrCode) },
	{ title: 'Verifier', text: 'Receives a minimal genuine or warning result.', icon: markRaw(BarChart3) },
]

usePageMeta(() => ({ title: 'Credential Trust' }))
</script>
