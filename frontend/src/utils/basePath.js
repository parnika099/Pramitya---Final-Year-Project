const LMS_FIRST_SEGMENTS_AFTER_BASE = [
	'courses',
	'batches',
	'programs',
	'quizzes',
	'search',
	'statistics',
	'notifications',
	'billing',
	'certified-participants',
	'assignments',
	'programming-exercises',
	'data-import',
	'persona',
	'job-openings',
	'quiz',
	'quiz-submissions',
	'quiz-submission',
	'user',
	'job-opening',
	'assignment-submission',
	'assignment-submissions',
]

function normalizeSegment(value) {
	if (value === undefined || value === null || value === '') return ''
	const s = String(value).trim()
	return s.replace(/^\/+|\/+$/g, '')
}

/** Prevent using unreplaced Jinja or junk as the SPA base path. */
function isLikelyLmsSlug(segment) {
	if (!segment || segment.length > 128) return false
	return /^[a-zA-Z0-9_.-]+$/.test(segment)
}

/**
 * LMS is always mounted at /<mount>/courses/...
 * Prefer this over meta/boot so router base matches browser URL even if boot is stale.
 */
function deriveMountSegmentBeforeCourses(pathname = '') {
	const marker = '/courses/'
	const idx = pathname.indexOf(marker)
	if (idx < 1) {
		return ''
	}
	const before = pathname.slice(0, idx).replace(/^\/+|\/+$/g, '')
	const parts = before.split('/').filter(Boolean)
	return parts.length ? parts[parts.length - 1] : ''
}

/** Infer SPA base from pathname when meta/boot are unavailable (dev / script order edge cases). */
function inferBaseFromLocation() {
	if (typeof window === 'undefined') return ''
	const raw = window.location.pathname || ''
	const parts = raw.split('/').filter(Boolean)
	const first = parts[0]
	const second = parts[1]

	if (!first) return ''

	// SPA home at /<base>/ with no trailing segment handled by LMS route rules
	if (!second) return normalizeSegment(first)

	if (LMS_FIRST_SEGMENTS_AFTER_BASE.includes(second)) {
		return normalizeSegment(first)
	}

	return ''
}

export function getLmsBasePath() {
	if (typeof window !== 'undefined') {
		const fromUrlMount = deriveMountSegmentBeforeCourses(window.location.pathname || '')
		if (fromUrlMount && isLikelyLmsSlug(fromUrlMount)) {
			return fromUrlMount
		}
	}

	if (typeof document !== 'undefined') {
		const el = document.querySelector('meta[name="lms-path"]')
		const fromMeta = el?.getAttribute('content')
		const m = normalizeSegment(fromMeta)
		if (m && isLikelyLmsSlug(m)) return m
	}

	if (typeof window !== 'undefined' && window.lms_path !== undefined && window.lms_path !== '') {
		const fromBoot = normalizeSegment(window.lms_path)
		if (fromBoot && isLikelyLmsSlug(fromBoot)) return fromBoot
	}

	const inferred = inferBaseFromLocation()
	if (inferred && isLikelyLmsSlug(inferred)) return inferred

	return 'lms'
}

export function getLmsRoute(path = '') {
	const base = getLmsBasePath()
	if (!path) {
		return base
	}
	const normalized = path.startsWith('/') ? path.slice(1) : path
	return `/${base}/${normalized}`
}
