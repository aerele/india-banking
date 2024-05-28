frappe.ui.form.on('Payment Order', {
	onload(frm) {
		frm.set_df_property("payment_order_type", "options", [""].concat(["Bank Payment Request", "Payment Entry", "Purchase Invoice"]));
		frm.refresh_field("payment_order_type");

		frm.set_query("company_bank_account", function (doc) {
			return {
				filters: {
					company: doc.company,
					is_company_account: 1
				},
			};
		});
	},
	refresh(frm) {
		frm.set_df_property('summary', 'cannot_delete_rows', true);
		frm.set_df_property('summary', 'cannot_add_rows', true);

		frm.remove_custom_button("Payment Entry", "Get Payments from");
		frm.remove_custom_button("Payment Request", "Get Payments from");

		frm.set_df_property("payment_order_type", "options", [""].concat(["Bank Payment Request", "Payment Entry", "Purchase Invoice"]));
		frm.refresh_field("payment_order_type");

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
			frappe.db.get
			frm.add_custom_button(__('Payment Entry'), function() {
				frm.trigger("remove_row_if_empty");
				let docs = frm.doc.references?.map((doc)=>{return doc.payment_entry})

				erpnext.utils.map_current_doc({
					method: "india_banking.india_banking.doctype.bank_payment_request.bank_payment_request.make_payment_order",
					source_doctype: "Payment Entry",
					target: frm,
					args: {"ref_doctype": "Payment Entry"},
					setters: {
						party: frm.doc.supplier || "",
						paid_amount : ""
					},
					get_query_filters: {
						docstatus: 1,
						name: ["not in", docs],
						source_doctype: ["!=", "Bank Payment Request"]
					}
				});
			}, __("Get from"));
		};
		if (frm.doc.docstatus===1 && frm.doc.payment_order_type==='Bank Payment Request') {
			frm.remove_custom_button(__('Create Payment Entries'));
		}
		if (frm.doc.status == "Pending" && frm.doc.docstatus == 1) {
			if (frm.has_perm('write') && 'summary' in frm.doc) {
				var uninitiated_payments = 0;
				for(var i = 0; i < frm.doc.summary.length; i++) {
					if (!frm.doc.summary[i].payment_initiated) {
						uninitiated_payments += 1
					}
				}
				if (uninitiated_payments > 0) {
					if(frm.doc.company_bank == 'ICICI Bank'){
						frm.add_custom_button(__('Initiate Payment'), function() {
							frappe.call({
								method: "india_banking.india_banking.doc_events.payment_order.generate_payment_otp",
								freeze: true,
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
				}
			}
		}

		if ((frm.doc.status == "Pending" || frm.doc.status == "Initiated") && frm.doc.docstatus == 1) {
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
				query: "erpnext.setup.doctype.party_type.party_type.get_party_type",
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
	get_summary: function(frm) {
		if (frm.doc.docstatus > 0) {
			frappe.msgprint("Not allowed to change post submission");
			return
		}
		if (!frm.doc.company_bank_account > 0) {
			frappe.msgprint("Please Select Company Bank Account");
			return
		}
		frappe.call({
			method: "india_banking.india_banking.override.payment_order.get_party_summary",
			args: {
				references: frm.doc.references,
				company_bank_account: frm.doc.company_bank_account
			},
			freeze: true,
			callback: function(r) {
				if(r.message && !r.exc) {
					let summary_data = r.message
					frm.clear_table("summary");
					var doc_total = 0
					for (var i = 0; i < summary_data.length; i++) {
						doc_total += summary_data[i].amount
						let row = frm.add_child("summary");
						row.party_type = summary_data[i].party_type;
						row.party = summary_data[i].party;
						row.amount = summary_data[i].amount;
						row.bank_account = summary_data[i].bank_account;
						row.account = summary_data[i].account;
						row.mode_of_transfer = summary_data[i].mode_of_transfer;
						row.cost_center = summary_data[i].cost_center;
						row.project = summary_data[i].project;
						row.tax_withholding_category = summary_data[i].tax_withholding_category;
						row.reference_doctype = summary_data[i].reference_doctype;
						row.payment_entry = summary_data[i].payment_entry;
					}
					frm.refresh_field("summary");
					frm.doc.total = doc_total;
					frm.refresh_fields();
				}
			}
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
	}

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