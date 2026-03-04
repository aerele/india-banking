<template>
	<div class="doctype-links">
		<div v-for="link in links" :key="link.label" class="link-item" @click="go(link)">
			<span class="icon">{{ link.icon }}</span>
			<span class="label">{{ link.label }}</span>
		</div>
	</div>
</template>

<script setup>
const props = defineProps({
	links: {
		type: Array,
		required: true,
	},
});

const go = (link) => {
	if (link.route) {
		frappe.set_route(...link.route);
	}
};
</script>

<style scoped>
.doctype-links {
	display: flex;
	gap: 12px;
	margin-top: 14px;
	flex-wrap: wrap;
}

.link-item {
	display: flex;
	align-items: center;
	gap: 6px;

	padding: 6px 10px;
	border-radius: 10px;

	background: #f8fafc;
	border: 1px solid #e5e7eb;

	font-size: 12px;
	font-weight: 500;
	color: #334155;

	cursor: pointer;
	user-select: none;

	transition: background 0.15s ease, border-color 0.15s ease, transform 0.15s ease;
}

.link-item:hover {
	background: #eff6ff;
	border-color: #2563eb;
	transform: translateY(-1px);
}

.icon {
	font-size: 14px;
}
</style>
