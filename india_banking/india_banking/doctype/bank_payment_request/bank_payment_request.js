// Copyright (c) 2024, Aerele Technologies Private Limited and contributors
// For license information, please see license.txt

frappe.ui.form.on('Bank Payment Request', {
	setup: function (frm) {
		frm.set_query("party_type", function () {
			return {
				filters: {
                    "name": ["in", ["Supplier", "Employee"]]
                }
			};
		});
	},

	onload_post_render: function(frm) {
		if (frm.doc.__islocal && frm.doc.bank_account) {
			frm.events.get_default_beneficiary(frm);
		}
	},

	refresh(frm) {
		frm.set_query("payment_type", function() {
			return {
				filters: {
					"company": frm.doc.company
				}
			};
		});

		frm.set_query("cost_center", function() {
			return {
				filters: {
					"is_group": 0,
					"disabled": 0
				}
			};
		});

		frm.set_query("mode_of_payment", function() {
			return {
				filters: {
					"name": "Wire Transfer"
				}
			};
		});

		frm.set_query("beneficiary", function() {
			return {
				filters: {
					"bank_account": frm.doc.bank_account,
					"beneficiary_status": "Approved"
				}
			};
		});

		frm.set_query("beneficiary", function() {
			return {
				filters: {
					"bank_account": frm.doc.bank_account,
					"company": frm.doc.company,
					"party_type": frm.doc.party_type,
					"party": frm.doc.party,
					"beneficiary_status": "Approved"
				}
			};
		});

		setTimeout(() => {
			frm.trigger('toggle_custom_button')
		}, 500);
		if (frm.doc.docstatus == 1) {
			frm
			.add_custom_button("Goto Payment Order", function () {
			frappe.set_route("List", "Payment Order");
			})
			.addClass("btn-primary");
		}
	},
	toggle_custom_button(frm){
		if(frm.doc.status == "Initiated") {
			frm.remove_custom_button(__('Create Payment Entry'))
		}
	},

	company (frm) {
		frm.trigger("update_payment_type")
		frm.set_query("payment_type", function() {
			return {
				filters: {
					"company": frm.doc.company
				}
			};
		});
	},
	update_payment_type(frm){
		frappe.db.get_value("Payment Type",
			{
				"is_default": 1,
				"company": frm.doc.company
			},
			["name"],
			(res)=>{
				if(res.name){
					frm.set_value("payment_type", res.name)
				}
			})
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
	},
	bank_account (frm) {
		if (frm.doc.mode_of_payment == "Wire Transfer") {
			frm.events.get_default_beneficiary(frm);
		}
	},
	get_default_beneficiary(frm) {
		frm.call("get_default_beneficiary").then((r) => {
			if (r.message) {
				frm.set_value("beneficiary", r.message);
			} else {
				frappe.msgprint(__("No approved beneficiary found for the selected bank account."));
			}
		});
	},
});

const get_bank_query_conditions = function(frm) {
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
