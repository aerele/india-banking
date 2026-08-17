<template>
	<div class="p-4">
		<h3 class="mb-3 text-lg font-semibold">Available Banks</h3>

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
.bank-grid {
	display: flex;
	gap: 24px;
	flex-wrap: wrap;
}
</style>
