frappe.ui.form.on("Bank Account", {
	onload(frm) {
		if (frm.doc.workflow_state == "Approved") {
			frm.set_read_only();
		}
	},
	refresh(frm) {
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
