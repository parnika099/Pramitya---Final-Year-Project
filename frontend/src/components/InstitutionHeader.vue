<template>
	<header class="institution-header">
		<router-link :to="{ name: 'Home' }" class="institution-brand">
			<span class="institution-mark">
				<img src="https://unnatidevelopment.in/logo.png" alt="Unnati Development Institute" />
			</span>
			<span class="min-w-0">
				<span class="block truncate text-[15px] font-semibold leading-5 sm:text-lg">
					{{ brand.name || 'Unnati Development LMS' }}
				</span>
				<span class="hidden text-xs text-blue-100/80 sm:block">
					Linux, Cloud, DevOps & trusted credentials
				</span>
			</span>
		</router-link>
		<div v-if="userResource.data" class="hidden items-center gap-2 text-sm sm:flex">
			<span class="rounded-full bg-white/10 px-3 py-1.5">
				{{ userResource.data.full_name }}
			</span>
		</div>
		<router-link v-else :to="{ name: 'Courses' }" class="text-sm font-medium text-white">
			Explore courses
		</router-link>
	</header>
</template>

<script setup>
import { sessionStore } from '@/stores/session'
import { usersStore } from '@/stores/user'

const { brand } = sessionStore()
const { userResource } = usersStore()
</script>
