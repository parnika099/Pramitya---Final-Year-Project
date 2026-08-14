import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { test } from 'node:test'
import { compileScript, parse } from '@vue/compiler-sfc'
import { transformSync } from 'esbuild'
import * as vue from 'vue'

// Compile the actual component so the lifecycle tests need neither a browser
// microphone nor a paid Deepgram connection.
const source = readFileSync(new URL('./CourseAiViva.vue', import.meta.url), 'utf8')
const { descriptor } = parse(source)
const compiled = transformSync(compileScript(descriptor, { id: 'viva-test' }).content, {
	format: 'cjs',
}).code

function setup(call = async () => ({})) {
	const lifecycle = {}
	const modules = {
		vue: {
			...vue,
			onMounted: (fn) => (lifecycle.mount = fn),
			onBeforeUnmount: (fn) => (lifecycle.unmount = fn),
			watch: () => {},
		},
		'frappe-ui': {
			Button: {},
			call,
			createResource: () => ({ reload: async () => {} }),
		},
		'vue-router': { useRoute: () => ({ params: {} }), useRouter: () => ({}) },
		'@/utils/basePath': { getLmsRoute: (path) => `/lms/${path}` },
	}
	const module = { exports: {} }
	new Function('require', 'module', 'exports', '__', compiled)(
		(name) => {
			assert.ok(modules[name], `Unexpected dependency: ${name}`)
			return modules[name]
		},
		module,
		module.exports,
		(text) => text
	)
	const state = module.exports.default.setup({ courseName: 'course-1' }, { expose() {} })
	return { state, lifecycle }
}

function fakeAgent() {
	const listeners = new Map()
	const calls = []
	return {
		calls,
		listeners,
		micContext: { sampleRate: 44100 },
		addEventListener: (name, handler) => listeners.set(name, handler),
		removeEventListener: (name) => listeners.delete(name),
		setAttribute(name, value) {
			calls.push([name, value])
			if (name === 'config') {
				listeners.get('structured message')?.({
					detail: { type: 'ConversationText', role: 'assistant', content: 'First question?' },
				})
			}
		},
		removeAttribute(name) {
			if (name === 'config') this.disconnect()
		},
		async disconnect() {
			calls.push(['disconnect'])
		},
	}
}

const scoredTranscript = [
	{ role: 'user', content: 'My answer', text: 'My answer' },
	{ role: 'assistant', content: 'VIVA_SCORE:80', text: 'VIVA_SCORE:80' },
]

test('startup does not wait for optional course metadata; listeners precede config', async () => {
	let resolveMetadata
	let requestedAccess = false
	const { state } = setup((method) => {
		if (method.endsWith('get_course_details')) {
			return new Promise((resolve) => (resolveMetadata = resolve))
		}
		requestedAccess = true
		return Promise.resolve({
			session: 'session-1',
			access_token: 'temporary-token',
			settings: { audio: { input: { sample_rate: 48000 } } },
		})
	})
	state.deepgramLoaded.value = true
	const agent = fakeAgent()
	state.agentRef.value = agent
	const starting = state.startDeepgramSession()
	await new Promise((resolve) => setImmediate(resolve))
	const accessWasConcurrent = requestedAccess
	resolveMetadata?.({ title: 'Test course' })
	await starting
	assert.equal(accessWasConcurrent, true, 'metadata must not delay the voice connection')
	assert.equal(state.transcript.value[0]?.content, 'First question?')
	const config = JSON.parse(agent.calls.find(([name]) => name === 'config')[1])
	assert.equal(config.audio.input.sample_rate, 44100, 'declare the actual microphone context rate')
})

test('disconnect is serialized and removes every event listener', async () => {
	const { state } = setup()
	const agent = fakeAgent()
	state.agentRef.value = agent
	for (const event of ['structured message', 'socket close', 'invalid auth', 'failed setup']) {
		agent.listeners.set(event, () => {})
	}
	await Promise.all([state.disconnectAgent(), state.disconnectAgent()])
	assert.equal(agent.calls.filter(([name]) => name === 'disconnect').length, 1)
	assert.equal(agent.listeners.size, 0)
})

test('submit without an examiner score keeps the session open', async () => {
	let submissions = 0
	const { state } = setup(async () => { submissions++; return {} })
	state.bundle.value = { session: 'session-1' }
	state.liveSession.value = true
	state.transcript.value = scoredTranscript.slice(0, 1)
	await state.submit()
	assert.equal(submissions, 0)
	assert.equal(state.liveSession.value, true)
	assert.match(state.errorMsg.value, /score|finish/i)
})

test('a failed score save preserves transcript and allows retry after stopping audio', async () => {
	let attempts = 0
	const { state } = setup(async () => {
		if (++attempts === 1) throw new Error('Temporary save failure')
		return { score: 80, passed: true, pass_score: 60 }
	})
	state.bundle.value = { session: 'session-1' }
	state.transcript.value = [...scoredTranscript]
	state.liveSession.value = false
	await state.submit()
	assert.equal(state.bundle.value.session, 'session-1')
	assert.deepEqual(state.transcript.value, scoredTranscript)
	assert.equal(state.submitting.value, false)
	await state.submit()
	assert.match(state.resultMsg.value, /80/)
	assert.equal(state.bundle.value, null, 'a saved attempt must not be submitted again')
})

test('a structured provider error is shown instead of leaving the viva silently stuck', () => {
	const { state } = setup()
	state.onStructured({ detail: { type: 'Error', description: 'The voice service is unavailable.' } })
	assert.match(state.errorMsg.value, /voice service is unavailable/)
})
