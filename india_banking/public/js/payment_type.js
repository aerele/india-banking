frappe.ui.form.on('Payment Type', {
	refresh(frm) {
		frm.set_query("account", function() {
			return {
				filters: {
					"is_group": 0,
					"disabled": 0,
                    "account_type": "Payable"
				}
			};
		});
	}
})