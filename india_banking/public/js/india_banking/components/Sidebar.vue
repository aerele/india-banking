<template>
	<div class="sidebar">
		<div class="sidebar-brand">
			<span class="brand-icon">₹</span>
			<span class="brand-label">India Banking</span>
		</div>

		<div class="sidebar-nav">
			<div class="nav-item" @click="go(['Form', 'India Banking Settings'])">
				<span class="nav-icon">⚙️</span>
				<span>India Banking Settings</span>
			</div>
			<div class="nav-item" @click="go(['List', 'India Banking Request Log'])">
				<span class="nav-icon">📋</span>
				<span>India Banking Request Log</span>
			</div>
			<div class="nav-item" @click="go(['List', 'Mode of Transfer'])">
				<span class="nav-icon">🔁</span>
				<span>Mode of Transfer</span>
			</div>

			<div class="nav-group">
				<div class="nav-group-title" @click="reportsOpen = !reportsOpen">
					<span>Reports</span>
					<span class="chevron" :class="{ open: reportsOpen }">›</span>
				</div>

				<div v-show="reportsOpen" class="nav-group-items">
					<div
						class="nav-item"
						@click="go(['query-report', 'Bulk Create Payment Request'])"
					>
						<span>Bulk Create Payment Request</span>
					</div>
					<div
						class="nav-item"
						@click="go(['query-report', 'Bulk Update Payment Request'])"
					>
						<span>Bulk Update Payment Request</span>
					</div>
					<div class="nav-item" @click="go(['query-report', 'Bank GST Payables'])">
						<span>Bank GST Payables</span>
					</div>
				</div>
			</div>
		</div>

		<div class="sidebar-footer">
			<img v-if="userImage" :src="userImage" class="user-avatar" alt="" />
			<span v-else class="user-avatar user-avatar-fallback">{{ userAbbr }}</span>

			<div class="user-text">
				<div class="user-name">{{ userFullName }}</div>
				<div class="user-email">{{ userEmail }}</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { ref } from "vue";

const reportsOpen = ref(true);

const userInfo = frappe.user_info();
const userFullName = userInfo.fullname;
const userEmail = frappe.session.user;
const userImage = userInfo.image;
const userAbbr = userInfo.abbr;

const go = (route) => frappe.set_route(...route);
</script>

<style scoped>
.sidebar {
	display: flex;
	flex-direction: column;
	width: 240px;
	flex-shrink: 0;
	height: 100%;
	border-right: 1px solid #e5e7eb;
	background: #ffffff;
}

.sidebar-brand {
	display: flex;
	align-items: center;
	gap: 10px;
	padding: 18px 16px;
	font-size: 16px;
	font-weight: 700;
	color: #111827;
}

.brand-icon {
	display: flex;
	align-items: center;
	justify-content: center;
	width: 32px;
	height: 32px;
	border-radius: 8px;
	background: #2563eb;
	color: #ffffff;
	font-weight: 700;
}

.sidebar-nav {
	flex: 1;
	overflow-y: auto;
	padding: 8px 8px;
}

.nav-item {
	display: flex;
	align-items: center;
	gap: 10px;
	padding: 8px 10px;
	border-radius: 8px;
	font-size: 13px;
	color: #374151;
	cursor: pointer;
	user-select: none;
}

.nav-item:hover {
	background: #f3f4f6;
}

.nav-icon {
	font-size: 14px;
}

.nav-group {
	margin-top: 6px;
}

.nav-group-title {
	display: flex;
	align-items: center;
	justify-content: space-between;
	padding: 8px 10px;
	font-size: 12px;
	font-weight: 600;
	color: #6b7280;
	text-transform: uppercase;
	letter-spacing: 0.04em;
	cursor: pointer;
	user-select: none;
}

.chevron {
	transition: transform 0.15s ease;
}

.chevron.open {
	transform: rotate(90deg);
}

.nav-group-items .nav-item {
	padding-left: 20px;
	font-size: 12.5px;
}

.sidebar-footer {
	display: flex;
	align-items: center;
	gap: 10px;
	padding: 14px 16px;
	border-top: 1px solid #e5e7eb;
}

.user-avatar {
	width: 32px;
	height: 32px;
	border-radius: 50%;
	object-fit: cover;
	flex-shrink: 0;
}

.user-avatar-fallback {
	display: flex;
	align-items: center;
	justify-content: center;
	background: #2563eb;
	color: #ffffff;
	font-size: 12px;
	font-weight: 700;
}

.user-text {
	min-width: 0;
}

.user-name {
	font-size: 13px;
	font-weight: 600;
	color: #111827;
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}

.user-email {
	font-size: 12px;
	color: #6b7280;
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}
</style>
