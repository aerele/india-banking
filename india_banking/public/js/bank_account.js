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
	},
	onload(frm){
		if (frm.doc.workflow_state == 'Approved') {
			frm.disable_form();
		}
		else {
			frm.fields.forEach((field) => {
				frm.set_df_property(field.df.fieldname, "read_only", "0");
			});
		}
	},
});