frappe.ui.form.on('Payment Request', {
	refresh(frm) {
		if(frm.doc.status == "Initiated") {
			frm.remove_custom_button(__('Create Payment Entry'))
		}
		frm.set_query("payment_type", function() {
			return {
				filters: {
					"company": frm.doc.company
				}
			};
		});
	},
	company (frm) {
		frm.set_query("payment_type", function() {
			return {
				filters: {
					"company": frm.doc.company
				}
			};
		});
	},
	mode_of_payment (frm) {
		var conditions = get_bank_query_conditions(frm);
		if (frm.doc.mode_of_payment == "Wire Transfer") {
			frm.set_query("bank_account", function() {
				return {
					filters: conditions
				};
			});
		}
	},
	party_type (frm) {
		var conditions = get_bank_query_conditions(frm);
		if (frm.doc.mode_of_payment == "Wire Transfer") {
			frm.set_query("bank_account", function() {
				return {
					filters: conditions
				};
			});
		}
	},
	party (frm) {
		var conditions = get_bank_query_conditions(frm);
		if (frm.doc.mode_of_payment == "Wire Transfer") {
			frm.set_query("bank_account", function() {
				return {
					filters: conditions
				};
			});
		}
	}
});

var get_bank_query_conditions = function(frm) {
	var conditions = {}
	if (frm.doc.party_type) {
		conditions["party_type"] = frm.doc.party_type;
	}
	if (frm.doc.party) {
		conditions["party"] = frm.doc.party;
	}
	if (frm.doc.mode_of_payment == "Wire Transfer") {
		frm.set_query("bank_account", function() {
			return {
				filters: conditions
			};
		});
	}
	return conditions;
};