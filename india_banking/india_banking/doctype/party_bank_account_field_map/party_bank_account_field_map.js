// Copyright (c) 2025, Aerele Technologies Private Limited and contributors
// For license information, please see license.txt

frappe.ui.form.on("Party Bank Account Field Map", {
	onload(frm) {
		if(frm.is_new()){
			frm.add_child("field_map", {"bank_account_field": "bank"})
			frm.add_child("field_map", {"bank_account_field": "branch_code"})
			frm.add_child("field_map", {"bank_account_field": "bank_account_no"})
			frm.refresh_field("field_map");
		}
	},
	refresh(frm) {
		frm.set_query("party_type", function () {
			return {
				query: "erpnext.setup.doctype.party_type.party_type.get_party_type",
			};
		});
		frm.set_df_property("field_map", "cannot_add_rows", true);
		frm.set_df_property("field_map", "cannot_delete_rows", true);
	},
});
