frappe.ui.form.on("Payment Request", {
	refresh(frm) {
		if (
			frm.doc.payment_request_type == "Outward" &&
			["Initiated", "Partially Paid"].includes(frm.doc.status)
		) {
			frm.remove_custom_button(__("Create Payment Entry"));
			frm.add_custom_button("Goto Payment Order", function () {
				frappe.set_route("List", "Payment Order");
			}).addClass("btn-primary");
		}
		set_payment_type_query(frm);
		set_bank_account_query(frm);
		frm.set_df_property(
			"conversion_rate",
			"description",
			"1 " + frm.doc.currency + " = [?] " + frm.doc.party_account_currency
		);
	},
	company(frm) {
		set_payment_type_query(frm);
		set_bank_account_query(frm);
	},
	mode_of_payment(frm) {
		set_bank_account_query(frm);
	},
	party_type(frm) {
		set_bank_account_query(frm);
		set_bank_account_query(frm);
	},
	party(frm) {
		set_bank_account_query(frm);
	},
});

function set_payment_type_query(frm) {
	frm.set_query("payment_type", function () {
		return {
			filters: {
				company: frm.doc.company,
			},
		};
	});
}

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
		company: frm.doc.company,
		disabled: 0,
	};
	frappe.db.get_single_value("India Banking Settings", "activate_workflow_on_bank_account").then((r) => {
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
