<template>
	<div class="bank-card p-4" @click="goToBank">
		<img :src="bank.logo" :alt="bank.name" class="bank-logo" />
	</div>
</template>

<script setup>
const props = defineProps({
	bank: {
		type: Object,
		required: true,
	},
});

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
	width: 170px;
	height: 130px;
	padding: 8px;
	border: 1px solid #e5e7eb;
	border-radius: 14px;
	text-align: center;
	background: #ffffff;

	display: inline-flex;
	flex-direction: column;
	align-items: center;

	cursor: pointer;
	user-select: none;

	transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
	will-change: transform;
}

.bank-card:hover {
	transform: scale(1.08);
	box-shadow: 0 12px 28px rgba(0, 0, 0, 0.12);
	border-color: #2563eb;
}

.bank-logo {
	width: 150px;
	height: 150px;
	object-fit: contain;
}

.bank-name {
	margin-top: 12px;
	font-size: 15px;
	font-weight: 600;
}
</style>
