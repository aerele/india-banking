<template>
	<div class="sidebar" :class="{ collapsed }">
		<button class="collapse-toggle" @click="collapsed = !collapsed">
			{{ collapsed ? "»" : "«" }}
		</button>

		<div class="sidebar-nav">
			<div
				class="nav-item"
				:title="'Mode of Transfer'"
				@click="go(['List', 'Mode of Transfer'])"
			>
				<span class="nav-icon" v-html="icon('refresh')"></span>
				<span v-if="!collapsed">Mode of Transfer</span>
			</div>
			<div
				class="nav-item"
				:title="'India Banking Request Log'"
				@click="go(['List', 'India Banking Request Log'])"
			>
				<span class="nav-icon" v-html="icon('list-alt')"></span>
				<span v-if="!collapsed">India Banking Request Log</span>
			</div>
			<div
				class="nav-item"
				:title="'India Banking Settings'"
				@click="go(['Form', 'India Banking Settings'])"
			>
				<span class="nav-icon" v-html="icon('setting-gear')"></span>
				<span v-if="!collapsed">India Banking Settings</span>
			</div>

			<div v-if="!collapsed" class="nav-group">
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

			<div v-if="!collapsed" class="user-text">
				<div class="user-name">{{ userFullName }}</div>
				<div class="user-email">{{ userEmail }}</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { ref } from "vue";

const collapsed = ref(false);
const reportsOpen = ref(true);

const userInfo = frappe.user_info();
const userFullName = userInfo.fullname;
const userEmail = frappe.session.user;
const userImage = userInfo.image;
const userAbbr = userInfo.abbr;

const go = (route) => frappe.set_route(...route);
const icon = (name) => frappe.utils.icon(name, "sm");
</script>

<style scoped>
.sidebar {
	position: relative;
	display: flex;
	flex-direction: column;
	width: 240px;
	flex-shrink: 0;
	border-right: 1px solid #e5e7eb;
	background: #ffffff;
	transition: width 0.15s ease;
}

.sidebar.collapsed {
	width: 60px;
}

.collapse-toggle {
	position: absolute;
	top: 12px;
	right: -12px;
	width: 24px;
	height: 24px;
	border-radius: 50%;
	border: 1px solid #e5e7eb;
	background: #ffffff;
	color: #374151;
	font-size: 12px;
	line-height: 1;
	cursor: pointer;
	z-index: 1;
}

.sidebar-nav {
	flex: 1;
	overflow-y: auto;
	overflow-x: hidden;
	padding: 44px 8px 8px;
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
	white-space: nowrap;
}

.nav-item:hover {
	background: #f3f4f6;
}

.nav-icon {
	display: flex;
	align-items: center;
	color: #8d99a6;
	flex-shrink: 0;
}

.nav-icon :deep(svg) {
	width: 16px;
	height: 16px;
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
