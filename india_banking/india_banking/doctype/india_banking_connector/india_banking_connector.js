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
