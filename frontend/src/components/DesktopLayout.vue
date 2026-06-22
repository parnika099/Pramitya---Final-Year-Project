<template>
	<div class="flex h-screen w-screen flex-col bg-[#f3f5fa]">
		<InstitutionHeader />
		<div class="flex min-h-0 flex-1">
			<div class="h-full bg-white shadow-[3px_0_12px_rgba(38,49,100,0.08)]">
				<AppSidebar />
			</div>
			<main class="institution-workspace flex min-w-0 flex-1 flex-col overflow-auto">
				<slot />
			</main>
		</div>
	</div>
</template>
<script setup>
import AppSidebar from '@/components/Sidebar/AppSidebar.vue'
import InstitutionHeader from '@/components/InstitutionHeader.vue'
</script>
