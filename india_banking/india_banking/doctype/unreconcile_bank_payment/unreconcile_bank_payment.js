// Copyright (c) 2026, Aerele Technologies Private Limited and contributors
// For license information, please see license.txt

frappe.ui.form.on("Unreconcile Bank Payment", {
	refresh(frm) {
		frm.set_query("voucher_type", function () {
			return {
				filters: {
					name: ["in", ["Payment Order"]],
				},
			};
		});

		frm.set_query("voucher_no", function (doc) {
			return {
				filters: {
					company: doc.company,
					docstatus: 1,
				},
			};
		});
	},
	get_allocations: function (frm) {
		frm.clear_table("allocations");
		frappe.call({
			method: "get_reference_from_payment_order",
			doc: frm.doc,
			callback: function (r) {
				if (r.message) {
					r.message.forEach((x) => {
						frm.add_child("allocations", {
							party_type: x.party_type,
							party: x.party,
							reference_type: x.reference_doctype,
							reference_name: x.reference_name,
							amount: x.amount,
							account: x.account,
							payment_request: x.payment_request,
						});
					});
					frm.refresh_fields();
				}
			},
		});
	},
});
