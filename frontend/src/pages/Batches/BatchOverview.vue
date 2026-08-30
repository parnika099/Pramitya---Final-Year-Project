<template>
	<div class="m-5 pb-10">
		<div class="flex justify-between w-full">
			<div class="md:w-2/3">
				<div class="text-3xl font-semibold text-ink-gray-9">
					{{ batch.data.title }}
				</div>
				<div
					v-if="batch.data.batch_code || batch.data.academic_year || batch.data.department"
					class="mt-2 flex flex-wrap gap-2 text-sm text-ink-gray-7"
				>
					<span v-if="batch.data.batch_code" class="rounded-md border px-2 py-1">
						{{ __('Batch ID') }} {{ batch.data.batch_code }}
					</span>
					<span v-if="batch.data.academic_year" class="rounded-md border px-2 py-1">
						{{ batch.data.academic_year }}
					</span>
					<span v-if="batch.data.department" class="rounded-md border px-2 py-1">
						{{ batch.data.department }}
					</span>
					<span v-if="batch.data.semester" class="rounded-md border px-2 py-1">
						{{ batch.data.semester }}
					</span>
				</div>
				<div class="my-3 leading-6 text-ink-gray-7">
					{{ batch.data.description }}
				</div>
				<div class="flex avatar-group overlap">
					<div
						class="h-6 mr-1"
						:class="{
							'avatar-group overlap': batch.data.instructors.length > 1,
						}"
					>
						<UserAvatar
							v-for="instructor in batch.data.instructors"
							:user="instructor"
						/>
					</div>
					<CourseInstructors :instructors="batch.data.instructors" />
				</div>
				<BatchOverlay :batch="batch" class="md:hidden mt-5" />
				<div
					class="ProseMirror prose prose-table:table-fixed prose-td:p-2 prose-th:p-2 prose-td:border prose-th:border prose-td:border-outline-gray-2 prose-th:border-outline-gray-2 prose-td:relative prose-th:relative prose-th:bg-surface-gray-2 prose-sm max-w-none !whitespace-normal mt-10"
					v-html="batch.data.batch_details"
				></div>
			</div>
			<div class="hidden md:block">
				<BatchOverlay :batch="batch" />
			</div>
		</div>
		<div v-if="courses.data?.length">
			<div class="flex items-center mt-10">
				<div class="text-2xl font-semibold text-ink-gray-9">
					{{ __('Courses') }}
				</div>
			</div>
			<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8 mt-5">
				<div
					v-if="courses.data?.length"
					v-for="course in courses.data"
					:key="course.course"
				>
					<router-link
						:to="{
							name: 'CourseDetail',
							params: {
								courseName: course.name,
							},
						}"
					>
						<CourseCard :course="course" :key="course.name" />
					</router-link>
				</div>
			</div>
			<div v-if="batch.data.batch_details_raw">
				<div
					v-html="batch.data.batch_details_raw"
					class="batch-description"
				></div>
			</div>
		</div>
	</div>
</template>
<script setup lang="ts">
import { createResource } from 'frappe-ui'
import CourseCard from '@/components/CourseCard.vue'
import BatchOverlay from '@/pages/Batches/components/BatchOverlay.vue'
import CourseInstructors from '@/components/CourseInstructors.vue'
import UserAvatar from '@/components/UserAvatar.vue'

const props = defineProps({
	batch: {
		type: Object,
		default: null,
	},
})

const courses = createResource({
	url: 'lms.lms.utils.get_batch_courses',
	params: {
		batch: props.batch?.data?.name,
	},
	cache: ['batchCourses', props.batch?.data?.name],
	auto: true,
})
</script>
