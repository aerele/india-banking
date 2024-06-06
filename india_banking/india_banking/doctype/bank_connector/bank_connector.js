// Copyright (c) 2024, Aerele Technologies Private Limited and contributors
// For license information, please see license.txt

frappe.ui.form.on("Bank Connector", {
	refresh(frm) {
        frm.set_query("bank_account", function (doc) {
			return {
				filters: {
					disabled: 0,
					is_default: 1,
                    is_company_account: 1
				},
			};
		});
	},
});
