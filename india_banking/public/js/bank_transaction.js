
frappe.ui.form.on('Bank Transaction', {
	refresh(frm) {
		frm.add_custom_button(__("Find Payments"), function () {
			let data = []
			frm.call({
				method: "india_banking.utils.find_payments",
				args: {
					"transaction_id": frm.doc.name,
				}
			}).then((res)=>{
				if(!res.exc && res.message.length > 0 ){
					showPaymentsDialog(frm, res.message)
				}else{
					frappe.msgprint("We could not find any record with the given filter")
				}
			})
		});
	},
})

function showPaymentsDialog(frm, payments_data = []) {
	const dialog = new frappe.ui.Dialog({
		size: "extra-large",
		title: __('Find Payments'),
		fields: [
			{
				fieldname: 'payments',
				fieldtype: 'Table',
				label: __('Payments'),
				fields: [
					{
						fieldname: 'party_type',
						options: 'Party Type',
						label: __('Party Type'),
						in_list_view: 1,
					},
					{
						fieldname: 'party',
						fieldtype: 'Dynamic Link',
						options: 'party_type',
						label: __('Party'),
						in_list_view: 1,
					},
					{
						fieldname: 'doctype',
						fieldtype: 'Link',
						options: 'DocType',
						label: __('DocType'),
						in_list_view: 1,
					},
					{
						fieldname: 'docname',
						fieldtype: 'Dynamic Link',
						options: 'doctype',
						label: __('Docname'),
						in_list_view: 1,
					},
					{
						fieldname: 'amount',
						fieldtype: 'Currency',
						label: __('Amount'),
						in_list_view: 1,
					},
				],
				data: payments_data // set dynamic data here
			}
		],
		primary_action_label: __('Update'),
		primary_action(values) {
			if (!values.payments || values.payments.length !== 1) {
				frappe.msgprint(__('Please select exactly one payment to update.'));
				return;
			}else{
				let payment_data = values.payments[0]
				frm.set_value("party_type", payment_data.party_type)
				frm.set_value("party", payment_data.party)
				frm.add_child("payment_entries", {
					"payment_document":  payment_data.doctype,
					"payment_entry":  payment_data.docname,
					"allocated_amount": payment_data.amount,
				})
				cur_frm.refresh_field("payment_entries")
			}
			dialog.hide();
		}
	});
	dialog.show();
}
