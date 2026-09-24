<template>
	<div class="connected-banks">
		<h3 class="mb-3 section-title">Connected Banks</h3>

		<!-- Skeletons while loading -->
		<div v-if="loading" class="bank-scroll">
			<SkeletonCard v-for="n in 3" :key="n" />
		</div>

		<!-- Bank cards -->
		<div v-else class="bank-scroll">
			<ConnectedBankCard v-for="bank in banks" :key="bank.name" :bank="bank" />
			<AddBankCard />
		</div>
	</div>
</template>

<script setup>
import { ref, onMounted } from "vue";

const banks = ref([]);
const loading = ref(true);

onMounted(async () => {
	try {
		const res = await fetch("/api/method/india_banking.api.get_connected_bank_accounts");
		const data = await res.json();
		banks.value = data.message || [];
	} finally {
		loading.value = false;
	}
});
</script>

<style scoped>
.connected-banks {
	padding: 16px;
}

.section-title {
	font-size: 22px;
	font-weight: 700;
}

.bank-scroll {
	display: flex;
	gap: 20px;
	overflow-x: auto;
	padding-bottom: 8px;
}

.bank-scroll::-webkit-scrollbar {
	height: 6px;
}

.bank-scroll::-webkit-scrollbar-thumb {
	background: #cbd5e1;
	border-radius: 6px;
}
</style>
