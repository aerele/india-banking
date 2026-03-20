frappe.ui.form.on("Payment Order", {
	onload(frm) {
		// Set summary based on party or voucher
		if (frm.doc.docstatus == 0) {
			frappe.db
				.get_single_value("India Banking Settings", "summarise_payment_based_on")
				.then((res) => {
					if (!res.exc) {
						frm.set_value("summarise_payment_based_on", res);
					}
				});
		}

		// Clear the references table for new documents
		if (frm.is_new()) {
			if (frm.doc.references) {
				cur_frm.clear_table("references");
			}
		}

		// Set query for the company_bank_account field
		frm.set_query("company_bank_account", () => {
			return {
				filters: {
					company: frm.doc.company,
					is_company_account: 1,
				},
			};
		});

		// Set query for the mode_of_transfer field in the summary child table
		frm.set_query("mode_of_transfer", "summary", () => {
			return {
				filters: {
					disabled: 0,
				},
			};
		});
		frm.set_query("default_mode_of_transfer", () => {
			return {
				filters: {
					disabled: 0,
				},
			};
		});

		// Set properties for the summary table
		const summary_field = "summary";
		frm.set_df_property(summary_field, "cannot_delete_rows", true);
		frm.set_df_property(summary_field, "cannot_add_rows", true);

		frm.events.show_balace(frm);
	},

	async update_bank_balance(frm, field) {
		const bank_account = field.value;
		field.set_description("");
		if (!bank_account) return;

		let { message } = await frappe.call({
			method: "india_banking.india_banking.doctype.bank_connector.bank_connector.get_bank_balance",
			args: { bank_account_name: bank_account },
		});
		const has_valid_balance = message !== null && message !== undefined;
		const indicator_color = has_valid_balance ? "green" : "orange";
		const balance_display = has_valid_balance ? message : __("Unavailable");
		const balance_status = $(
			`<div class="d-flex indicator ${indicator_color}">
			Balance:&nbsp;<strong>${balance_display}</strong>
			</div>
			<div>
				<span class="text-right ml-auto">
					<span style="font-size: 12px; color: gray; padding-right: 15px;">
						Last Updated: ${frappe.datetime.now_datetime()}
					</span>
					<svg class="icon icon-sm reload-balance" style="cursor: pointer;">
						<use href="#icon-refresh"></use>
					</svg>
				</span>
			</div>
			`
		);

		balance_status.find(".reload-balance").on("click", async function () {
			await frm.events.update_bank_balance(frm, field);
		});
		return field.set_description(balance_status);
	},

	refresh(frm) {
		// // Remove all custom buttons first
		const custom_buttons = ["Payment Request", "Payment Entry"];

		Object.entries(frm.custom_buttons)?.map((label) => {
			if (frm.custom_buttons[label[0]] && custom_buttons.includes(label[0])) {
				frm.remove_custom_button(label[0], "Get Payments from");
			}
		});

		cur_frm.$wrapper.find(`[data-label="Create%20Journal%20Entries"]`).remove();

		frm.trigger("set_get_payments_from_buttons");
		frm.trigger("set_payment_and_status_buttons");
		frm.trigger("set_pending_payment_cancel_button");
	},

	set_pending_payment_cancel_button(frm) {
		const has_pending_payment = frm.doc.summary?.filter(
			(item) => item.payment_status == "Pending"
		).length;
		if (
			has_pending_payment &&
			has_pending_payment < frm.doc.summary.length &&
			frm.doc.docstatus == 1
		) {
			frm.add_custom_button(__("Cancel Pending Payments"), function () {
				show_update_status_dialog(frm);
			});
		}
	},
	async set_get_payments_from_buttons(frm) {
		if (frm.doc.docstatus === 0) {
			// Define an array of payment sources and their respective triggers
			const payment_sources = [
				{
					label: __("Payment Request"),
					trigger: "get_payments_from_payment_request",
				},
				{
					label: __("Payment Entry"),
					trigger: "get_payments_from_payment_entry",
				},
				{
					label: __("Bank Entry(JV)"),
					trigger: "get_payments_from_journal_entry",
				},
			];

			// Add custom buttons for each payment source
			for (const source of payment_sources) {
				const res = await frappe.db.get_single_value(
					"India Banking Settings",
					"allowed_payment_doctypes"
				);
				if (res.split("\n").includes(source.label)) {
					if (
						frm.doc.payment_order_type == source.label ||
						(source.label == "Bank Entry(JV)" &&
							frm.doc.payment_order_type == "Journal Entry")
					) {
						frm.add_custom_button(
							source.label,
							() => frm.trigger(source.trigger),
							__("Get Payments from")
						);
					} else if (!frm.doc.payment_order_type) {
						frm.add_custom_button(
							source.label,
							() => frm.trigger(source.trigger),
							__("Get Payments from")
						);
					}
				}
			}
		}
	},

	get_payments_from_payment_request(frm) {
		// Ensure references table is clean before processing
		frm.trigger("remove_row_if_empty");

		// Collect existing payment requests from references table, if any
		const existing_payment_requests = (frm.doc.references || []).map(
			(reference) => reference.payment_request
		);

		// Use map_current_doc utility to fetch and map payment requests
		erpnext.utils.map_current_doc({
			method: "india_banking.overrides.payment_request.make_payment_order",
			source_doctype: "Payment Request",
			target: frm,
			setters: {
				party_type: "",
				party: "",
				grand_total: "",
				currency: "INR",
			},
			get_query_filters: {
				docstatus: 1,
				status: ["=", "Initiated"],
				bank: frm.doc.bank,
				name: ["not in", existing_payment_requests],
				company: frm.doc.company,
				transaction_date: ["<=", frappe.datetime.get_today()],
			},
		});
	},

	get_payments_from_payment_entry(frm) {
		// Ensure references table is clean before processing
		frm.trigger("remove_row_if_empty");

		// Collect existing payment entries from the references table, if any
		const existing_payment_entries = (frm.doc.references || []).map(
			(reference) => reference.payment_entry
		);

		// Use map_current_doc utility to fetch and map payment entries
		erpnext.utils.map_current_doc({
			method: "india_banking.overrides.payment_entry.make_payment_order",
			source_doctype: "Payment Entry",
			target: frm,
			setters: {
				party: "",
				paid_amount: "",
			},
			get_query_filters: {
				docstatus: 1,
				existing_payment_entries: existing_payment_entries,
				source_doctype: ["!=", "Payment Request"],
				payment_type: "Pay",
				mode_of_payment: "Wire Transfer",
				bank_account: frm.doc.company_bank_account,
			},
			get_query_method: "india_banking.overrides.payment_entry.get_payment_entry",
		});
	},

	get_payments_from_journal_entry(frm) {
		erpnext.utils.map_current_doc({
			method: "india_banking.overrides.journal_entry.make_payment_order",
			source_doctype: "Journal Entry",
			target: frm,
			setters: [
				{
					fieldtype: "Link",
					label: "Company",
					fieldname: "company",
					options: "Company",
					default: frm.doc.company || frappe.defaults.get_user_default("company"),
				},
				{
					fieldtype: "Select",
					label: "Entry Type",
					fieldname: "voucher_type",
					options: "Bank Entry",
					hidden: true,
				},
				{
					fieldtype: "Currency",
					label: "Amount",
					fieldname: "total",
					hidden: true,
				},
			],
			get_query: function () {
				// Extract unique reference names from the references table
				const existing_journal_entries = [
					...new Set(
						(frm.doc.references || []).map((reference) => reference.reference_name)
					),
				];
				return {
					query: "india_banking.overrides.journal_entry.get_bank_entry",
					filters: {
						docs: existing_journal_entries,
						company_account: frm.doc.account,
					},
				};
			},
		});
	},

	set_payment_and_status_buttons(frm) {
		// Check if the document is in a pending state and user has write permissions
		if (frm.doc.docstatus === 1 && frm.has_perm("write")) {
			// Check if any summary item has a payment status of "Pending"
			const has_pending_payments = frm.doc.summary.some(
				(item) => item.payment_status === "Pending"
			);

			if (frappe.user_roles.includes("Payment Manager") && has_pending_payments) {
				// Add a custom button to initiate payment
				frm.add_custom_button(__("Initiate Payment"), () => {
					frm.trigger("make_payment");
				});
			}
		}

		if (frm.doc.docstatus === 1 && frm.has_perm("write")) {
			const has_initiated_or_non_pending = frm.doc.summary.some(
				(item) => item.payment_status === "Initiated" || item.payment_status !== "Pending"
			);

			if (has_initiated_or_non_pending) {
				frm.dashboard.add_comment(
					"Payment is already initiated. Check the status using the 'Get Status' button before trying again.",
					"blue",
					false
				);
				frm.add_custom_button(__("Get Status"), () => {
					frappe.call({
						method: "india_banking.india_banking.doctype.bank_connector.bank_connector.get_payment_status",
						freeze: true,
						freeze_message: __("Fetching payment status..."),
						args: {
							payment_order: frm.doc.name,
						},
						callback: function () {
							frm.reload_doc();
						},
					});
				});
			}
		}
	},

	make_payment: function (frm) {
		frappe.call({
			method: "india_banking.india_banking.doctype.bank_connector.bank_connector.make_payment",
			freeze: true,
			freeze_message: __("Initiating Payment..."),
			args: {
				payment_order: frm.doc.name,
			},
			callback: (res) => {
				if (res.message && res.message.otp_required) {
					// If OTP is required, trigger OTP verification
					frm.trigger("verify_otp");
				}

				// Reload the form to reflect any changes (whether OTP is required or not)
				frm.reload_doc();
			},
		});
	},

	verify_otp(frm) {
		frappe.prompt(
			{
				label: __("Enter OTP"),
				place_holder: "Enter the OTP sent to your registered mobile number",
				fieldname: "otp",
				fieldtype: "Data",
				reqd: true, // Make the OTP field mandatory
			},
			(values) => {
				// Ensure the OTP is not blank
				const otp = values.otp || "";
				if (!otp.trim()) {
					frappe.msgprint({
						title: __("Invalid OTP"),
						message: __("Please enter a valid OTP."),
						indicator: "red",
					});
					return;
				}

				frappe.call({
					method: "india_banking.india_banking.doctype.bank_connector.bank_connector.make_payment",
					freeze: true,
					freeze_message: __("Verifying OTP and processing payment..."),
					args: {
						payment_order: frm.doc.name,
						otp: otp,
					},
					callback: function (r) {
						if (!r.exc) {
							frm.reload_doc(); // Reload form to reflect changes
						}
					},
				});
			},
			__("Sent an OTP to your registered mobile number"),
			__("Proceed")
		);
	},

	summarise_payment_based_on(frm) {
		if (frm.doc.company_bank_account) {
			frm.trigger("get_summary");
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
			method: "india_banking.overrides.payment_order.get_party_summary",
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
	company(frm) {
		cur_frm.trigger("set_default_company_bank_account");
	},
	set_default_company_bank_account(frm) {
		if (frm.doc.company) {
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
	company_bank_account(frm) {
		frm.events.show_balace(frm);
	},
	show_balace(frm) {
		frappe.db
			.get_single_value("India Banking Settings", "show_bank_balance_in_payment_order")
			.then((r) => {
				if (r) {
					frm.events.update_bank_balance(frm, frm.get_field("company_bank_account"));
				}
			});
	},
});

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
				method: "india_banking.india_banking.doc_events.payment_order.cancel_pending_payments",
				args: {
					data: dialog.get_values()["summary"],
					payment_order_type: frm.doc.payment_order_type,
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
		if (["Pending", "Initiated"].includes(d.payment_status)) {
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
