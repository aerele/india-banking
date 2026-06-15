// Copyright (c) 2026, Aerele Technologies Private Limited and contributors
// For license information, please see license.txt

frappe.ui.form.on("India Banking Connector", {
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
		frm.trigger("toggle_bulk_transaction");
		frm.trigger("show_connection_status");

		if (!frm.is_new()) {
			frm.add_custom_button(__("Check Connection"), () => {
				frappe.call({
					method: "india_banking.india_banking.doctype.india_banking_connector.india_banking_connector.check_connection",
					args: { connector_name: frm.doc.name },
					freeze: true,
					freeze_message: __("Testing connection..."),
					callback(r) {
						frm.reload_doc();
					},
				});
			});
		}
	},
	show_connection_status(frm) {
		const color_map = {
			Connected: "green",
			Failed: "red",
			"Not Connected": "orange",
		};
		const status = frm.doc.connection_status || "Not Connected";
		frm.page.set_indicator(__(status), color_map[status] || "gray");
	},
	toggle_bulk_transaction(frm) {
		frm.call({
			method: "india_banking.utils.get_bulk_transaction_banks",
			async: false,
			callback(r) {
				let show = 0;
				if (r.message?.includes(frm.doc.bank)) {
					show = 1;
				}
				frm.set_df_property("bulk_transaction", "hidden", !show);
			},
		});
	},
	after_save(frm) {
		frm.reload_doc();
	},
	bank_account(frm) {
		frm.trigger("toggle_bulk_transaction");
	},
	enqueue_large_payments_in_the_background(frm) {
		if (!frm.doc.enqueue_payments_threshold) {
			frm.set_value("enqueue_payments_threshold", 10);
		}
	},
	enable_payment_delay(frm) {
		if (!frm.doc.payment_call_interval) {
			frm.set_value("payment_call_interval", 10);
		}
	},
});
