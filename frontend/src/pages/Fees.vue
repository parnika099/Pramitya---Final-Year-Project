<template>
	<div>
		<header
			class="sticky top-0 z-10 flex items-center justify-between border-b bg-surface-white px-3 py-2.5 sm:px-5"
		>
			<Breadcrumbs class="h-7" :items="breadcrumbs" />
		</header>
		<div class="p-5">
			<div class="mb-5 grid grid-cols-2 gap-3 md:grid-cols-4">
				<div
					v-for="card in summaryCards"
					:key="card.label"
					class="rounded-md border px-3 py-3"
				>
					<div class="text-xs text-ink-gray-5">{{ card.label }}</div>
					<div class="mt-1 text-lg font-semibold text-ink-gray-9">
						{{ card.value }}
					</div>
				</div>
			</div>

			<div
				v-if="canManage"
				class="mb-5 rounded-md border p-4"
			>
				<div class="mb-3 font-semibold text-ink-gray-9">
					{{ __('New fee record') }}
				</div>
				<div class="grid grid-cols-1 gap-3 md:grid-cols-3">
					<FormControl v-model="draft.student_id" :label="__('Student ID')" />
					<FormControl v-model="draft.batch" :label="__('Batch ID')" />
					<FormControl v-model="draft.academic_year" :label="__('Academic year')" />
					<FormControl
						v-model="draft.semester"
						type="select"
						:label="__('Semester / year')"
						:options="semesterOptions"
					/>
					<FormControl v-model="draft.department" :label="__('Department')" />
					<FormControl v-model="draft.total_fees" :label="__('Total fees')" />
					<FormControl v-model="draft.due_date" type="date" :label="__('Due date')" />
				</div>
				<Button class="mt-3" variant="solid" :loading="saving" @click="createAccount">
					{{ __('Save fee record') }}
				</Button>
			</div>

			<div class="mb-3 grid grid-cols-1 gap-2 sm:grid-cols-4">
				<FormControl
					v-if="canManage || isFaculty"
					v-model="filters.student_id"
					:placeholder="__('Student ID')"
				/>
				<FormControl
					v-if="canManage || isFaculty"
					v-model="filters.batch"
					:placeholder="__('Batch ID')"
				/>
				<FormControl
					v-model="filters.status"
					type="select"
					:options="statusOptions"
				/>
				<Button @click="load(1)">{{ __('Filter') }}</Button>
			</div>

			<div class="overflow-x-auto rounded-md border">
				<table class="min-w-full text-left text-sm">
					<thead class="bg-surface-gray-1 text-ink-gray-7">
						<tr>
							<th class="px-3 py-2">{{ __('Student ID') }}</th>
							<th class="px-3 py-2">{{ __('Student') }}</th>
							<th class="px-3 py-2">{{ __('Batch ID') }}</th>
							<th class="px-3 py-2">{{ __('Total') }}</th>
							<th class="px-3 py-2">{{ __('Paid') }}</th>
							<th class="px-3 py-2">{{ __('Outstanding') }}</th>
							<th class="px-3 py-2">{{ __('Status') }}</th>
							<th class="px-3 py-2">{{ __('Due') }}</th>
						</tr>
					</thead>
					<tbody>
						<tr v-if="!accounts.data?.rows?.length">
							<td colspan="8" class="px-3 py-6 text-center text-ink-gray-5">
								{{ __('No fee records.') }}
							</td>
						</tr>
						<tr
							v-for="row in accounts.data?.rows || []"
							:key="row.name"
							class="cursor-pointer border-t"
							@click="openAccount(row.name)"
						>
							<td class="px-3 py-2 font-medium">{{ row.student_id }}</td>
							<td class="px-3 py-2">{{ row.student_name }}</td>
							<td class="px-3 py-2">{{ row.batch_code || '—' }}</td>
							<td class="px-3 py-2">{{ row.total_fees }}</td>
							<td class="px-3 py-2">{{ row.amount_paid }}</td>
							<td class="px-3 py-2 font-medium">{{ row.pending_amount }}</td>
							<td class="px-3 py-2">
								<Badge :theme="statusTheme(row.status)" :label="row.status" />
							</td>
							<td class="px-3 py-2">{{ row.due_date }}</td>
						</tr>
					</tbody>
				</table>
			</div>

			<div
				v-if="selected.data"
				class="mt-5 rounded-md border p-4"
			>
				<div class="mb-2 flex items-center justify-between">
					<div class="font-semibold text-ink-gray-9">
						{{ selected.data.student_id }} · {{ selected.data.status }} ·
						{{ __('Outstanding') }} {{ selected.data.pending_amount }}
					</div>
					<Button variant="ghost" @click="selected.reset()">{{ __('Close') }}</Button>
				</div>
				<table class="mb-4 min-w-full text-left text-sm">
					<thead>
						<tr class="text-ink-gray-6">
							<th class="py-1 pr-3">{{ __('Date') }}</th>
							<th class="py-1 pr-3">{{ __('Amount') }}</th>
							<th class="py-1 pr-3">{{ __('Method') }}</th>
							<th class="py-1 pr-3">{{ __('Reference') }}</th>
						</tr>
					</thead>
					<tbody>
						<tr v-if="!selected.data.transactions?.length">
							<td colspan="4" class="py-2 text-ink-gray-5">
								{{ __('No payments yet.') }}
							</td>
						</tr>
						<tr v-for="payment in selected.data.transactions" :key="payment.name">
							<td class="py-1 pr-3">{{ payment.payment_date }}</td>
							<td class="py-1 pr-3">{{ payment.amount }}</td>
							<td class="py-1 pr-3">{{ payment.payment_method }}</td>
							<td class="py-1 pr-3">{{ payment.transaction_id || '—' }}</td>
						</tr>
					</tbody>
				</table>
				<div v-if="canManage" class="grid grid-cols-1 gap-3 md:grid-cols-4">
					<FormControl v-model="payment.amount" :label="__('Amount')" />
					<FormControl v-model="payment.payment_date" type="date" :label="__('Payment date')" />
					<FormControl
						v-model="payment.payment_method"
						type="select"
						:label="__('Method')"
						:options="methodOptions"
					/>
					<FormControl v-model="payment.transaction_id" :label="__('Reference ID')" />
					<Button variant="solid" :loading="saving" @click="recordPayment">
						{{ __('Record payment') }}
					</Button>
				</div>
			</div>
		</div>
	</div>
</template>
<script setup>
import { computed, inject, reactive, ref } from 'vue'
import {
	Badge,
	Breadcrumbs,
	Button,
	FormControl,
	call,
	createResource,
	toast,
	usePageMeta,
} from 'frappe-ui'
import { sessionStore } from '@/stores/session'
import {
	PAYMENT_METHODS,
	SEMESTERS,
	errorMessage,
	statusTheme,
	validateMoney,
} from '@/utils/academic'

const user = inject('$user')
const { brand } = sessionStore()
const saving = ref(false)
const filters = reactive({ student_id: '', batch: '', status: '' })
const draft = reactive({
	student_id: '',
	batch: '',
	academic_year: '',
	semester: 'Semester 1',
	department: '',
	total_fees: '',
	due_date: '',
})
const payment = reactive({
	amount: '',
	payment_date: new Date().toISOString().slice(0, 10),
	payment_method: 'UPI',
	transaction_id: '',
})

const canManage = computed(
	() => user.data?.is_moderator || user.data?.is_system_manager
)
const isFaculty = computed(
	() => user.data?.is_evaluator || user.data?.is_instructor
)
const breadcrumbs = computed(() => [{ label: __('Fees'), route: { name: 'Fees' } }])
const semesterOptions = SEMESTERS.map((item) => ({ label: item, value: item }))
const methodOptions = PAYMENT_METHODS.map((item) => ({ label: item, value: item }))
const statusOptions = [{ label: __('All statuses'), value: '' }].concat(
	['Paid', 'Partially Paid', 'Pending', 'Overdue'].map((item) => ({
		label: __(item),
		value: item,
	}))
)

const accounts = createResource({
	url: 'lms.lms.academic.list_fee_accounts',
	makeParams() {
		return {
			query: filters.student_id,
			batch: filters.batch,
			status: filters.status,
			page: 1,
			page_size: 50,
		}
	},
	auto: true,
	onError(error) {
		toast.error(errorMessage(error))
	},
})

const selected = createResource({
	url: 'lms.lms.academic.get_fee_account',
	onError(error) {
		toast.error(errorMessage(error))
	},
})

const summaryCards = computed(() => {
	const summary = accounts.data?.summary || []
	if (summary.length) return summary.slice(0, 4)
	const rows = accounts.data?.rows || []
	const outstanding = rows.reduce((sum, row) => sum + Number(row.pending_amount || 0), 0)
	return [
		{ label: __('Records'), value: accounts.data?.total || rows.length },
		{ label: __('Outstanding on this page'), value: outstanding.toFixed(2) },
	]
})

const load = () => {
	accounts.reload()
}

const openAccount = (name) => {
	selected.fetch({ name })
}

const createAccount = async () => {
	const amountError = validateMoney(draft.total_fees)
	if (amountError) {
		toast.error(amountError)
		return
	}
	if (!draft.student_id || !draft.batch || !draft.academic_year || !draft.due_date) {
		toast.error(__('Student ID, Batch ID, academic year, and due date are required.'))
		return
	}
	saving.value = true
	try {
		await call('lms.lms.academic.create_fee_account', { ...draft })
		toast.success(__('Fee record saved'))
		draft.total_fees = ''
		accounts.reload()
	} catch (error) {
		toast.error(errorMessage(error))
	} finally {
		saving.value = false
	}
}

const recordPayment = async () => {
	const amountError = validateMoney(payment.amount, false)
	if (amountError) {
		toast.error(amountError)
		return
	}
	if (!payment.payment_date || !payment.payment_method) {
		toast.error(__('Payment date and method are required.'))
		return
	}
	saving.value = true
	try {
		const updated = await call('lms.lms.academic.record_fee_payment', {
			fee_account: selected.data.name,
			...payment,
		})
		selected.data = updated
		payment.amount = ''
		payment.transaction_id = ''
		toast.success(__('Payment recorded'))
		accounts.reload()
	} catch (error) {
		toast.error(errorMessage(error))
	} finally {
		saving.value = false
	}
}

usePageMeta(() => ({ title: __('Fees'), icon: brand.favicon }))
</script>
