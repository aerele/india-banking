frappe.ui.form.on("Payment Order", {
  onload(frm) {
    // Set summary based on party or voucher
    frappe.db
      .get_single_value("India Banking Settings", "summarise_payment_based_on")
      .then((res) => {
        if (res === "Party") {
          frm.set_value("summarise_payment_based_on", res);
        }
      });

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
  },

  refresh(frm) {
    frm.remove_custom_button("Payment Entry", "Get Payments from");
    frm.remove_custom_button("Payment Request", "Get Payments from");

    frm.trigger("set_get_payments_from_buttons");

    frm.trigger("set_payment_and_status_buttons");

    frm.trigger("remove_button");
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
      },
      get_query_filters: {
        docstatus: 1,
        status: ["=", "Initiated"],
        bank: frm.doc.bank,
        name: ["not in", existing_payment_requests],
        company: frm.doc.company,
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
        name: ["not in", existing_payment_entries],
        source_doctype: ["!=", "Payment Request"],
        payment_type: "Pay",
      },
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
          default: frappe.defaults.get_user_default("company"),
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
        const unique_accounts = [
          ...new Set(
            (frm.doc.references || []).map(
              (reference) => reference.reference_name
            )
          ),
        ];

        return {
          query: "india_banking.overrides.journal_entry.get_bank_entry",
          filters: {
            docs: unique_accounts,
          },
        };
      },
    });
  },

  set_get_payments_from_buttons(frm) {
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
      payment_sources.forEach((source) => {
        frm.add_custom_button(
          source.label,
          () => frm.trigger(source.trigger),
          __("Get Payments from")
        );
      });
    }
  },

  set_payment_and_status_buttons(frm) {
    // Check if the document is in a pending state and user has write permissions
    if (
      frm.doc.status === "Pending" &&
      frm.doc.docstatus === 1 &&
      frm.has_perm("write")
    ) {
      // Check if any summary item has a payment status of "Pending"
      const has_pending_payments = frm.doc.summary.some(
        (item) => item.payment_status === "Pending"
      );

      if (has_pending_payments) {
        // Add a custom button to initiate payment
        frm.add_custom_button(__("Initiate Payment"), () => {
          frm.trigger("make_payment");
        });
      }
    }

    if (
      ["Pending", "Initiated"].includes(frm.doc.status) &&
      frm.doc.docstatus === 1 &&
      frm.has_perm("write")
    ) {
      // Check if any summary item has a payment status of "Initiated"
      const has_initiated_status = frm.doc.summary.some(
        (item) => item.payment_status === "Initiated"
      );

      if (has_initiated_status) {
        frm.add_custom_button(__("Get Status"), () => {
          frappe.call({
            method:
              "india_banking.india_banking.doctype.bank_connector.bank_connector.get_payment_status",
            freeze: true,
            freeze_message: __("Fetching payment status..."),
            args: {
              payment_order: frm.doc.name,
            },
            callback: function (response) {
              frm.reload_doc();
            },
          });
        });
      }
    }
  },

  make_payment: function (frm) {
    frappe.call({
      method:
        "india_banking.india_banking.doctype.bank_connector.bank_connector.make_payment",
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
          method:
            "india_banking.india_banking.doctype.bank_connector.bank_connector.make_payment",
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

  remove_button: function (frm) {
    // Remove the "Create Journal Entries" button
    frm.remove_custom_button("Create Journal Entries");

    // Check conditions for removing "Get Payments from" buttons
    if (
      (frm.doc.references.length > 0 && frm.doc.payment_order_type) ||
      frm.doc.docstatus != 0
    ) {
      // Define the mapping of payment_order_type to buttons
      const button_mapping = {
        "Payment Request": ["Bank Entry(JV)", "Payment Entry"],
        "Payment Entry": ["Bank Entry(JV)", "Payment Request"],
        "Journal Entry": ["Payment Request", "Payment Entry"],
      };

      // Get the relevant buttons based on the payment_order_type
      const buttons_to_remove = button_mapping[frm.doc.payment_order_type] || [];

      // Iterate over the buttons and remove them
      buttons_to_remove.forEach((button) => {
        frm.remove_custom_button(button, "Get Payments from");
      });
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
});
