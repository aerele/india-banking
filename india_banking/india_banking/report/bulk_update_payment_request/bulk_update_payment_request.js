// Copyright (c) 2025, Aerele Technologies Private Limited and contributors
// For license information, please see license.txt
frappe.provide("erpnext.utils");

frappe.query_reports["Bulk Update Payment Request"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			reqd: 1,
			default: frappe.defaults.get_default("company"),
		},
		{
			fieldname: "party",
			label: __("Supplier"),
			fieldtype: "Link",
			options: "Supplier",
		},
		{
			fieldname: "transaction_date",
			label: __("Posting Date"),
			fieldtype: "Date Range",
		},
	],
	get_datatable_options(options) {
		options.checkboxColumn = true;
		return options;
	},
	onload: function (report) {
		let switch_icon = `
		<div title="Switch to Bulk Create Payment Request">
		<svg class="icon  icon-md" style="" aria-hidden="true" title="Bulk Create Payment Request">
			<use class="" href="#icon-change"></use>
		</svg>
		</div>`;
		let switch_element = frappe.query_report.page.add_inner_button(switch_icon, () => {
			frappe.set_route("query-report", "Bulk Create Payment Request");
		});
		if ($("#switch-button").length > 0) {
			$("#switch-button").remove();
			$(`[title="Bulk Update Payment Request"]`).parent().append(switch_element);
		} else {
			$(`[title="Bulk Update Payment Request"]`).parent().append(switch_element);
		}

		setTimeout(() => {
			$('[class="inner-group-button"]').hide();
		}, 1000);

		frappe.query_report.page.add_inner_button(
			"Payment Order",
			() => {
				frappe.set_route("List", "Payment Order");
			},
			"View"
		);

		report.page.add_action_item(__("Submit Payment Request"), function () {
			let checked_rows_indexes = report.datatable?.rowmanager.getCheckedRows();
			let checked_rows = checked_rows_indexes?.map((i) => report.data[i]);

			if (!checked_rows) {
				return;
			}

			if (checked_rows && checked_rows.length === 0) {
				frappe.throw("Select one or more rows");
			}
			let docnames = checked_rows.map((row) => row.payment_request);

			frappe.call({
				method: "india_banking.india_banking.report.bulk_update_payment_request.bulk_update_payment_request.update_bulk_payment_request",
				args: {
					docnames: docnames,
					filters: frappe.query_report.get_filter_values(),
				},
				async: false,
				callback: function (r) {
					if (!r.exc) {
						$('[data-original-title="Reload Report"]').click();
					}
				},
			});
		});
	},
};

let update_amount = function (data) {
	let docname = data.split("amt:")[0];
	let amount = data.split("amt:")[1];

	var d = new frappe.ui.Dialog({
		title: __("Update Amount"),
		fields: [
			{
				label: "Amount",
				fieldname: "amount",
				fieldtype: "Float",
				reqd: 1,
				default: amount,
			},
			{
				label: "Amount",
				fieldname: "total",
				fieldtype: "Float",
				reqd: 1,
				hidden: 1,
				default: amount,
			},
		],
		primary_action: function () {
			var data = d.get_values();

			if (data.amount > data.total) {
				frappe.throw(`values cannot be updated more than <b>${data.total}</b>.`);
			}
			frappe.call({
				method: "india_banking.india_banking.report.bulk_update_payment_request.bulk_update_payment_request.update_value",
				args: {
					doctype: "Payment Request",
					docname: docname,
					value: data.amount,
				},
				async: false,
				callback: function (r) {
					d.hide();
					if (!r.exc) {
						window.location.reload();
					}
				},
			});
		},
		primary_action_label: __("Update"),
	});
	d.show();
};

frappe.router.on("change", () => {
	window.location.reload();
});
