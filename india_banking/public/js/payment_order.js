frappe.ui.form.on('Payment Order', {
	onload(frm) {
		frm.set_df_property("payment_order_type", "options", [""].concat(["Bank Payment Request", "Payment Entry", "Purchase Invoice", "Payroll Entry"]));
		frm.refresh_field("payment_order_type");
		if(frm.is_new()){
			cur_frm.clear_table('references')
		}

		frm.set_query("company_bank_account", function (doc) {
			return {
				filters: {
					company: doc.company,
					is_company_account: 1,
					workflow_state: "Approved"
				},
			};
		});
		if(frm.is_new()){
			cur_frm.trigger("set_default_company_bank_account");
		}
		if (frm.is_new()) {
			frappe.db
			  .get_single_value(
				"India Banking Settings",
				"summarise_payment_based_on"
			  )
			  .then((res) => {
				  frm.doc.summarise_payment_based_on = res;
				  frm.refresh_fields()
			  });
		}
	},
	set_pending_payment_cancel_button(frm) {
		const has_pending_payment = frm.doc.summary?.filter(
			(item) => item.payment_status == "Pending"
		).length;
		if (
			has_pending_payment &&
			has_pending_payment < frm.doc.summary.length &&
			frm.doc.docstatus == 1
		){
			frm.add_custom_button(__("Cancel Pending Payments"), function () {
				show_update_status_dialog(frm);
			});
		}
	},
	refresh(frm) {
		frm.set_df_property('summary', 'cannot_delete_rows', true);
		frm.set_df_property('summary', 'cannot_add_rows', true);

		frm.remove_custom_button("Payment Entry", "Get Payments from");
		frm.remove_custom_button("Payment Request", "Get Payments from");

		frm.set_df_property("payment_order_type", "options", [""].concat(["Bank Payment Request", "Payment Entry", "Purchase Invoice"]));
		frm.refresh_field("payment_order_type");
		frm.trigger("set_pending_payment_cancel_button");

		if (frm.doc.docstatus == 0) {
			frm.add_custom_button(__('Bank Payment Request'), function() {
				frm.trigger("remove_row_if_empty");
				let docs = frm.doc.references?.map((doc)=>{return doc.bank_payment_request})

				erpnext.utils.map_current_doc({
					method: "india_banking.india_banking.doctype.bank_payment_request.bank_payment_request.make_payment_order",
					source_doctype: "Bank Payment Request",
					target: frm,
					args: {"ref_doctype": "Bank Payment Request"},
					setters: {
						party: frm.doc.supplier || "",
						grand_total: "",
					},
					get_query_filters: {
						docstatus: 1,
						status: ["in", ["Initiated"]],
						name: ["not in", docs],
						mode_of_payment: "Wire Transfer",
						transaction_date : ["<=", frm.doc.posting_date],
						company: frm.doc.company
					}
				});
			}, __("Get from"));

			//frm.add_custom_button(__('Payment Entry'), function() {
			//	frm.trigger("remove_row_if_empty");
			//	let docs = frm.doc.references?.map((doc)=>{return doc.payment_entry})
			//
			//	erpnext.utils.map_current_doc({
			//		method: "india_banking.india_banking.doctype.bank_payment_request.bank_payment_request.make_payment_order",
			//		source_doctype: "Payment Entry",
			//		target: frm,
			//		args: {"ref_doctype": "Payment Entry"},
			//		setters: {
			//			party: frm.doc.supplier || "",
			//			paid_amount : ""
			//		},
			//		get_query_filters: {
			//			docstatus: 1,
			//			name: ["not in", docs],
			//			source_doctype: ["!=", "Bank Payment Request"]
			//		}
			//	});
			//}, __("Get from"));
			frm.add_custom_button(__('Bank Entry (JV)'), function() {
				erpnext.utils.map_current_doc({
					method: "india_banking.india_banking.doctype.bank_payment_request.bank_payment_request.make_payment_order",
					source_doctype: "Journal Entry",
					target: frm,
					args: {"ref_doctype": "Journal Entry"},
					setters: [
						{
							fieldtype: "Link",
							label: "Company",
							fieldname: "company",
							options: "Company",
							default: frappe.defaults.get_user_default("company")
						},
						{
							fieldtype: "Select",
							label: "Entry Type",
							fieldname: "voucher_type",
							options: "Bank Entry",
							hidden: 1
						},
						{
							fieldtype: "Currency",
							label: "Amount",
							fieldname: "total",
							hidden: 1
						}
					],
					get_query: function () {
						let docs = frm.doc.references?.map((doc)=>{return doc.reference_name})
						let unique_accounts =  [...new Set(docs)]
						return {
							query: "india_banking.india_banking.doctype.bank_payment_request.bank_payment_request.get_bank_entry",
							filters: {
								docs: unique_accounts
							},
						};
					},
				});
			}, __("Get from"));
		}
		if (frm.doc.docstatus===1 && frm.doc.payment_order_type==='Bank Payment Request') {
			frm.remove_custom_button(__('Create Payment Entries'));
		}
		let is_pending = false
		let permitted = frappe.user.has_role("Payment Manager")
		if (["Pending", "Partially Initiated"].includes(frm.doc.status) && frm.doc.docstatus == 1 && permitted) {
			if (frm.has_perm('write') && 'summary' in frm.doc) {
				var uninitiated_payments = 0;
				for(var i = 0; i < frm.doc.summary.length; i++) {
					if (!frm.doc.summary[i].payment_initiated) {
						uninitiated_payments += 1
					}
					if(frm.doc.summary[i].payment_status == "Pending"){
						is_pending = true
					}
				}
				if (uninitiated_payments > 0 && is_pending) {
					frappe.db.get_value(
						"Bank Connector",
						{ bank: frm.doc.company_bank},
						"bulk_transaction"
					,(r)=>{
						if(r.bulk_transaction){
							frm.add_custom_button(__('Initiate Payment'), function() {
								frappe.call({
									method: "india_banking.india_banking.doc_events.payment_order.generate_payment_otp",
									freeze: true,
									freeze_message: "Initiating Payment...",
									args: {
										docname: frm.doc.name
									},
									callback: (res)=>{//
										if(!res.exc){
											frappe.prompt(
												{
													label: 'Enter OTP',
													place_holder: 'Enter',
													fieldname: 'otp',
													fieldtype: 'Data'
												}, (values) => {
												frappe.call({
													method: "india_banking.india_banking.doc_events.payment_order.make_bank_payment",
													freeze: 1,
													args: {
														docname: frm.doc.name,
														otp: values.otp,
													},
													callback: function(r) {
														if(r.message) {
															frappe.msgprint(r.message)
														}
														frm.reload_doc();
													}
												});
											},
											"Sent an OTP to the registered account number",
											"Proceed")
										}//
									}
								})
							});
						}else{
							frm.add_custom_button(__('Initiate Payment'), function() {
								frappe.call({
									method: "india_banking.india_banking.doc_events.payment_order.make_bank_payment",
									freeze: 1,
									freeze_message: "Initiating Payment...",
									args: {
										docname: frm.doc.name
									},
									callback: function(r) {
										if(r.message && !r.exc) {
											frappe.msgprint(r.message)
										}
										frm.reload_doc();
									}
								});
							});
						}
					})
				}
			}
		}

		if (["Initiated", "Pending", "Partially Initiated"].includes(frm.doc.status) && frm.doc.docstatus == 1) {
			if (frm.has_perm('write') && 'summary' in frm.doc) {
				var pending_status_check = 0
				for (var j = 0; j < frm.doc.summary.length; j++) {
					if(frm.doc.summary[j].payment_status == "Initiated") {
						pending_status_check += 1
					}
				}

				if (pending_status_check > 0) {
					frm.add_custom_button(__('Get Status'), function() {
						frappe.call({
							method: "india_banking.india_banking.doc_events.payment_order.get_payment_status",
							freeze: 1,
							freeze_message: "Fetching payment status....",
							args: {
								docname: frm.doc.name,
							},
							callback: function(r) {
								if(r.message && !r.exc) {
									frappe.msgprint(r.message)
								}
								frm.reload_doc();
							}
						});
					});
				}
			}
		}
		frm.set_query("party_type", "references" , function() {
			return {
				filters: {
                    "name": ["in", ["Supplier", "Employee"]]
                }
			};
		});
		frm.set_query("mode_of_transfer", "summary" , function() {
			return {
				filters: {
                    "disabled": 0
                }
			};
		});
	},

	remove_button: function(frm) {
		// remove custom button of order type that is not imported
		let label = ["Payment Request", "Purchase Invoice"];

		if (frm.doc.references.length > 0 && frm.doc.payment_order_type) {
			label = label.reduce(x => {
				x!= frm.doc.payment_order_type;
				return x;
			});
			frm.remove_custom_button(label, "Get from");
		}
	},
	get_summary: function (frm) {
		if (frm.doc.docstatus > 0) {
			frappe.msgprint("Not allowed to change post submission");
			return;
		}
		if (!frm.doc.company_bank_account > 0) {
			frappe.msgprint("Please Select Company Bank Account");
			return;
		}
		frappe.call({
			method: "india_banking.india_banking.override.payment_order.get_party_summary",
			args: {
				references: frm.doc.references,
				company_bank_account: frm.doc.company_bank_account,
				summarise_payment_based_on: frm.doc.summarise_payment_based_on,
			},
			freeze: true,
			callback: function (r) {
				if (r.message && !r.exc) {
					frm.clear_table("summary");
					const summary_data = r.message;
					let doc_total = 0;
					summary_data.forEach(function (item) {
						frm.add_child("summary", item);
						doc_total += item.amount; // Calculate total amount
					});

					// Set total amount in the form
					frm.doc.total = doc_total;
					frm.refresh_fields();
				}
			},
		});
	},
	update_status: function(frm) {
		if (frm.doc.docstatus != 1) {
			frappe.msgprint("Updating status is not allowed without submission");
			return
		}

		if (!frm.doc.approval_status) {
			frappe.msgprint("Updating status is not allowed without value");
			return
		}

		var selected_rows = frm.get_selected()
		if (!Object.keys(selected_rows).length || !"summary" in selected_rows){
			frappe.msgprint("No rows are selected");
			return
		}

		frappe.call({
			method: "india_banking.india_banking.doc_events.payment_order.modify_approval_status",
			args: {
				items: selected_rows.summary,
				approval_status: frm.doc.approval_status,
			},
			callback: function(r) {
				if(r.message && !r.exc) {
					var updated_count = 0
					for (var line_item in r.message) {
						if (r.message[line_item].status) {
							frappe.model.set_value("Payment Order Summary", line_item, "approval_status", r.message[line_item].message);
							updated_count += 1
						} else {
							frappe.msgprint(r.message[line_item].message)
						}
					}
					frappe.msgprint(updated_count + " record(s) updated.")
				}
				frm.dirty();
				frm.refresh_fields();
			}
		});
	},
	company(frm){
		cur_frm.trigger("set_default_company_bank_account");
	},
	set_default_company_bank_account(frm){
		if(frm.doc.company){
			frappe.db
			.get_value(
				"Bank Account",
				{ is_default: 1, is_company_account: 1, company: frm.doc.company },
				["name"]
			)
			.then((r) => {
				frm.set_value("company_bank_account", r.message.name);
			});
		}
	},
});

frappe.ui.form.on('Payment Order Summary', {
	setup: function(frm) {
		frm.set_query("party_type", function() {
			return {
				query: "erpnext.setup.doctype.party_type.party_type.get_party_type",
			};
		});
	}
})



const show_update_status_dialog = function (frm) {
	frm.data = [];
	const dialog = new frappe.ui.Dialog({
		title: __("Pending Payments"),
		size: "extra-large",
		fields: [
			{
				fieldtype: "HTML",
				options: `<p>Cancel any pending payments by updating the payment status to Failed.</p>`,
			},
			{
				fieldname: "summary",
				fieldtype: "Table",
				label: __("Summary"),
				data: frm.data,
				in_place_edit: true,
				cannot_add_rows: true,
				cannot_delete_rows: true,
				get_data: () => {
					return frm.data;
				},
				fields: [
					{
						label: __("Row Name"),
						fieldname: "row_name",
						fieldtype: "data",
						read_only: 1,
					},
					{
						label: __("payment_order"),
						fieldname: "payment_order",
						fieldtype: "data",
						hidden: 1,
					},
					{
						label: __("Party Type"),
						fieldname: "party_type",
						fieldtype: "Link",
						options: "DocType",
						in_list_view: 1,
						columns: 1,
						read_only: 1,
						get_query: () => {
							return {
								filters: {
									company: frm.doc.company,
									name: ["in", ["Supplier", "Employee"]],
								},
							};
						},
					},
					{
						label: __("Party"),
						fieldname: "party",
						fieldtype: "Dynamic Link",
						options: "party_type",
						columns: 2,
						in_list_view: 1,
						read_only: 1,
					},
					{
						label: __("Amount"),
						fieldname: "amount",
						fieldtype: "Currency",
						in_list_view: 1,
						columns: 1,
						read_only: 1,
					},
					{
						label: __("Status"),
						fieldname: "status",
						fieldtype: "Select",
						options: "\nPending\nFailed",
						columns: 1,
						in_list_view: 1,
					},
					{
						label: __("Payment Entry"),
						fieldname: "payment_entry",
						fieldtype: "Data",
						hidden: 1,
					},
				],
			},
		],
		primary_action: () => {
			frm.call({
				method:
					"india_banking.india_banking.doc_events.payment_order.cancel_pending_payments",
				args: {
					data: dialog.get_values()["summary"],
				},
				freeze: true,
				freeze_message: __("Cancelling..."),
				callback: function (r) {
					dialog.hide();
					frm.reload_doc();
				},
			});
		},
		primary_action_label: __("Update"),
	});

	frm.doc.summary.forEach((d) => {
		if (["Pending"].includes(d.payment_status)) {
			dialog.fields_dict.summary.df.data.push({
				payment_order: frm.doc.name,
				row_name: d.name,
				party_type: d.party_type,
				party: d.party,
				amount: d.amount,
				payment_entry: d.payment_entry,
			});
		}
	});

	frm.data = [];
	dialog.show();
	dialog.fields_dict.summary.grid.refresh();
	dialog.$wrapper.find(".grid-row-check").prop("disabled", 1);
};
