<template>
	<div class="mt-7 mb-10">
		<h2 class="mb-3 text-lg font-semibold text-ink-gray-9">
			{{ __('Certificates') }}
		</h2>
		<div
			v-if="certificates.data?.length"
			class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
		>
			<div
				v-for="certificate in certificates.data"
				:key="certificate.name"
				class="flex flex-col bg-surface-white border rounded-lg p-3 cursor-pointer hover:bg-surface-menu-bar"
				@click="openCertificate(certificate)"
			>
				<div class="flex gap-3">
					<div class="min-w-0 flex-1">
						<div class="font-medium leading-5 mb-2 text-ink-gray-9">
							{{ certificate.course_title || certificate.batch_title }}
						</div>
						<div class="text-sm text-ink-gray-7 font-medium mt-auto">
							<span> {{ __('Issued on') }}: </span>
							{{ dayjs(certificate.issue_date).format('DD MMM YYYY') }}
						</div>
						<button
							v-if="proofs.data?.[certificate.name]"
							class="mt-3 text-sm font-semibold text-[#303b78] hover:underline"
							@click.stop="openVerification(certificate.name)"
						>
							{{ __('Verify credential') }}
						</button>
					</div>
					<img
						v-if="qrCodes[certificate.name]"
						:src="qrCodes[certificate.name]"
						:alt="__('Credential verification QR code')"
						class="size-20 shrink-0 rounded border bg-white p-1"
					/>
				</div>
			</div>
		</div>
		<div v-else class="text-sm italic text-ink-gray-5">
			{{ __('You have not received any certificates yet.') }}
		</div>
	</div>
</template>
<script setup>
import { createListResource, createResource } from 'frappe-ui'
import { inject, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import QRCode from 'qrcode'

const dayjs = inject('$dayjs')
const router = useRouter()
const qrCodes = ref({})
const props = defineProps({
	profile: {
		type: Object,
		required: true,
	},
})

onMounted(() => {
	if (props.profile.data?.name) {
		certificates.reload()
		proofs.fetch()
	}
})

const proofs = createResource({
	url: 'lms.lms.credential.get_certificate_proofs',
	makeParams() {
		return { member: props.profile.data?.name }
	},
	onSuccess: async (data) => {
		for (const [certificate, token] of Object.entries(data || {})) {
			const url = `${window.location.origin}/lms/verify/${token}`
			qrCodes.value[certificate] = await QRCode.toDataURL(url, {
				width: 140,
				margin: 1,
				color: { dark: '#303B78', light: '#FFFFFF' },
			})
		}
	},
})

const certificates = createListResource({
	doctype: 'LMS Certificate',
	filters: {
		member: props.profile.data?.name,
	},
	fields: ['name', 'course_title', 'batch_title', 'issue_date', 'template'],
	cache: ['certificates', props.profile.data?.name],
})

const openCertificate = (certificate) => {
	window.open(
		`/api/method/frappe.utils.print_format.download_pdf?doctype=LMS+Certificate&name=${
			certificate.name
		}&format=${encodeURIComponent(certificate.template)}`
	)
}

const openVerification = (certificate) => {
	const token = proofs.data?.[certificate]
	if (token) router.push({ name: 'CredentialVerify', params: { token } })
}
</script>
