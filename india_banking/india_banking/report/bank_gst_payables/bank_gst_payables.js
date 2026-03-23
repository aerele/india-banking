// Copyright (c) 2025, Aerele Technologies Private Limited and contributors
// For license information, please see license.txt

frappe.query_reports["Bank GST Payables"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			reqd: 1,
			default: frappe.defaults.get_user_default("Company"),
		},
		{
			fieldname: "voucher_type",
			label: __("Voucher Type"),
			fieldtype: "Select",
			options: "Purchase Invoice\nPurchase Order",
			default: "Purchase Invoice",
			reqd: 1,
		},
		{
			fieldname: "supplier",
			label: __("Supplier"),
			fieldtype: "Link",
			options: "Supplier",
		},
	],
	get_datatable_options(options) {
		options.checkboxColumn = true;
		return options;
	},
	onload: function (report) {
		frappe.query_report.page.add_inner_button(
			"Payment Request",
			() => {
				frappe.set_route("List", "Payment Request");
			},
			"View"
		);
		setTimeout(() => {
			$('[class="inner-group-button"]').hide();
			$('[data-label="Create%20Card"]').hide();
			let status_message = frappe.query_report.$status.html();
			let newStatus = status_message.replace(
				"click on Rebuild",
				"click on Rebuild or Generate New Report"
			);

			let new_message = `<div style="color: #ff4008;">${newStatus}</>`;
			frappe.query_report.$status.html(new_message);
		}, 1000);

		report.page.add_action_item(__("Create Payment Request"), function () {
			let checked_rows_indexes = report.datatable?.rowmanager.getCheckedRows();
			let checked_rows = checked_rows_indexes?.map((i) => report.data[i]);

			if (!checked_rows) {
				return;
			}

			if (checked_rows && checked_rows.length === 0) {
				frappe.throw("Select one or more rows");
			}
			frappe.call({
				method: "india_banking.india_banking.report.bank_gst_payables.bank_gst_payables.create_bulk_payment_request",
				args: {
					vouchers: checked_rows,
					filters: frappe.query_report.get_filter_values(),
				},
				async: false,
				callback: function (r) {
					$('[data-original-title="Reload Report"]').click();
				},
			});
		});
	},
};

let pay_net_outstanding = function (data) {
	let invoice = data.split("amt:")[0];
	let net_outstanding = data.split("amt:")[1];
	frappe.call({
		method: "india_banking.india_banking.report.bank_gst_payables.bank_gst_payables.create_single_payment_request",
		args: {
			voucher_type: "Purchase Invoice",
			voucher_name: invoice,
			amount: net_outstanding,
			filters: frappe.query_report.get_filter_values(),
		},
		async: false,
		callback: function (r) {
			$('[data-original-title="Reload Report"]').click();
		},
	});
};

let pay_due_balance = function (data) {
	let order = data.split("amt:")[0];
	let due_balance = data.split("amt:")[1];
	frappe.call({
		method: "india_banking.india_banking.report.bank_gst_payables.bank_gst_payables.create_single_payment_request",
		args: {
			voucher_type: "Purchase Order",
			voucher_name: order,
			amount: due_balance,
			filters: frappe.query_report.get_filter_values(),
		},
		async: false,
		callback: function (r) {
			$('[data-original-title="Reload Report"]').click();
		},
	});
};
