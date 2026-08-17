<template>
	<div class="india-banking-layout">
		<Sidebar />

		<div class="india-banking-content p-4">
			<DoctypeLinks
				:links="[
					{
						label: 'Bank Account',
						icon: '🏦',
						route: ['List', 'Bank Account'],
					},
					{
						label: 'India Banking Connector',
						icon: '🔗',
						route: ['List', 'Bank Connector'],
					},
					{
						label: 'Payment Entry',
						icon: '💸',
						route: ['List', 'Payment Entry'],
					},
				]"
			/>

			<AvailableBanks />
			<ConnectedBankList />
		</div>
	</div>
</template>

<script setup></script>

<style scoped>
.india-banking-layout {
	display: flex;
	min-height: calc(100vh - 56px);
}

.india-banking-content {
	flex: 1;
	min-width: 0;
}
</style>
