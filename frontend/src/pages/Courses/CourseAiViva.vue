<template>
	<div class="mx-auto max-w-2xl space-y-6 p-5">
		<router-link
			:to="{ name: 'CourseDetail', params: { courseName: props.courseName } }"
			class="text-sm text-ink-gray-7 hover:text-ink-gray-9"
		>
			← {{ __('Back to course') }}
		</router-link>
		<header class="space-y-1">
			<h1 class="text-2xl font-semibold text-ink-gray-9">
				{{ __('AI Viva — oral exam') }}
			</h1>
			<p v-if="courseTitle" class="text-ink-gray-7">{{ courseTitle }}</p>
		</header>

		<div
			v-if="eligibility.loading || (!eligibility.fetched && !eligibility.error)"
			class="rounded-lg border border-outline-gray-2 bg-surface-gray-2 p-4 text-ink-gray-8"
		>
			{{ __('Checking eligibility…') }}
		</div>

		<div
			v-else-if="eligibility.error"
			class="rounded-lg border border-red-200 bg-red-50 p-4 text-red-900"
		>
			{{
				eligibility.error?.messages?.[0] ||
				eligibility.error?.message ||
				String(eligibility.error)
			}}
		</div>

		<div
			v-else-if="eligibility.data?.eligible === false"
			class="rounded-lg border border-outline-gray-2 bg-surface-gray-2 p-4 text-ink-gray-8"
		>
			{{ eligibility.data.message || __('You cannot start the AI Viva right now.') }}
			<p v-if="eligibility.data.reason === 'login_required'" class="mt-3 text-sm">
				<a :href="loginHref" class="font-medium text-ink-brand hover:underline">{{
					__('Log in')
				}}</a>
			</p>
			<ul
				v-if="eligibility.data.reason !== 'login_required'"
				class="mt-3 list-inside list-disc text-sm"
			>
				<li>{{ __('Ensure the course enables AI Viva (course settings tab).') }}</li>
				<li>{{ __('You must be enrolled and at 100% course progress.') }}</li>
				<li>{{ __('If you failed before: you may retry until attempts run out.') }}</li>
			</ul>
		</div>

		<div v-else-if="eligibility.data?.eligible === true" class="space-y-4">
			<div
				v-if="eligibility.data?.developer_preview_waiver"
				class="rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-950"
			>
				{{
					__(
						'Developer preview: enrollment and completion rules are waived while developer_mode is on (Administrators / System Managers / Moderators). Turn off developer_mode on production.'
					)
				}}
			</div>
			<p class="text-sm text-ink-gray-7">
				{{
					__(
						'Allow microphone access. The interviewer will ask a few verbal questions about the course material. Speak clearly.'
					)
				}}
			</p>
			<p
				v-if="micPermissionMessage"
				class="rounded-md border border-outline-gray-2 bg-surface-gray-2 p-3 text-sm text-ink-gray-8"
			>
				{{ micPermissionMessage }}
			</p>

			<div v-if="errorMsg" class="text-sm text-red-600">{{ errorMsg }}</div>
			<div v-if="agentStatus" class="text-sm text-ink-gray-7">{{ agentStatus }}</div>
			<div v-if="resultMsg" class="rounded-md border border-green-200 bg-green-50 p-3 text-green-900">
				{{ resultMsg }}
			</div>

			<div
				class="rounded-lg border border-outline-gray-2 bg-surface-white p-4 shadow-sm space-y-4"
			>
				<div v-if="!liveSession && !hasExaminerScore" class="space-y-3">
					<h2 class="text-lg font-semibold text-ink-gray-9">
						{{ __('Start voice session') }}
					</h2>
					<button
						type="button"
						class="inline-flex min-h-10 min-w-[14rem] cursor-pointer appearance-none items-center justify-center rounded-md border border-transparent bg-ink-gray-9 px-4 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-ink-gray-8 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ink-gray-9 disabled:cursor-not-allowed disabled:opacity-70"
						:disabled="starting || submitting"
						@click.prevent.stop="begin"
					>
						{{ starting ? __('Starting...') : __('Connect microphone & begin') }}
					</button>
					<p class="text-sm text-ink-gray-7">
						{{
							deepgramLoaded
								? __('Tap the button above to connect to the voice interviewer.')
								: __(
										'The live voice panel will appear below after you connect. Your browser may ask for microphone access when you tap the button.'
									)
						}}
					</p>
				</div>

				<div v-if="bundle" class="flex flex-wrap gap-2">
					<Button v-if="liveSession" variant="subtle" :disabled="submitting" @click="disconnectAgent">
						{{ __('Stop microphone') }}
					</Button>
					<Button variant="solid" :disabled="!hasUserAnswer || !hasExaminerScore || starting" :loading="submitting" @click="submit">
						{{ __('Submit and score') }}
					</Button>
				</div>
				<p v-if="bundle && !hasExaminerScore" class="text-sm text-ink-gray-7">
					{{ __('Wait for the examiner’s final score before submitting. To finish early, ask the examiner to conclude and give your score.') }}
				</p>

				<deepgram-agent
					v-if="deepgramLoaded && sdkReady && bundle && liveSession"
					ref="agentRef"
					class="deepgram-agent-wrap"
					:url="bundle.websocket_url"
					auth-scheme="bearer"
					output-sample-rate="24000"
					height="220"
					width="220"
					idle-timeout-ms="180000"
				/>
				<p
					v-else-if="liveSession && deepgramLoaded && (!sdkReady || !bundle)"
					class="text-sm text-ink-gray-7"
				>
					{{ __('Connecting to the voice interviewer…') }}
				</p>
			</div>

			<div v-if="transcriptPreview.length" class="text-xs text-ink-gray-7">
				<p class="mb-2 font-semibold text-ink-gray-9">{{ __('Live transcript snippets') }}</p>
				<ul class="space-y-1 overflow-y-auto max-h-40">
					<li v-for="(line, i) in transcriptPreview" :key="i">
						<span class="font-medium">{{ line.role }}:</span>
						{{ line.text }}
					</li>
				</ul>
			</div>
		</div>

		<div
			v-else
			class="rounded-lg border border-outline-gray-2 bg-surface-gray-2 p-4 text-ink-gray-8"
		>
			{{
				__(
					'Could not read eligibility yet. Reload the page, or rebuild the LMS frontend (`bench build --app lms`) if routes are missing.'
				)
			}}
		</div>
	</div>
</template>

<script setup>
import { Button, call, createResource } from 'frappe-ui'
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getLmsRoute } from '@/utils/basePath'

const props = defineProps({
	courseName: { type: String, required: true },
})

const route = useRoute()
const router = useRouter()
const courseTitle = ref('')
const transcript = ref([])
const errorMsg = ref('')
const resultMsg = ref('')
const submitting = ref(false)
const agentStatus = ref('')

const sdkReady = ref(false)
const deepgramLoaded = ref(false)
const liveSession = ref(false)
const bundle = ref(null)
const agentRef = ref(null)
const micPermission = ref('unknown')
let micPermissionStatus = null
let disconnecting = null
let sessionGeneration = 0

const eligibility = createResource({
	url: 'lms.lms.api.ai_viva_eligibility',
	makeParams() {
		return { course: props.courseName }
	},
	auto: true,
})

const loginHref = computed(() => {
	const back = encodeURIComponent(
		getLmsRoute(`courses/${props.courseName}/ai-viva`)
	)
	return `/login?redirect-to=${back}`
})

const starting = ref(false)

const transcriptPreview = computed(() => {
	return transcript.value.filter((row) => row.text).slice(-20)
})

const hasUserAnswer = computed(() => {
	return transcript.value.some((row) => row.role === 'user' && row.text)
})

const hasExaminerScore = computed(() => {
	return transcript.value.some(
		(row) => row.role === 'assistant' && /VIVA_SCORE\s*:\s*\d+(?:\.\d+)?/i.test(row.content || row.text || '')
	)
})

const micPermissionMessage = computed(() => {
	if (micPermission.value === 'granted') {
		return __('Microphone permission is allowed for this site.')
	}
	if (micPermission.value === 'denied') {
		return __(
			'Microphone is blocked for this site. Open the browser site settings (lock/tune icon in the address bar), allow Microphone, then reload this page.'
		)
	}
	if (micPermission.value === 'prompt') {
		return __('Your browser should ask for microphone permission when you start the viva.')
	}
	return ''
})

watch(
	() => route.params.courseName,
	() => {
		sessionGeneration++
		void disconnectAgent()
		eligibility.reload()
		courseTitle.value = ''
		transcript.value = []
		errorMsg.value = ''
		resultMsg.value = ''
		agentStatus.value = ''
		liveSession.value = false
		bundle.value = null
	}
)

async function bootDeepgramUi() {
	if (!deepgramLoaded.value) {
		await import('@deepgram/browser-agent')
		deepgramLoaded.value = true
	}
}

async function ensureCourseMeta() {
	if (courseTitle.value) return
	const course = props.courseName
	const details = await call('lms.lms.utils.get_course_details', {
		course,
	})
	if (course === props.courseName) courseTitle.value = details?.title || ''
}

async function refreshMicPermission() {
	if (!navigator.permissions?.query) return micPermission.value
	try {
		micPermissionStatus = await navigator.permissions.query({
			name: 'microphone',
		})
		micPermission.value = micPermissionStatus.state
		micPermissionStatus.onchange = () => {
			micPermission.value = micPermissionStatus.state
		}
	} catch {
		micPermission.value = 'unknown'
	}
	return micPermission.value
}

function begin() {
	if (starting.value || submitting.value || liveSession.value) return
	const generation = ++sessionGeneration
	errorMsg.value = ''
	resultMsg.value = ''
	agentStatus.value = __('Requesting microphone access…')
	starting.value = true
	/* Browsers tie mic permission to a user gesture; awaiting network first lets that
	   expire, so `<deepgram-agent>` never triggers a prompt. Acquire audio here first. */
	if (!navigator.mediaDevices?.getUserMedia) {
		errorMsg.value = __(
			'Microphone is not available. Use HTTPS (or localhost) and a supported browser.'
		)
		starting.value = false
		return
	}

	// This must happen synchronously inside the native button click.
	// If permission is still in the "prompt" state, this exact call opens Chrome's mic popup.
	navigator.mediaDevices
		.getUserMedia({
			audio: true,
			video: false,
		})
		.then((stream) => {
			stream.getTracks().forEach((t) => t.stop())
			if (generation !== sessionGeneration) return
			micPermission.value = 'granted'
			agentStatus.value = __('Microphone is on. Connecting voice agent…')
			refreshMicPermission()
			return startDeepgramSession()
		})
		.catch(async (e) => {
			const denied =
				e?.name === 'NotAllowedError' || e?.name === 'PermissionDeniedError'
			await refreshMicPermission()
			if (denied) micPermission.value = 'denied'
			errorMsg.value = denied
				? __(
						'Microphone permission was denied. Allow it for this site in your browser settings, then tap Start again.'
					)
				: `${e?.name ? `${e.name}: ` : ''}${e?.message || String(e)}`
			starting.value = false
		})
}

async function startDeepgramSession() {
	const generation = sessionGeneration
	try {
		// Course details are display-only. Neither they nor the SDK download
		// should delay the independent access-token request.
		void ensureCourseMeta().catch(() => {})
		const [data] = await Promise.all([
			call('lms.lms.api.ai_viva_get_access', {
				course: props.courseName,
				ttl_seconds: 120,
			}),
			bootDeepgramUi(),
			disconnecting,
		])
		if (generation !== sessionGeneration) return
		transcript.value = []
		bundle.value = data
		sdkReady.value = true
		liveSession.value = true
		await nextTick()
		if (generation !== sessionGeneration) return
		const el = agentRef.value
		if (el && data.access_token && data.settings) {
			el.token = data.access_token
			for (const [event, handler] of Object.entries(agentEvents)) {
				el.addEventListener(event, handler)
			}
			// browser-agent 0.2.1 sends PCM from this context without resampling.
			// Its default rate is hardware-dependent (often 44.1kHz, not 48kHz).
			if (el.micContext?.sampleRate) {
				data.settings.audio.input.sample_rate = el.micContext.sampleRate
			}
			el.setAttribute('config', JSON.stringify(data.settings))
		}
	} catch (e) {
		if (generation !== sessionGeneration) return
		errorMsg.value = e?.messages?.[0] || e?.message || String(e)
		liveSession.value = false
		bundle.value = null
	} finally {
		if (generation === sessionGeneration) starting.value = false
	}
}

function onStructured(ev) {
	const msg = ev.detail
	if (!msg) return
	if (msg.type === 'Error') {
		errorMsg.value = msg.description || msg.message || __('The voice service could not continue. Please reconnect.')
		void disconnectAgent()
		return
	}
	if (msg.type === 'AgentThinking') {
		agentStatus.value = __('Preparing the next question…')
		return
	}
	if (msg.type === 'UserStartedSpeaking') {
		agentStatus.value = __('I can hear you speaking…')
		return
	}
	if (msg.type === 'AgentAudioDone') {
		agentStatus.value = __('Listening for your answer…')
		return
	}
	if (msg.type !== 'ConversationText') return
	agentStatus.value = msg.role === 'user' ? __('Heard your answer.') : __('Interviewer replied.')
	transcript.value.push({
			type: msg.type,
			role: msg.role,
			content: msg.content || msg.text || '',
			text: (msg.content || msg.text || '').trim(),
			ts: Date.now(),
		})
}

function onAgentOpen() {
	agentStatus.value = __('Voice agent connected. Speak when prompted.')
}

function onAgentErr(ev) {
	errorMsg.value = __('Voice agent connection error. Try reloading and ensure Deepgram billing is enabled.')
	console.error(ev)
	void disconnectAgent()
}

function onMicErr(ev) {
	micPermission.value = 'denied'
	errorMsg.value = __(
		'The voice agent could not access your microphone. Allow Microphone in browser site settings, reload, and tap Start again.'
	)
	console.error(ev)
	void disconnectAgent()
}

function onAgentWarn(ev) {
	console.warn('deepgram UNKNOWN', ev)
}

function onAgentClose() {
	if (!disconnecting) {
		agentStatus.value = __('Voice connection closed. You can submit a completed viva or reconnect.')
		void disconnectAgent()
	}
}

const agentEvents = {
	'structured message': onStructured,
	'socket open': onAgentOpen,
	'invalid auth': onAgentErr,
	'socket close': onAgentClose,
	'failed setup': onAgentErr,
	'connection timeout': onAgentErr,
	'failed to connect user media': onMicErr,
	'unknown message': onAgentWarn,
}

function disconnectAgent() {
	if (disconnecting) return disconnecting
	const el = agentRef.value
	for (const [event, handler] of Object.entries(agentEvents)) {
		el?.removeEventListener(event, handler)
	}
	// Removing config also calls disconnect in the SDK. Calling both races
	// socket cleanup and can leave the submit action waiting forever.
	disconnecting = Promise.resolve()
		.then(() => el?.disconnect?.())
		.catch((error) => console.warn('Voice cleanup failed', error))
		.finally(() => {
			liveSession.value = false
			agentStatus.value = ''
			disconnecting = null
		})
	return disconnecting
}

async function submit() {
	if (submitting.value || !bundle.value?.session) return
	if (!hasUserAnswer.value) {
		errorMsg.value = __('Please answer at least one viva question before submitting.')
		return
	}
	if (!hasExaminerScore.value) {
		errorMsg.value = __('Wait for the examiner to finish and give your score before submitting.')
		return
	}
	submitting.value = true
	errorMsg.value = ''
	try {
		await disconnectAgent()
		const res = await call('lms.lms.api.ai_viva_submit', {
			session: bundle.value.session,
			transcript: JSON.stringify(transcript.value),
		})
		bundle.value = null
		resultMsg.value = res.passed
			? `${__('Submitted.')} ${__('Passed.')} ${__('Score')}: ${res.score ?? '—'}. ${__('Pass threshold')}: ${res.pass_score}.`
			: `${__('Submitted.')} ${__('Score')}: ${res.score ?? __('not detected')} — ${__('below threshold')} ${res.pass_score}.`
		// A failed eligibility refresh must not turn a successful save into
		// a submission error and encourage duplicate attempts.
		void eligibility.reload().catch(() => {})
	} catch (e) {
		errorMsg.value = e?.messages?.[0] || e?.message || String(e)
	} finally {
		submitting.value = false
	}
}

onBeforeUnmount(async () => {
	sessionGeneration++
	await disconnectAgent()
	if (micPermissionStatus) micPermissionStatus.onchange = null
})

onMounted(() => {
	refreshMicPermission()
})
</script>

<style scoped>
.deepgram-agent-wrap {
	display: block;
	margin: 0 auto;
}
</style>
