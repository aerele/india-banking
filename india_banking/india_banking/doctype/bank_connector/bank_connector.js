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
		if (!frm.is_new()){
			frm.add_custom_button(__("Fetch Statements"), function () {
				const dialog = new frappe.ui.Dialog({
				  title: __("Fetch Statements"),
				  fields: [
					{
					  fieldname: "from_date",
					  fieldtype: "Date",
					  label: __("From Date"),
					},
					{
					  fieldtype: "Column Break",
					},
					{
					  fieldname: "to_date",
					  fieldtype: "Date",
					  label: __("To Date"),
					},
				  ],
				  primary_action: () => {
					frm.call({
						doc: frm.doc,
						method:
						"get_bank_statements",
						args: {
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
			}, "Actions");
		}
	},
});


