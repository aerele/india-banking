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
		frm.events.add_benificery_actions(frm)
	},
	add_benificery_actions(frm){
		debugger
		frm.add_custom_button("Add Benificery", frm.events.update_benificery_details(frm, "Create"), "Benificery Action")
		frm.add_custom_button("Update Benificery", frm.events.update_benificery_details(frm, "Update"), "Benificery Action")
		frm.add_custom_button("Discard Benificery", frm.events.update_benificery_details(frm, "Discard"), "Benificery Action")
		frm.add_custom_button("Approve Benificery", frm.events.update_benificery_details(frm, "Approve"), "Benificery Action")
		frm.add_custom_button("Reject Benificery", frm.events.update_benificery_details(frm, "Reject"), "Benificery Action")
		frm.add_custom_button("Suspend Benificery", frm.events.update_benificery_details(frm, "Suspend"), "Benificery Action")
	},
	update_benificery_details(frm, action){
		frm.call({
			method: "update_benificery_details",
			action: action,
			freeze: 1,
			freeze_message: "Updating..."
		})
	},
	onload(frm){
		if (frm.doc.workflow_state == 'Approved') {
			frm.set_read_only();
		}
	},
	after_workflow_action: function (frm) {
		if (frm.doc.workflow_state == 'Approved') {
			frm.set_read_only();
		}
		frm.reload_doc();
	},
});