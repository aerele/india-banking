<template>
	<div class="add-bank-card" @click="addBank">
		<div class="plus">＋</div>
		<div class="text">Add Bank</div>
	</div>
</template>

<script setup>
const addBank = () => {
	frappe.set_route("Form", "Bank Account", "new");
};
</script>

<style scoped>
.add-bank-card {
	min-width: 340px;
	height: 210px;
	border-radius: 18px;

	display: flex;
	flex-direction: column;
	align-items: center;
	justify-content: center;

	border: 1.5px dashed #cbd5e1;
	background: #f8fafc;
	color: #475569;

	cursor: pointer;
	font-family: system-ui;

	transition: transform 0.18s ease, box-shadow 0.18s ease;
}

.add-bank-card:hover {
	transform: translateY(-3px);
	box-shadow: 0 10px 22px rgba(0, 0, 0, 0.12);
}

.plus {
	font-size: 36px;
	font-weight: 300;
}

.text {
	margin-top: 10px;
	font-size: 14px;
	font-weight: 600;
}
</style>
