<template>
	<div ref="layoutRef" class="india-banking-layout" :style="{ minHeight: layoutMinHeight }">
		<Sidebar />

		<div class="india-banking-content p-4">
			<AvailableBanks />
			<ConnectedBankList />
		</div>
	</div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from "vue";

const layoutRef = ref(null);
const layoutMinHeight = ref("100vh");

const updateLayoutHeight = () => {
	if (!layoutRef.value) return;
	const top = layoutRef.value.getBoundingClientRect().top;
	layoutMinHeight.value = `${window.innerHeight - top}px`;
};

onMounted(() => {
	updateLayoutHeight();
	window.addEventListener("resize", updateLayoutHeight);
});

onUnmounted(() => {
	window.removeEventListener("resize", updateLayoutHeight);
});
</script>

<style scoped>
.india-banking-layout {
	display: flex;
}

.india-banking-content {
	flex: 1;
	min-width: 0;
}
</style>
