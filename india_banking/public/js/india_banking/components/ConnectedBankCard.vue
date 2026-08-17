<template>
	<div
		class="bank-card"
		:class="{ selected }"
		:style="{ background: cardGradient }"
		@click="selectCard"
	>
		<!-- top-right logo -->
		<img :src="bank.logo" class="bank-logo-top" alt="" />

		<!-- watermark logo -->
		<img :src="bank.logo" class="bank-watermark" aria-hidden="true" />

		<!-- header -->
		<div class="card-header">
			<span class="bank-name">{{ bank.bank_name }}</span>
		</div>

		<!-- account number -->
		<div class="account-number">
			<span>
				{{ showNumber ? bank.account_number : maskedAccountNumber }}
			</span>

			<span class="eye" @click.stop="toggleNumber">👁</span>
		</div>

		<!-- footer -->
		<div class="card-footer">
			<div class="footer-item">
				<div class="label">Account</div>
				<div class="value">{{ bank.account_name }}</div>
			</div>

			<div class="footer-item">
				<div class="label">Branch Code</div>
				<div class="value">{{ bank.branch_code }}</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed, ref } from "vue";

const props = defineProps({
	bank: Object,
});

const showNumber = ref(false);
const selected = ref(false);

const toggleNumber = () => (showNumber.value = !showNumber.value);

const selectCard = () => {
	selected.value = true;
	setTimeout(() => (selected.value = false), 180);
	frappe.set_route("Form", "Bank Account", props.bank.name);
};

const maskedAccountNumber = computed(() => props.bank.account_number.replace(/\d(?=\d{4})/g, "•"));

const cardGradient = computed(() => {
	const c1 = props.bank.primary_color || "#1e3a8a";
	const c2 = props.bank.secondary_color || "#2563eb";
	return `linear-gradient(135deg, ${c1}, ${c2})`;
});
</script>

<style scoped>
.bank-card {
	position: relative;
	min-width: 340px;
	height: 210px;
	border-radius: 18px;
	padding: 20px;
	color: #fff;
	overflow: hidden;
	cursor: pointer;

	font-family: system-ui;
	box-shadow: 0 12px 30px rgba(0, 0, 0, 0.25);
	transition: transform 0.18s ease, box-shadow 0.18s ease;
}

.bank-card:hover {
	transform: translateY(-4px);
}

.bank-card.selected {
	transform: scale(0.98);
}

/* top-right logo */
.bank-logo-top {
	position: absolute;
	top: 5px;
	right: 14px;
	width: 90px;
	height: 50px;
	object-fit: contain;
	border-radius: 8px;
	padding: 4px;
}

/* watermark */
.bank-watermark {
	position: absolute;
	inset: 0;
	margin: auto;
	width: 160px;
	opacity: 0.08;
	filter: grayscale(100%);
	pointer-events: none;
}

/* content */
.card-header {
	font-weight: 600;
	font-size: 15px;
}

.account-number {
	margin-top: 26px;
	font-size: 18px;
	letter-spacing: 2px;
	display: flex;
	justify-content: space-between;
}

.eye {
	cursor: pointer;
	opacity: 0.8;
}

.card-footer {
	margin-top: 26px;
	display: flex;
	justify-content: space-between;
}

.label {
	font-size: 10px;
	opacity: 0.75;
}

.value {
	font-size: 14px;
	font-weight: 600;
}
</style>
