// Copyright (c) 2024, Aerele Technologies Private Limited and contributors
// For license information, please see license.txt

frappe.ui.form.on("India Banking Settings", {
	refresh(frm) {
        frm.set_query("default_email_format", function() {
            return {
                filters: {
                    "doc_type": "Payment Entry"
                }
            }
        })
	},
});
