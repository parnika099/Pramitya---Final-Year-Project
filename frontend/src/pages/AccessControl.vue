<template>
	<div>
		<header
			class="sticky top-0 z-10 flex items-center justify-between border-b bg-surface-white px-3 py-2.5 sm:px-5"
		>
			<Breadcrumbs class="h-7" :items="breadcrumbs" />
		</header>
		<NoPermission v-if="!canManage" />
		<div v-else class="p-5">
			<div class="mb-5 grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
				<div
					v-for="item in directory.data?.hierarchy || []"
					:key="item.role"
					class="rounded-md border p-3"
				>
					<div class="font-semibold text-ink-gray-9">{{ __(item.role) }}</div>
					<div class="mt-1 text-xs text-ink-gray-5">{{ item.maps_to }}</div>
					<div class="mt-2 text-sm text-ink-gray-7">{{ __(item.summary) }}</div>
				</div>
			</div>
			<div class="mb-3 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
				<div class="text-lg font-semibold text-ink-gray-9">{{ __('People') }}</div>
				<div class="flex gap-2">
					<FormControl v-model="query" :placeholder="__('Name, username, or Student ID')" class="min-w-64" />
					<Button variant="solid" @click="load(1)">{{ __('Search') }}</Button>
				</div>
			</div>
			<div class="space-y-3">
				<div
					v-for="person in directory.data?.rows || []"
					:key="person.name"
					class="rounded-md border p-3"
				>
					<div class="flex flex-wrap items-center justify-between gap-2">
						<div>
							<div class="font-medium text-ink-gray-9">{{ person.full_name }}</div>
							<div class="text-xs text-ink-gray-5">
								{{ person.student_id || person.username }} · {{ person.access_level }}
							</div>
						</div>
						<div v-if="!person.can_edit" class="text-xs text-ink-gray-5">
							{{ __('Only a Super Admin can change this account.') }}
						</div>
					</div>
					<div class="mt-3 flex flex-wrap gap-2">
						<Button
							v-for="role in roles"
							:key="role.name"
							size="sm"
							:variant="person.roles.includes(role.name) ? 'solid' : 'subtle'"
							:disabled="!person.can_edit || saving === person.name + role.name"
							@click="toggleRole(person, role.name)"
						>
							{{ __(role.label) }}
						</Button>
					</div>
				</div>
			</div>
			<div class="mt-3 flex justify-end gap-2">
				<Button :disabled="page <= 1" @click="load(page - 1)">{{ __('Previous') }}</Button>
				<Button
					:disabled="page * 20 >= (directory.data?.total || 0)"
					@click="load(page + 1)"
				>
					{{ __('Next') }}
				</Button>
			</div>
			<div v-if="directory.data?.recent?.length" class="mt-6">
				<div class="mb-2 font-semibold text-ink-gray-9">
					{{ __('Recent role changes') }}
				</div>
				<div
					v-for="entry in directory.data.recent"
					:key="entry.creation + entry.subject"
					class="border-t py-2 text-sm text-ink-gray-7"
				>
					{{ entry.creation }} · {{ entry.actor }} · {{ entry.subject }}
				</div>
			</div>
		</div>
	</div>
</template>
<script setup>
import { computed, inject, ref } from 'vue'
import { Breadcrumbs, Button, FormControl, call, createResource, toast, usePageMeta } from 'frappe-ui'
import NoPermission from '@/components/NoPermission.vue'
import { sessionStore } from '@/stores/session'
import { errorMessage } from '@/utils/academic'

const user = inject('$user')
const { brand } = sessionStore()
const query = ref('')
const page = ref(1)
const saving = ref('')
const roles = [
	{ name: 'LMS Student', label: 'Student' },
	{ name: 'Course Creator', label: 'Faculty / Course Creator' },
	{ name: 'Batch Evaluator', label: 'Faculty / Evaluator' },
	{ name: 'Moderator', label: 'Admin' },
]
const canManage = computed(
	() => user.data?.is_moderator || user.data?.is_system_manager
)
const breadcrumbs = computed(() => [{ label: __('Access'), route: { name: 'AccessControl' } }])

const directory = createResource({
	url: 'lms.lms.academic.list_access_directory',
	makeParams() {
		return { query: query.value, page: page.value, page_size: 20 }
	},
	auto: canManage.value,
	onError(error) {
		toast.error(errorMessage(error))
	},
})

const load = (nextPage) => {
	page.value = nextPage
	directory.reload()
}

const toggleRole = async (person, role) => {
	const enabled = person.roles.includes(role)
	saving.value = person.name + role
	try {
		await call('lms.lms.api.save_role', {
			user: person.name,
			role,
			value: enabled ? 0 : 1,
		})
		toast.success(__('Role updated'))
		directory.reload()
	} catch (error) {
		toast.error(errorMessage(error))
	} finally {
		saving.value = ''
	}
}

usePageMeta(() => ({ title: __('Access'), icon: brand.favicon }))
</script>
