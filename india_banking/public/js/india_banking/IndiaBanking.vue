<template>
	<div class="p-4">
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
</template>

<script setup></script>
