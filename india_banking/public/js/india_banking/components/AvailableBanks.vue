<template>
	<div class="p-4">
		<h3 class="mb-3 section-title">Available Banks</h3>

		<div class="bank-grid">
			<BankLogoCard v-for="bank in banks" :key="bank.name" :bank="bank" />
		</div>
	</div>
</template>

<script setup>
import { ref, onMounted } from "vue";

const banks = ref([]);

onMounted(async () => {
	const res = await fetch("/api/method/india_banking.api.get_standard_bank");
	const data = await res.json();
	banks.value = data.message || [];
});
</script>

<style scoped>
.section-title {
	font-size: 22px;
	font-weight: 700;
}

.bank-grid {
	display: grid;
	grid-template-columns: repeat(6, minmax(0, 1fr));
	gap: 16px;
}

@media (max-width: 1200px) {
	.bank-grid {
		grid-template-columns: repeat(4, minmax(0, 1fr));
	}
}

@media (max-width: 768px) {
	.bank-grid {
		grid-template-columns: repeat(2, minmax(0, 1fr));
	}
}
</style>
