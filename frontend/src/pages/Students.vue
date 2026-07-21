<template>
	<div>
		<header
			class="sticky top-0 z-10 flex items-center justify-between border-b bg-surface-white px-3 py-2.5 sm:px-5"
		>
			<Breadcrumbs class="h-7" :items="breadcrumbs" />
		</header>
		<NoPermission v-if="!canView" />
		<div v-else class="p-5">
			<div class="mb-4 flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
				<div>
					<div class="text-lg font-semibold text-ink-gray-9">
						{{ __('Students') }}
					</div>
					<div class="text-sm text-ink-gray-6">
						{{ __('Search by Student ID, name, or username.') }}
					</div>
				</div>
				<div class="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-4">
					<FormControl v-model="query" :placeholder="__('Student ID or name')" />
					<FormControl v-model="batch" :placeholder="__('Batch ID')" />
					<FormControl v-model="department" :placeholder="__('Department')" />
					<Button variant="solid" @click="load(1)">{{ __('Search') }}</Button>
				</div>
			</div>
			<div v-if="result.loading" class="text-sm text-ink-gray-6">
				{{ __('Loading students...') }}
			</div>
			<div v-else class="overflow-x-auto rounded-md border">
				<table class="min-w-full text-left text-sm">
					<thead class="bg-surface-gray-1 text-ink-gray-7">
						<tr>
							<th class="px-3 py-2 font-medium">{{ __('Student ID') }}</th>
							<th class="px-3 py-2 font-medium">{{ __('Name') }}</th>
							<th class="px-3 py-2 font-medium">{{ __('Batch ID') }}</th>
							<th class="px-3 py-2 font-medium">{{ __('Department') }}</th>
							<th class="px-3 py-2 font-medium">{{ __('Year') }}</th>
							<th class="px-3 py-2 font-medium">{{ __('Semester') }}</th>
						</tr>
					</thead>
					<tbody>
						<tr v-if="!result.data?.rows?.length">
							<td colspan="6" class="px-3 py-6 text-center text-ink-gray-5">
								{{ __('No students found.') }}
							</td>
						</tr>
						<tr
							v-for="row in result.data?.rows || []"
							:key="row.student_id"
							class="border-t"
						>
							<td class="px-3 py-2 font-medium text-ink-gray-9">
								{{ row.student_id }}
							</td>
							<td class="px-3 py-2">
								<router-link
									v-if="row.username"
									class="text-ink-gray-9 underline"
									:to="{ name: 'Profile', params: { username: row.username } }"
								>
									{{ row.full_name }}
								</router-link>
								<span v-else>{{ row.full_name }}</span>
							</td>
							<td class="px-3 py-2">{{ row.batch_code || '—' }}</td>
							<td class="px-3 py-2">{{ row.department || '—' }}</td>
							<td class="px-3 py-2">{{ row.academic_year || '—' }}</td>
							<td class="px-3 py-2">{{ row.semester || '—' }}</td>
						</tr>
					</tbody>
				</table>
			</div>
			<div class="mt-3 flex items-center justify-between text-sm text-ink-gray-6">
				<span>{{ __('Total') }}: {{ result.data?.total || 0 }}</span>
				<div class="flex gap-2">
					<Button :disabled="page <= 1" @click="load(page - 1)">
						{{ __('Previous') }}
					</Button>
					<Button
						:disabled="page * (result.data?.page_size || 20) >= (result.data?.total || 0)"
						@click="load(page + 1)"
					>
						{{ __('Next') }}
					</Button>
				</div>
			</div>
		</div>
	</div>
</template>
<script setup>
import { computed, inject, ref } from 'vue'
import { Breadcrumbs, Button, FormControl, createResource, toast, usePageMeta } from 'frappe-ui'
import NoPermission from '@/components/NoPermission.vue'
import { sessionStore } from '@/stores/session'
import { errorMessage } from '@/utils/academic'

const user = inject('$user')
const { brand } = sessionStore()
const query = ref('')
const batch = ref('')
const department = ref('')
const page = ref(1)

const canView = computed(
	() =>
		user.data?.is_moderator ||
		user.data?.is_evaluator ||
		user.data?.is_instructor ||
		user.data?.is_system_manager
)

const breadcrumbs = computed(() => [{ label: __('Students'), route: { name: 'Students' } }])

const result = createResource({
	url: 'lms.lms.academic.get_report',
	makeParams() {
		return {
			report: 'students',
			filters: {
				query: query.value,
				batch_id: batch.value,
				department: department.value,
			},
			page: page.value,
			page_size: 20,
			sort_by: 'full_name',
			sort_order: 'asc',
		}
	},
	onError(error) {
		toast.error(errorMessage(error))
	},
	auto: canView.value,
})

const load = (nextPage) => {
	page.value = nextPage
	result.reload()
}

usePageMeta(() => ({ title: __('Students'), icon: brand.favicon }))
</script>
