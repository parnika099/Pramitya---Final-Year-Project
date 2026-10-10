<template>
	<div class="mx-auto max-w-lg space-y-4 p-6">
		<h1 class="text-xl font-semibold text-ink-gray-9">{{ __('Page not found') }}</h1>
		<p class="text-sm text-ink-gray-7">{{ __('Nothing matched this path in the LMS app.') }}</p>
		<code class="block break-all rounded border border-outline-gray-2 bg-surface-gray-2 p-3 text-xs text-ink-gray-8">
			{{ fullPath }}
		</code>
		<p class="text-xs text-ink-gray-7">
			{{ __('Open the LMS from Courses, or rebuild if you upgraded (`bench build --app lms`).') }}
		</p>
		<router-link
			class="inline-block text-sm text-ink-brand hover:underline"
			:to="{ name: 'Courses' }"
		>
			{{ __('Go to courses') }}
		</router-link>
	</div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const fullPath = computed(() => route.fullPath || route.path || '')
</script>
