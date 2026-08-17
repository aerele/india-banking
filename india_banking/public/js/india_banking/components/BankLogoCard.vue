<template>
	<div class="bank-card" @click="goToBank">
		<div
			class="bank-icon"
			:style="!bank.logo ? { background: bank.primary_color || '#1a1a2e' } : null"
		>
			<img v-if="bank.logo" :src="bank.logo" :alt="bank.name" class="bank-logo" />
			<span v-else class="bank-initials">{{ initials }}</span>
		</div>

		<div class="bank-text">
			<div class="bank-name" :title="bank.name">{{ bank.name }}</div>
			<div class="bank-status" :class="{ connected: bank.status === 'Connected' }">
				{{ bank.status }}
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
	bank: {
		type: Object,
		required: true,
	},
});

const initials = computed(() =>
	props.bank.name
		.split(" ")
		.map((word) => word[0])
		.join("")
		.slice(0, 2)
		.toUpperCase()
);

const goToBank = () => {
	frappe.set_route("List", "Bank Account", {
		bank: props.bank.name,
		is_company_account: 1,
		disabled: 0,
	});
};
</script>

<style scoped>
.bank-card {
	display: flex;
	align-items: center;
	gap: 12px;
	padding: 10px 14px;
	border: 1px solid #e5e7eb;
	border-radius: 12px;
	background: #ffffff;
	cursor: pointer;
	user-select: none;
	transition: box-shadow 0.15s ease, border-color 0.15s ease;
}

.bank-card:hover {
	box-shadow: 0 4px 14px rgba(0, 0, 0, 0.08);
	border-color: #d1d5db;
}

.bank-icon {
	flex-shrink: 0;
	width: 40px;
	height: 40px;
	border-radius: 50%;
	display: flex;
	align-items: center;
	justify-content: center;
	overflow: hidden;
	background: #f3f4f6;
}

.bank-logo {
	width: 26px;
	height: 26px;
	object-fit: contain;
}

.bank-initials {
	font-size: 13px;
	font-weight: 700;
	color: #ffffff;
}

.bank-text {
	min-width: 0;
	display: flex;
	flex-direction: column;
}

.bank-name {
	font-size: 14px;
	font-weight: 600;
	color: #111827;
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}

.bank-status {
	font-size: 12px;
	color: #2563eb;
}

.bank-status.connected {
	color: #16a34a;
	font-weight: 600;
}
</style>
