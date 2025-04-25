frappe.ui.form.on('Bank Account', {
	refresh(frm) {
		if(frm.doc.is_company_account && frm.doc.is_company_account && !frm.doc.disabled){
			frm.add_custom_button(__('Fetch Balance'), function() {
				frappe.call({
					method: "india_banking.india_banking.doc_events.payment_order.get_bank_balance",
					freeze: true,
					args: {
						bank_name: frm.doc.name
					},
					callback: (res)=>{
						cur_frm.reload_doc()
					}
				})
			});
		}
		if (frm.doc.workflow_state == 'Approved') {
			frm.set_read_only();
		}
		frm.set_query("cost_center", function() {
			return {
				filters: {
					"is_group": 0,
					"disabled": 0,
					company: frm.doc.company
				}
			};
		});
		frm.set_query("beneficiary", function() {
			return {
				filters: {
					company: frm.doc.company,
					docstatus: ["!=", 2],
				}
			};
		});
		frm.events.add_beneficiary_actions(frm)
	},
	add_beneficiary_actions(frm){
		if(!frm.doc.beneficiary) {
			frm.add_custom_button("Add Beneficiary", ()=>frm.events.add_beneficiary(frm), "Beneficiary Action")
		}
		else{
			frappe.db.get_value("Beneficiary", frm.doc.beneficiary, "beneficiary_status", (r) => {
				let bene_status_tag = `<span class="indicator-pill no-indicator-dot whitespace-nowrap blue"><span>Beneficiary Status: ${r.beneficiary_status}</span></span>`
				$(`[title="${frm.doc.name}"]`).parent().append(bene_status_tag);
				if (r.beneficiary_status == "Draft") {
					frm.add_custom_button("Add Beneficiary", ()=>frm.events.submit_beneficiary(frm), "Beneficiary Action")
				}
				else if(r.beneficiary_status == 'Submitted') {
					frm.add_custom_button("Approve Beneficiary", ()=>frm.events.update_beneficiary_details(frm, "Approve"), "Beneficiary Action")
					frm.add_custom_button("Reject Beneficiary", ()=>frm.events.update_beneficiary_details(frm, "Reject"), "Beneficiary Action")
				}
				else if(['Approved', 'Rejected'].includes(r.beneficiary_status)) {
					frm.add_custom_button("Update Beneficiary", ()=>update_beneficiary_dialog(frm), "Beneficiary Action")
					if(r.beneficiary_status == 'Approved') {
						frm.add_custom_button("Suspend Beneficiary", ()=>frm.events.update_beneficiary_details(frm, "Suspend"), "Beneficiary Action")
					}
				}
				else if(r.beneficiary_status == 'Suspended') {
					frm.add_custom_button("Approve Beneficiary", ()=>frm.events.update_beneficiary_details(frm, "Approve"), "Beneficiary Action")
				}
			})
		}
	},

	add_beneficiary(frm){
		add_beneficiary_dialog(frm)
	},

	submit_beneficiary(frm){
		frm.call({
			method: "india_banking.india_banking.doctype.beneficiary.beneficiary.submit_beneficiary",
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
			method: "india_banking.india_banking.doctype.beneficiary.beneficiary.update_beneficiary",
			args: {
				beneficiary_id: frm.doc.beneficiary,
				action: action,
			},
			freeze: 1,
			freeze_message: `${action_map[action]}...`,
			callback: function (r) {
				frm.reload_doc();
			}
		})
	},

	after_workflow_action: function (frm) {
		if (frm.doc.workflow_state == 'Approved') {
			frm.set_read_only();
		}
		frm.reload_doc();
	},
});

// This function creates a dialog to add a beneficiary
function add_beneficiary_dialog(frm) {
	d = new frappe.ui.Dialog({
		title: __('Add Beneficiary'),
		size: "extra-large",
		fields: [
			{
				fieldname: 'bank_connector',
				label: __('Bank Connector'),
				fieldtype: 'Link',
				options: 'Bank Connector',
				reqd: 1,
				onchange() {
					if (this.value) {
						frappe.db.get_value('Bank Connector', this.value, 'bank', function (r) {
							d.set_value('connector_bank', r.bank);
							if(r.bank == frm.doc.bank){
								d.set_value('payment_type', "INHOUSE-TRANSFER");
							}
							else{
								d.set_value('payment_type', "INTERBANK-TRANSFER");
							}
						});

						if(!this.message) {
							this.message = __('The Beneficiary Name will be fetched from the bank account. If you wish to change it, please update it manually.')
							frappe.msgprint(this.message);
						}
					}
				},
				get_query: function () {
					return {
						filters: {
							"company": frm.doc.company,
						}
					};
				}
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
				fieldname: 'beneficiary_name',
				label: __('Beneficiary Name'),
				fieldtype: 'Data',
				options: 'Name',
				reqd: 1,
			},
			{
				fieldname: 'payment_type',
				label: __('Payment Type'),
				fieldtype: 'Data',
				options: 'Name',
				reqd: 1,
				read_only: 1,
			},
			{
				fieldname: 'mobile',
				label: __('Mobile'),
				fieldtype: 'Data',
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
				reqd: 1,
				read_only: 1,
			},
			{
				fieldname: 'bank_account_number',
				label: __('Bank Account No'),
				fieldtype: 'Data',
				read_only: 1,
				reqd: 1,
			},
			{
				fieldname: 'email',
				label: __('Email'),
				fieldtype: 'Data',
				options: 'Email',
				read_only: 1,
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
							d.set_value("limit_frequency", "")
							d.set_value("limit_on_amount", 0)
							d.set_value("limit_on_transactions", 0)
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
		primary_action_label: __('Add'),
		primary_action(values) {
			frm.call({
				method: "india_banking.india_banking.doctype.beneficiary.beneficiary.add_beneficiary",
				args: values,
				freeze: 1,
				freeze_message: "Adding...",
				callback: function (r) {
					if (r.message) {
						frm.reload_doc();
					}
				}
			})
			d.hide();
		}
	});
	d.set_value("bank_account", frm.doc.name);
	d.set_value("beneficiary_name", frm.doc.account_name.replace(/[^a-zA-Z0-9 ]/g, '').replace(/\s+/g, ' ').trim());
	d.set_value("bank_account_number", frm.doc.bank_account_no)
	d.set_value("mobile", frm.doc.mobile_number)
	d.set_value("email", frm.doc.email)
	d.show();
}

// This function creates a dialog to Update a beneficiary
async function update_beneficiary_dialog(frm) {
	let fields = ["bank_connector", "connector_bank", "beneficiary_name", "payment_type", "mobile", "bank_account", "email", "limit_level", "limit_frequency", "limit_on_transactions", "limit_on_amount"];
	let bene_details = {};
	await frappe.db.get_value("Beneficiary", frm.doc.beneficiary, fields, (r) => {
		bene_details = r;
	})

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
				fieldname: 'mobile',
				label: __('Mobile'),
				fieldtype: 'Data',
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
				read_only: 1,
			},
			{
				fieldname: 'bank_account_number',
				label: __('Bank Account No'),
				fieldtype: 'Data',
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
	d.set_value("bank_account", frm.doc.name);
	d.set_value("bank_account_number", frm.doc.bank_account_no)
	d.set_value("mobile", frm.doc.mobile_number)
	d.set_value("email", frm.doc.email)
	d.set_value("limit_level", bene_details.limit_level);
	d.set_value("limit_frequency", bene_details.limit_frequency)
	d.set_value("limit_on_transactions", bene_details.limit_on_transactions)
	d.set_value("limit_on_amount", bene_details.limit_on_amount)
	d.show();
}
