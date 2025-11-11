// Copyright (c) 2024, Aerele Technologies Private Limited and contributors
// For license information, please see license.txt

frappe.ui.form.on("Backend Connector", {
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
