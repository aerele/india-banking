frappe.ui.form.on("Bank Account", {
	onload(frm) {
		if (frm.doc.workflow_state == "Approved") {
			frm.set_read_only();
		}
	},
	refresh(frm) {
		let data = JSON.parse(frm.doc.bank_details_json || "{}");

		if (!cur_frm.is_new()) {
			if (data && Object.keys(data).length > 0) {
				let services_html = build_services_badges(data);

				let html_value = `
					<div style="
						border: 1px solid #dcdfe4;
						border-radius: 10px;
						padding: 16px;
						background: #fff;
						font-size: 13px;
						line-height: 1.6;
					">
						<div style="margin-bottom: 12px;">
							<div style="font-size: 16px; font-weight: 700;">
								${data.BANK ?? "-"}
							</div>
							<div style="color: #6b7280;">
								IFSC: <strong>${data.IFSC ?? "-"}</strong>
								&nbsp;•&nbsp;
								BANK CODE: <strong>${data.BANKCODE ?? "-"}</strong>
							</div>
						</div>

						<hr style="border: none; border-top: 1px solid #eee; margin: 12px 0;">

						<table style="width: 100%; border-collapse: collapse;">
							<tr>
								<td style="color:#6b7280; width: 140px; padding: 4px 0;">Branch</td>
								<td style="padding: 4px 0;">${data.BRANCH ?? "-"}</td>
							</tr>
							<tr>
								<td style="color:#6b7280; padding: 4px 0;">Address</td>
								<td style="padding: 4px 0;">${data.ADDRESS ?? "-"}</td>
							</tr>
							<tr>
								<td style="color:#6b7280; padding: 4px 0;">City</td>
								<td style="padding: 4px 0;">${data.CITY ?? "-"}</td>
							</tr>
							<tr>
								<td style="color:#6b7280; padding: 4px 0;">District</td>
								<td style="padding: 4px 0;">${data.DISTRICT ?? "-"}</td>
							</tr>
							<tr>
								<td style="color:#6b7280; padding: 4px 0;">State</td>
								<td style="padding: 4px 0;">${data.STATE ?? "-"}</td>
							</tr>
							<tr>
								<td style="color:#6b7280; padding: 4px 0;">MICR</td>
								<td style="padding: 4px 0;">${data.MICR ?? "-"}</td>
							</tr>
						</table>

						${
							services_html
								? `<div style="margin-top: 14px;">${services_html}</div>`
								: `<div style="margin-top: 14px; color:#6b7280;">No services available</div>`
						}
					</div>
				`;

				frm.set_df_property("bank_details_html", "options", html_value);
			} else {
				frm.set_df_property(
					"bank_details_html",
					"options",
					`<div class="alert alert-warning" style="margin:0;">Bank Details Not Found</div>`
				);
			}
		}
		if (frm.doc.is_company_account && !frm.doc.disabled) {
			frm.events.add_bank_custom_buttons(frm);
		}
		frappe.db.get_single_value("India Banking Settings", "enable_bank_account_workflow").then((r) => {
			if (r && frm.doc.workflow_state == "Approved") {
				frm.set_read_only();
			}
		});
	},
	add_bank_custom_buttons(frm) {
		if (!frm.doc.__islocal) {
			frm.events.add_balance_fetch_button(frm);
			frm.events.add_statements_fetch_button(frm);
		}
	},
	add_balance_fetch_button(frm) {
		frm.add_custom_button(
			__("Bank Balance"),
			function () {
				frappe.call({
					method: "india_banking.india_banking.doctype.india_banking_connector.india_banking_connector.get_bank_balance",
					freeze: true,
					args: {
						bank_account_name: frm.doc.name,
					},
					callback: () => {
						cur_frm.reload_doc();
					},
				});
			},
			"Fetch"
		);
	},
	add_statements_fetch_button(frm) {
		const fields = [
			{
				label: __("Company"),
				fieldname: "company",
				fieldtype: "Link",
				options: "Company",
				default: frm.doc.company,
				reqd: 1,
				read_only: 1,
			},
			{
				fieldtype: "Column Break",
			},
			{
				label: __("Bank Account"),
				fieldname: "bank_account",
				fieldtype: "Link",
				options: "Bank Account",
				default: frm.doc.name,
				reqd: 1,
				read_only: 1,
			},
			{
				fieldtype: "Section Break",
			},
			{
				label: __("From Date"),
				fieldname: "from_date",
				fieldtype: "Date",
				reqd: 1,
			},
			{
				fieldtype: "Column Break",
			},
			{
				label: __("To Date"),
				fieldname: "to_date",
				fieldtype: "Date",
				reqd: 1,
			},
		];
		frm.add_custom_button(
			__("Bank Statements"),
			function () {
				const dialog = new frappe.ui.Dialog({
					title: __("Fetch Statements"),
					fields,
					primary_action: () => {
						frm.call({
							method: "india_banking.india_banking.doctype.india_banking_connector.india_banking_connector.get_bank_statements",
							args: {
								bank_account_name: dialog.get_value("bank_account"),
								from_date: dialog.get_value("from_date"),
								to_date: dialog.get_value("to_date"),
							},
							freeze: true,
							freeze_message: __("Fetching..."),
							callback: function (r) {
								dialog.hide();
							},
						});
					},
					primary_action_label: __("Fetch"),
				});
				dialog.show();
			},
			"Fetch"
		);
	},
	after_workflow_action: function (frm) {
		if (frm.doc.workflow_state == "Approved") {
			frm.set_read_only();
		} else {
			cur_frm.reload_doc();
		}
	},
});

function random_badge_style() {
	let colors = [
		{ bg: "#ecfdf5", text: "#047857" }, // green
		{ bg: "#eff6ff", text: "#1d4ed8" }, // blue
		{ bg: "#fff7ed", text: "#9a3412" }, // orange
		{ bg: "#f5f3ff", text: "#5b21b6" }, // purple
		{ bg: "#fef2f2", text: "#991b1b" }, // red
		{ bg: "#f3f4f6", text: "#111827" }, // gray
	];
	return colors[Math.floor(Math.random() * colors.length)];
}

function build_services_badges(data) {
	let service_keys = ["NEFT", "RTGS", "IMPS", "UPI", "SWIFT"];
	let html = "";

	service_keys.forEach((key) => {
		if (data[key] === true) {
			let color = random_badge_style();
			html += `
				<span style="
					display:inline-block;
					padding:4px 10px;
					margin-right:6px;
					margin-bottom:6px;
					border-radius:999px;
					background:${color.bg};
					color:${color.text};
					font-size:12px;
					font-weight:600;
					letter-spacing:.2px;
				">${key}</span>
			`;
		}
	});

	return html;
}
