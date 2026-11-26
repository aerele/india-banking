<template>
	<div class="skeleton-card">
		<div class="skeleton header"></div>
		<div class="skeleton line"></div>
		<div class="skeleton line short"></div>
	</div>
</template>

<style scoped>
.skeleton-card {
	min-width: 320px;
	height: 190px;
	border-radius: 16px;
	padding: 18px;
	background: #e5e7eb;
}

.skeleton {
	background: linear-gradient(90deg, #e5e7eb, #f1f5f9, #e5e7eb);
	background-size: 200% 100%;
	animation: shimmer 1.4s infinite;
	border-radius: 6px;
}

.header {
	width: 60%;
	height: 16px;
}

.line {
	margin-top: 28px;
	height: 18px;
}

.short {
	width: 50%;
	margin-top: 12px;
}

@keyframes shimmer {
	0% {
		background-position: 200% 0;
	}
	100% {
		background-position: -200% 0;
	}
}
</style>
