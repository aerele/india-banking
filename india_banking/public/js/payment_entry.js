frappe.ui.form.on("Payment Entry", {
	refresh(frm) {
		if (
			frm.doc.docstatus != 1 ||
			frm.doc.payment_type != "Pay" ||
			frm.doc.mode_of_payment != "Wire Transfer"
		)
			return;

		Promise.all([
			frappe.call({ method: "india_banking.utils.get_connected_bank_accounts" }),
			frappe.db.get_list("Payment Order", {
				filters: [
					["Payment Order Reference", "payment_entry", "=", frm.doc.name],
					["docstatus", "!=", 2],
				],
				limit: 1,
			}),
		]).then(([bank_res, po_res]) => {
			if (bank_res.message && bank_res.message.includes(frm.doc.bank_account) && !po_res.length) {
				frm.add_custom_button(__("Initiate Payment"), () => {
					show_mode_of_transfer_dialog(frm);
				});
			}
		});
	},
});

function show_mode_of_transfer_dialog(frm) {
	let dialog = new frappe.ui.Dialog({
		title: __("Select Mode of Transfer"),
		fields: [
			{
				label: __("Mode of Transfer"),
				fieldname: "mode_of_transfer",
				fieldtype: "Link",
				options: "Mode of Transfer",
				reqd: true,
				get_query: () => ({ filters: { disabled: 0 } }),
			},
		],
		primary_action_label: __("Proceed"),
		primary_action(values) {
			dialog.hide();
			create_and_initiate(frm, values.mode_of_transfer);
		},
	});
	dialog.show();
}

function create_and_initiate(frm, mode_of_transfer) {
	frappe.call({
		method: "india_banking.overrides.payment_order.create_payment_order",
		freeze: true,
		freeze_message: __("Creating Payment Order..."),
		args: {
			payment_entry: frm.doc.name,
			default_mode_of_transfer: mode_of_transfer,
		},
		callback: function (r) {
			if (r.message) {
				initiate_payment(frm, r.message);
			}
		},
	});
}

function initiate_payment(frm, payment_order, otp) {
	frappe.call({
		method: "india_banking.india_banking.doctype.india_banking_connector.india_banking_connector.make_payment",
		freeze: true,
		freeze_message: __("Initiating Payment..."),
		args: {
			payment_order: payment_order,
			...(otp && { otp }),
		},
		callback: function (r) {
			if (r.message && r.message.otp_required) {
				verify_otp(frm, payment_order);
			}
			frm.reload_doc();
		},
	});
}

function verify_otp(frm, payment_order) {
	frappe.prompt(
		{
			label: __("Enter OTP"),
			placeholder: __("Enter the OTP sent to your registered mobile number"),
			fieldname: "otp",
			fieldtype: "Data",
			reqd: true,
		},
		(values) => {
			let otp = (values.otp || "").trim();
			if (!otp) {
				frappe.msgprint({
					title: __("Invalid OTP"),
					message: __("Please enter a valid OTP."),
					indicator: "red",
				});
				return;
			}
			initiate_payment(frm, payment_order, otp);
		},
		__("OTP sent to your registered mobile number"),
		__("Proceed")
	);
}
