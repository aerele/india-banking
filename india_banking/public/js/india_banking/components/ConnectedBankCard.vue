<template>
	<div
		class="bank-card"
		:class="{ selected }"
		:style="{ background: cardGradient }"
		@click="selectCard"
	>
		<!-- top-right logo -->
		<div class="bank-logo-top">
			<img v-if="bank.logo" :src="bank.logo" alt="" class="bank-logo-img" />
			<span v-else class="bank-logo-initials">{{ initials }}</span>
		</div>

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

const initials = computed(() =>
	(props.bank.bank_name || "")
		.split(" ")
		.map((word) => word[0])
		.join("")
		.slice(0, 2)
		.toUpperCase()
);

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
	top: 16px;
	right: 16px;
	width: 44px;
	height: 44px;
	border-radius: 50%;
	background: rgba(255, 255, 255, 0.15);
	display: flex;
	align-items: center;
	justify-content: center;
	overflow: hidden;
}

.bank-logo-img {
	width: 26px;
	height: 26px;
	object-fit: contain;
}

.bank-logo-initials {
	font-size: 13px;
	font-weight: 700;
	color: #ffffff;
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
