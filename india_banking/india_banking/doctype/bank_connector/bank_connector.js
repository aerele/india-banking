// Copyright (c) 2024, Aerele Technologies Private Limited and contributors
// For license information, please see license.txt

frappe.ui.form.on("Bank Connector", {
	refresh(frm) {
		frm.set_query("bank_account", function (doc) {
			return {
				filters: {
					disabled: 0,
					is_company_account: 1,
					company: doc.company,
				},
			};
		});
		frm.events.toggle_fields(frm);
	},
	bank_account(frm) {
		frm.events.toggle_fields(frm);
	},
	toggle_fields(frm) {
		if (frm.doc.bank === "CITI Bank") {
			if (frm.is_new()) {
				frm.set_value("integration_mode", "H2H");
			}
			frm.set_df_property("integration_mode", "hidden", 0);
		} else {
			if (frm.is_new()) {
				frm.set_value("integration_mode", "API");
			}
			frm.set_df_property("integration_mode", "hidden", 1);
		}
		frm.call("get_bulk_transaction_banks").then((res) => {
			if (res?.message.includes(frm.doc.bank)) {
				frm.set_df_property("bulk_transaction", "hidden", 0);
			}
		});
	},
});
