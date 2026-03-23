/* global INDICATORS */
INDICATORS["Payment Ordered"] = "blue";

frappe.listview_settings["Payment Request"].onload = function (listview) {
	listview.page.add_inner_button(
		__("New Payment Request(Adhoc)"),
		function () {
			frappe.new_doc("Payment Request", {
				payment_request_type: "Outward",
				transaction_date: frappe.datetime.get_today(),
				mode_of_payment: "Wire Transfer",
				is_adhoc: 1,
			});
		},
		"Action"
	);
};
