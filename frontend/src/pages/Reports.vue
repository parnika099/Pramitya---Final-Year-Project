<template>
	<div>
		<header
			class="sticky top-0 z-10 flex flex-wrap items-center justify-between gap-2 border-b bg-surface-white px-3 py-2.5 sm:px-5"
		>
			<Breadcrumbs class="h-7" :items="breadcrumbs" />
			<div class="flex gap-2">
				<Button @click="exportCsv" :loading="exporting">{{ __('Export CSV') }}</Button>
				<Button @click="printCurrent">{{ __('Print') }}</Button>
			</div>
		</header>
		<div class="p-5">
			<div class="mb-4 flex flex-wrap gap-2">
				<Button
					v-for="tab in tabs"
					:key="tab.id"
					:variant="report === tab.id ? 'solid' : 'subtle'"
					@click="switchReport(tab.id)"
				>
					{{ tab.label }}
				</Button>
			</div>
			<div v-if="report !== 'mine'" class="mb-4 grid grid-cols-1 gap-2 md:grid-cols-3 xl:grid-cols-6">
				<FormControl v-model="filters.student_id" :placeholder="__('Student ID')" />
				<FormControl v-model="filters.batch_id" :placeholder="__('Batch ID')" />
				<FormControl v-model="filters.department" :placeholder="__('Department')" />
				<FormControl v-model="filters.semester" :placeholder="__('Semester')" />
				<FormControl v-model="filters.date_from" type="date" />
				<FormControl v-model="filters.date_to" type="date" />
				<FormControl
					v-if="report === 'fees'"
					v-model="filters.payment_status"
					type="select"
					:options="statusOptions"
				/>
				<Button variant="solid" @click="load(1)">{{ __('Apply') }}</Button>
			</div>
			<div class="mb-4 grid grid-cols-2 gap-3 md:grid-cols-4">
				<div
					v-for="card in result.data?.summary || []"
					:key="card.label"
					class="rounded-md border px-3 py-3"
				>
					<div class="text-xs text-ink-gray-5">{{ __(card.label) }}</div>
					<div class="mt-1 text-lg font-semibold text-ink-gray-9">{{ card.value }}</div>
				</div>
			</div>
			<div class="overflow-x-auto rounded-md border">
				<table class="min-w-full text-left text-sm">
					<thead class="bg-surface-gray-1 text-ink-gray-7">
						<tr>
							<th
								v-for="column in result.data?.columns || []"
								:key="column.key"
								class="cursor-pointer px-3 py-2 font-medium"
								@click="sort(column.key)"
							>
								{{ __(column.label) }}
							</th>
						</tr>
					</thead>
					<tbody>
						<tr v-if="!result.data?.rows?.length">
							<td
								:colspan="result.data?.columns?.length || 1"
								class="px-3 py-6 text-center text-ink-gray-5"
							>
								{{ __('No records for these filters.') }}
							</td>
						</tr>
						<tr
							v-for="(row, index) in result.data?.rows || []"
							:key="index"
							class="border-t"
						>
							<td
								v-for="column in result.data?.columns || []"
								:key="column.key"
								class="px-3 py-2"
							>
								{{ row[column.key] ?? '—' }}
							</td>
						</tr>
					</tbody>
				</table>
			</div>
			<div
				v-if="report !== 'mine'"
				class="mt-3 flex items-center justify-between text-sm text-ink-gray-6"
			>
				<span>{{ __('Page') }} {{ result.data?.page || page }} · {{ result.data?.total || 0 }}</span>
				<div class="flex gap-2">
					<Button :disabled="page <= 1" @click="load(page - 1)">{{ __('Previous') }}</Button>
					<Button
						:disabled="page * (result.data?.page_size || 20) >= (result.data?.total || 0)"
						@click="load(page + 1)"
					>
						{{ __('Next') }}
					</Button>
				</div>
			</div>
			<div
				v-if="report === 'fees' && result.data?.collections?.length"
				class="mt-5"
			>
				<div class="mb-2 font-semibold text-ink-gray-9">
					{{ __('Date-wise collection') }}
				</div>
				<div class="overflow-x-auto rounded-md border">
					<table class="min-w-full text-left text-sm">
						<thead class="bg-surface-gray-1">
							<tr>
								<th class="px-3 py-2">{{ __('Date') }}</th>
								<th class="px-3 py-2">{{ __('Collected') }}</th>
								<th class="px-3 py-2">{{ __('Payments') }}</th>
							</tr>
						</thead>
						<tbody>
							<tr v-for="row in result.data.collections" :key="row.payment_date" class="border-t">
								<td class="px-3 py-2">{{ row.payment_date }}</td>
								<td class="px-3 py-2">{{ row.collected }}</td>
								<td class="px-3 py-2">{{ row.payments }}</td>
							</tr>
						</tbody>
					</table>
				</div>
			</div>
		</div>
	</div>
</template>
<script setup>
import { computed, inject, reactive, ref } from 'vue'
import {
	Breadcrumbs,
	Button,
	FormControl,
	createResource,
	toast,
	usePageMeta,
	call,
} from 'frappe-ui'
import { sessionStore } from '@/stores/session'
import { downloadTextFile, errorMessage, printTable } from '@/utils/academic'

const user = inject('$user')
const { brand } = sessionStore()
const page = ref(1)
const exporting = ref(false)
const sortBy = ref('')
const sortOrder = ref('desc')
const filters = reactive({
	student_id: '',
	batch_id: '',
	department: '',
	semester: '',
	academic_year: '',
	payment_status: '',
	date_from: '',
	date_to: '',
})

const isStaff = computed(
	() =>
		user.data?.is_moderator ||
		user.data?.is_system_manager ||
		user.data?.is_evaluator ||
		user.data?.is_instructor
)
const isAdmin = computed(
	() => user.data?.is_moderator || user.data?.is_system_manager
)
const tabs = computed(() => {
	if (!isStaff.value) return [{ id: 'mine', label: __('My records') }]
	const items = [
		{ id: 'students', label: __('Students') },
		{ id: 'batches', label: __('Batches') },
		{ id: 'fees', label: __('Fees') },
	]
	if (isAdmin.value) items.push({ id: 'activity', label: __('Activity') })
	return items
})
const report = ref(isStaff.value ? 'students' : 'mine')
const breadcrumbs = computed(() => [{ label: __('Reports'), route: { name: 'Reports' } }])
const statusOptions = [
	{ label: __('All statuses'), value: '' },
	{ label: __('Paid'), value: 'Paid' },
	{ label: __('Partially Paid'), value: 'Partially Paid' },
	{ label: __('Pending'), value: 'Pending' },
	{ label: __('Overdue'), value: 'Overdue' },
]

const result = createResource({
	url: 'lms.lms.academic.get_report',
	makeParams() {
		return {
			report: report.value,
			filters: { ...filters },
			page: page.value,
			page_size: 20,
			sort_by: sortBy.value,
			sort_order: sortOrder.value,
		}
	},
	auto: true,
	onError(error) {
		toast.error(errorMessage(error))
	},
})

const switchReport = (id) => {
	report.value = id
	page.value = 1
	sortBy.value = ''
	result.reload()
}

const load = (nextPage) => {
	page.value = nextPage
	result.reload()
}

const sort = (key) => {
	if (sortBy.value === key) {
		sortOrder.value = sortOrder.value === 'asc' ? 'desc' : 'asc'
	} else {
		sortBy.value = key
		sortOrder.value = 'asc'
	}
	load(1)
}

const exportCsv = async () => {
	exporting.value = true
	try {
		const file = await call('lms.lms.academic.export_report', {
			report: report.value,
			filters: { ...filters },
		})
		downloadTextFile(file.filename, file.content, file.mime)
	} catch (error) {
		toast.error(errorMessage(error))
	} finally {
		exporting.value = false
	}
}

const printCurrent = () => {
	printTable(
		__('Reports'),
		result.data?.columns || [],
		result.data?.rows || []
	)
}

usePageMeta(() => ({ title: __('Reports'), icon: brand.favicon }))
</script>
