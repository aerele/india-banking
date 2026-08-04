// Copyright (c) 2025, Aerele Technologies Private Limited and contributors
// For license information, please see license.txt

frappe.ui.form.on("Beneficiary", {
	onload_post_render(frm){
		if(frm.is_new()){
		frm.call("get_last_max_number").then((res)=>{if(!res.exc){
			frm.set_value("beneficiary", res.message)
		}})}
	},
	refresh: function(frm) {
		frm.events.add_filters(frm);
		frm.events.add_beneficiary_actions(frm);
		frm.toggle_display("beneficiary", 1)
		if(!["Draft", "Submitted"].includes(frm.doc.beneficiary_status)) {
			frm.disable_save()
		}
	},
	beneficiary_status: function(frm) {
		if(frm.doc.beneficiary_status == "Draft") {
			frm.enable_save()
		}
	},
	bank_connector: function(frm) {
		if(frm.doc.bank_connector) {
			frappe.db.get_value('Bank Connector', frm.doc.bank_connector, 'bank', function(r) {
				frm.set_value('connector_bank', r.bank);
				frm.trigger('set_payment_type');
			});
		}
	},
	bank_account: function(frm) {
		if(frm.doc.bank_account) {
			frappe.db.get_value('Bank Account', frm.doc.bank_account, 'bank', function(r) {
				frm.set_value('bank', r.bank);
				frm.trigger('set_payment_type');
			});
		}
	},
	set_payment_type: function(frm) {
		if(frm.doc.bank == frm.doc.connector_bank){
			frm.set_value('payment_type', "INHOUSE-TRANSFER");
		}
		else if(frm.doc.bank && frm.doc.connector_bank && frm.doc.bank != frm.doc.connector_bank){
			frm.set_value('payment_type', "INTERBANK-TRANSFER");
		}
	},
	add_filters(frm){
		frm.set_query("bank_connector", function() {
			return {
				filters: {
					company: frm.doc.company,
				}
			};
		});
		frm.set_query("party_type", function() {
			return {
				filters: {
					name: ["in", ["Customer", "Supplier", "Employee"]],
				}
			};
		});
		frm.set_query("bank_account", function() {
			return {
				filters: {
					party_type: frm.doc.party_type,
					party: frm.doc.party,
				}
			};
		});
	},
	add_beneficiary_actions(frm){
		if (frm.doc.beneficiary_status == "Draft") {
			frm.add_custom_button("Add Beneficiary", ()=>frm.events.submit_beneficiary(frm), "Beneficiary Action")
		}
		else if(frm.doc.beneficiary_status == 'Modified') {
			frm.add_custom_button("Update Beneficiary", ()=>update_beneficiary_dialog(frm), "Beneficiary Action")
		}
		else if(frm.doc.beneficiary_status == 'Submitted') {
			frm.add_custom_button("Approve Beneficiary", ()=>frm.events.update_beneficiary_details(frm, "Approve"), "Beneficiary Action")
			frm.add_custom_button("Reject Beneficiary", ()=>frm.events.update_beneficiary_details(frm, "Reject"), "Beneficiary Action")
		}
		else if(['Approved', 'Rejected'].includes(frm.doc.beneficiary_status)) {
			frm.add_custom_button("Update Beneficiary", ()=>update_beneficiary_dialog(frm), "Beneficiary Action")
			if(frm.doc.beneficiary_status == 'Approved') {
				frm.add_custom_button("Suspend Beneficiary", ()=>frm.events.update_beneficiary_details(frm, "Suspend"), "Beneficiary Action")
			}
		}
		else if(frm.doc.beneficiary_status == 'Suspended') {
			frm.add_custom_button("Approve Beneficiary", ()=>frm.events.update_beneficiary_details(frm, "Approve"), "Beneficiary Action")
		}
	},
	submit_beneficiary(frm){
		frm.call({
			doc: frm.doc,
			method: "submit_beneficiary",
			args: {
				beneficiary_id: frm.doc.beneficiary,
			},
			freeze: 1,
			freeze_message: "Submitting...",
			callback: function (r) {
				frm.reload_doc();
			}
		})
	},
	update_beneficiary_details(frm, action){
		let action_map = {
			"Approve": "Approving",
			"Reject": "Rejecting",
			"Suspend": "Suspending"
		}
		frm.call({
			doc: frm.doc,
			method: "update_beneficiary",
			args: {
				action: action,
			},
			freeze: 1,
			freeze_message: (action_map[action] || "Updating") + " Beneficiary...",
			callback: function (r) {
				frm.reload_doc();
			}
		})
	},
	limit_level(frm){
		if(frm.doc.limit_level) {
			if(frm.doc.limit_level == "NONE") {
				frm.set_value("limit_frequency", "");
				frm.set_value("limit_on_transactions", 0);
				frm.set_value("limit_on_amount", 0);
			} else if(frm.doc.limit_level == "ACCOUNT") {
				frm.set_value("limit_frequency", "MONTHLY");
				if(!frm.doc.limit_on_transactions) {
					frm.set_value("limit_on_transactions", 300);
				}
				if(!frm.doc.limit_on_amount) {
					frm.set_value("limit_on_amount", 100000000);
				}
			} else if(frm.doc.limit_level == "BENEFICIARY") {
				frm.set_value("limit_frequency", "DAILY");
				if(!frm.doc.limit_on_transactions) {
					frm.set_value("limit_on_transactions", 10);
				}
				if(!frm.doc.limit_on_amount) {
					frm.set_value("limit_on_amount", 1000000);
				}
			}
		}
	},
});


// This function creates a dialog to Update a beneficiary
async function update_beneficiary_dialog(frm) {
	let bene_details = frm.doc;

	d = new frappe.ui.Dialog({
		title: __('Update Beneficiary Details'),
		size: "extra-large",
		fields: [
			{
				fieldname: 'bank_connector',
				label: __('Bank Connector'),
				fieldtype: 'Link',
				options: 'Bank Connector',
				read_only: 1,
			},
			{
				fieldtype: 'Column Break'
			},
			{
				fieldname: 'connector_bank',
				label: __('Connector Bank'),
				fieldtype: 'Link',
				options: 'Bank',
				fetch_from: 'bank_connector.bank',
				read_only: 1,
			},
			{
				fieldtype: 'Section Break',
				depends_on: 'eval: !!doc.bank_connector'
			},
			{
				fieldname: 'beneficiary',
				label: __('Beneficiary'),
				fieldtype: 'Data',
				options: 'Name',
				read_only: 1,
			},
			{
				fieldname: 'beneficiary_name',
				label: __('Beneficiary Name'),
				fieldtype: 'Data',
				options: 'Name',
				read_only: 1,
			},
			{
				fieldname: 'payment_type',
				label: __('Payment Type'),
				fieldtype: 'Data',
				options: 'Name',
				read_only: 1,
			},
			{
				fieldtype: 'Column Break'
			},
			{
				fieldname: 'bank_account',
				label: __('Bank Account'),
				fieldtype: 'Link',
				options: 'Bank Account',
				onchange() {
					if (this.value) {
						frappe.db.get_value('Bank Account', this.value, ['bank_account_no', "email", "mobile_number"], (r) => {
							d.set_value('bank_account_number', r.bank_account_no);
							d.set_value('email', r.email);
							d.set_value('mobile', r.mobile_number);
						});
					} else {
						d.set_value('bank_account_number', '');
					}
				},
				get_query() {
					return {
						filters: {
							company: frm.doc.company,
							party_type: frm.doc.party_type,
							party: frm.doc.party,
						}
					};
				}
			},
			{
				fieldname: 'bank_account_number',
				label: __('Bank Account No'),
				fieldtype: 'Data',
				fetch_from: 'bank_account.bank_account_no',
				read_only: 1,
			},
			{
				fieldname: 'email',
				label: __('Email'),
				fieldtype: 'Data',
				options: 'Email',
				read_only: 1,
			},
			{
				fieldname: 'mobile',
				label: __('Mobile'),
				fieldtype: 'Data',
				read_only: 1,
			},
			{
				fieldname: 'action',
				label: __('Action'),
				fieldtype: 'Data',
				default: "Update",
				hidden: 1,
			},
			{
				label: __('Beneficiary Limit Details'),
				fieldtype: 'Section Break',
				depends_on: 'eval: !!doc.bank_connector'
			},
			{
				fieldname: 'limit_level',
				label: __('Limit Level'),
				fieldtype: 'Select',
				options: 'NONE\nACCOUNT\nBENEFICIARY',
				default: "NONE",
				description: __('Select the limit level for the beneficiary.<br>1. NONE: No limit<br>2.ACCOUNT: Limit is set on the bank account monthly<br>3. BENEFICIARY: Limit is set on the beneficiary daily'),
				onchange() {
					if (this.value) {
						if(this.value == "NONE"){
						}else if(this.value == "ACCOUNT"){
							if(!d.get_value("limit_on_transactions")){
								d.set_value("limit_on_transactions", 300)
							}
							if(!d.get_value("limit_on_amount")){
								d.set_value("limit_on_amount", 100000000)
							}
							d.set_value("limit_frequency", "MONTHLY")
						}
						else if(this.value == "BENEFICIARY"){
							if(!d.get_value("limit_on_transactions")){
								d.set_value("limit_on_transactions", 10)
							}
							if(!d.get_value("limit_on_amount")){
								d.set_value("limit_on_amount", 1000000)
							}
							d.set_value("limit_frequency", "DAILY")
						}
					}
				},
			},
			{
				fieldtype: 'Column Break'
			},
			{
				fieldname: 'limit_frequency',
				label: __('Limit Frequency'),
				fieldtype: 'Select',
				options: '\nDAILY\nMONTHLY',
				depends_on: 'eval: doc.limit_level != "NONE"',
				read_only: 1,
			},
			{
				fieldname: 'limit_on_transactions',
				label: __('No of Transactions'),
				fieldtype: 'Int',
				default: 0,
				description: __('Enter the number of transactions allowed for the beneficiary. eg. 100'),
				depends_on: 'eval: doc.limit_level != "NONE"',
			},
			{
				fieldname: 'limit_on_amount',
				label: __('Limit on amount'),
				fieldtype: 'Currency',
				options: 'Currency',
				default: 0,
				description: __('Enter the limit on amount allowed for the beneficiary. eg. 100000'),
				depends_on: 'eval: doc.limit_level != "NONE"',
			},
		],
		primary_action_label: __('Update'),
		primary_action(values) {
			frm.call({
				method: "india_banking.india_banking.doctype.beneficiary.beneficiary.update_beneficiary_details",
				args: values,
				freeze: 1,
				freeze_message: "updating...",
				callback: function (r) {
					frm.reload_doc();
				}
			})
			d.hide();
		}
	});
	d.set_value("bank_connector", bene_details.bank_connector);
	d.set_value("connector_bank", bene_details.connector_bank);
	d.set_value("beneficiary", frm.doc.beneficiary);
	d.set_value("payment_type", bene_details.payment_type);
	d.set_value("beneficiary_name", bene_details.beneficiary_name);
	d.set_value("bank_account", frm.doc.bank_account);
	d.set_value("bank_account_number", frm.doc.bank_account_no)
	d.set_value("mobile", frm.doc.mobile)
	d.set_value("email", frm.doc.email)
	d.set_value("limit_level", bene_details.limit_level);
	d.set_value("limit_frequency", bene_details.limit_frequency)
	d.set_value("limit_on_transactions", bene_details.limit_on_transactions)
	d.set_value("limit_on_amount", bene_details.limit_on_amount)
	d.show();
}
