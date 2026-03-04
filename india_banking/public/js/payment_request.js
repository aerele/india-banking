frappe.ui.form.on("Payment Request", {
	refresh(frm) {
		if (
			frm.doc.payment_request_type == "Outward" &&
			["Initiated", "Partially Paid"].includes(frm.doc.status)
		) {
			frm.remove_custom_button(__("Create Payment Entry"));
			cur_frm.add_custom_button("Goto Payment Order", function () {
				frappe.set_route("List", "Payment Order");
			});
		}

		set_bank_account_query(frm);

		frm.dashboard.clear_headline();
		frm.dashboard.add_comment(
			__(
				"<b>Warning: </b>The Adhoc Payment Request feature is deprecated. Please create a Payment Entry and pull it into the Payment Order instead."
			),
			"yellow",
			true
		);
	},
	mode_of_payment(frm) {
		set_bank_account_query(frm);
	},
	party_type(frm) {
		set_bank_account_query(frm);
	},
	party(frm) {
		set_bank_account_query(frm);
	},
});

function set_bank_account_query(frm) {
	let conditions = get_bank_query_conditions(frm);
	frm.set_query("bank_account", function () {
		return {
			filters: conditions,
		};
	});
}

function get_bank_query_conditions(frm) {
	let conditions = {
		disabled: 0,
	};
	frappe.db.get_single_value("India Banking Settings", "enable_bank_account_workflow").then((r) => {
		if (r) {
			conditions["workflow_state"] = "Approved";
		}
	});
	if (frm.doc.party_type) {
		conditions["party_type"] = frm.doc.party_type;
	}
	if (frm.doc.party) {
		conditions["party"] = frm.doc.party;
	}
	return conditions;
}
