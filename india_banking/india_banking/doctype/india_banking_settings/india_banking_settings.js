// Copyright (c) 2024, Aerele Technologies Private Limited and contributors
// For license information, please see license.txt

frappe.ui.form.on("India Banking Settings", {
	refresh(frm) {
		if (frappe.user.has_role("System Manager")) {
			frm.add_custom_button(__("Create Custom Fields"), () => {
				frappe.confirm(__("Create any missing India Banking custom fields now?"), () => {
					frm.call({
						method: "create_custom_fields",
						doc: frm.doc,
						freeze: true,
						freeze_message: __("Creating custom fields..."),
					});
				});
			});
		}
		frm.set_query("email_format", "payment_notification", function () {
			return {
				filters: {
					doc_type: "Payment Entry",
				},
			};
		});
		frm.get_field("allowed_payment_doctypes").$wrapper.click(() => {
			update_allow_doctypes(frm);
		});
		frm.set_query("doctype_name", "doctype_naming_series", () => {
			return {
				filters: {
					name: ["in", ["Payment Request", "Payment Order", "Payment Entry"]],
				},
			};
		});
	},
	auto_post_payments(frm) {
		if (frm.doc.retry_interval_minutes == 0) {
			frm.set_value("retry_interval_minutes", 5);
		}
		if (frm.doc.batch_size == 0) {
			frm.set_value("batch_size", 20);
		}
	},
});

const update_allow_doctypes = function (frm) {
	frm.data = [];
	const dialog = new frappe.ui.Dialog({
		title: __("Allowed Doctypes"),
		size: "small",
		fields: [
			{
				fieldname: "allowed_doctypes",
				fieldtype: "Table",
				label: __("Doctypes"),
				data: frm.data,
				in_place_edit: true,
				cannot_add_rows: true,
				cannot_delete_rows: true,
				get_data: () => {
					return frm.data;
				},
				fields: [
					{
						label: __("Doctype"),
						fieldname: "doctype",
						fieldtype: "Data",
						read_only: 1,
						in_list_view: 1,
					},
					{
						label: __("Allow"),
						fieldname: "allow",
						fieldtype: "Check",
						in_list_view: 1,
					},
				],
			},
		],
		primary_action: () => {
			let allowed = "";

			dialog.get_values().allowed_doctypes.forEach((ele) => {
				if (ele.allow) {
					allowed += ele.doctype + "\n";
				}
			});

			if (allowed) {
				frm.set_value("allowed_payment_doctypes", allowed);
				frm.save();
				dialog.hide();
			}
		},
		primary_action_label: __("Update"),
	});

	frm.call({
		method: "india_banking.utils.get_allowed_payment_doctypes",
		async: false,
		callback(r) {
			if (r.message) {
				r.message.forEach((d) => {
					let allowed = frm.doc.allowed_payment_doctypes.split("\n").includes(d);
					dialog.fields_dict.allowed_doctypes.df.data.push({
						doctype: d,
						allow: allowed,
					});
				});
				dialog.show();
				dialog.fields_dict.allowed_doctypes.grid.refresh();
			}
		},
	});
};
