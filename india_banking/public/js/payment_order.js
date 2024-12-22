frappe.ui.form.on("Payment Order", {
  onload(frm) {
    if (frm.is_new()) {
      cur_frm.clear_table("references");
    }

    frm.set_query("company_bank_account", function (doc) {
      return {
        filters: {
          company: doc.company,
          is_company_account: 1,
          workflow_state: "Approved",
        },
      };
    });
    frm.set_query("mode_of_transfer", "summary", function () {
      return {
        filters: {
          disabled: 0,
        },
      };
    });
  },

  get_payments_from_payment_request(frm) {
    frm.trigger("remove_row_if_empty");
    let docs = frm.doc.references?.map((doc) => {
      return doc.payment_request;
    });

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
        name: ["not in", docs],
        company: frm.doc.company,
      },
    });
  },

  get_payments_from_payment_entry(frm) {
    frm.trigger("remove_row_if_empty");
    let docs = frm.doc.references?.map((doc) => {
      return doc.payment_entry;
    });

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
        name: ["not in", docs],
        source_doctype: ["!=", "Payment Request"],
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
          hidden: 1,
        },
        {
          fieldtype: "Currency",
          label: "Amount",
          fieldname: "total",
          hidden: 1,
        },
      ],
      get_query: function () {
        let docs = frm.doc.references?.map((doc) => {
          return doc.reference_name;
        });
        let unique_accounts = [...new Set(docs)];
        return {
          query: "india_banking.overrides.journal_entry.get_bank_entry",
          filters: {
            docs: unique_accounts,
          },
        };
      },
    });
  },

  refresh(frm) {
    frm.set_df_property("summary", "cannot_delete_rows", true);
    frm.set_df_property("summary", "cannot_add_rows", true);

    frm.remove_custom_button("Payment Entry", "Get Payments from");
    frm.remove_custom_button("Payment Request", "Get Payments from");

    if (frm.doc.docstatus == 0) {
      frm.add_custom_button(
        __("Payment Request"),
        function () {
          frm.trigger("get_payments_from_payment_request");
        },
        __("Get Payments from")
      );

      frm.add_custom_button(
        __("Payment Entry"),
        function () {
          frm.trigger("get_payments_from_payment_entry");
        },
        __("Get Payments from")
      );

      frm.add_custom_button(
        __("Bank Entry(JV)"),
        function () {
          frm.trigger("get_payments_from_journal_entry");
        },
        __("Get Payments from")
      );
    }

    let is_pending = false;
    if (frm.doc.status == "Pending" && frm.doc.docstatus == 1) {
      if (frm.has_perm("write") && "summary" in frm.doc) {
        var uninitiated_payments = 0;
        for (var i = 0; i < frm.doc.summary.length; i++) {
          if (!frm.doc.summary[i].payment_initiated) {
            uninitiated_payments += 1;
          }
          if (frm.doc.summary[i].payment_status == "Pending") {
            is_pending = true;
          }
        }
        if (uninitiated_payments > 0 && is_pending) {
          frm.add_custom_button(__("Initiate Payment"), function () {
            frm.trigger("make_payment");
          });
        }
      }
    }

    if (
      ["Pending", "Initiated"].includes(frm.doc.status) &&
      frm.doc.docstatus == 1
    ) {
      if (frm.has_perm("write") && "summary" in frm.doc) {
        var pending_status_check = 0;
        for (var j = 0; j < frm.doc.summary.length; j++) {
          if (frm.doc.summary[j].payment_status == "Initiated") {
            pending_status_check += 1;
          }
        }

        if (pending_status_check > 0) {
          frm.add_custom_button(__("Get Status"), function () {
            frappe.call({
              method:
                "india_banking.india_banking.doctype.bank_connector.bank_connector.get_payment_status",
              freeze: 1,
              freeze_message: "Fetching payment status....",
              args: {
                payment_order: frm.doc.name,
              },
              callback: function (r) {
                frm.reload_doc();
              },
            });
          });
        }
      }
    }

    frm.trigger("remove_button");
  },

  make_payment: function (frm) {
    frappe.call({
      method:
        "india_banking.india_banking.doctype.bank_connector.bank_connector.make_payment",
      freeze: true,
      freeze_message: "Initiating Payment...",
      args: {
        payment_order: frm.doc.name,
      },
      callback: (res) => {
        if (!res.exc && res.message) {
          if (res.message.otp_required) {
            frm.trigger("verify_otp");
          }
        }
      },
    });
  },

  verify_otp(frm) {
    frappe.prompt(
      {
        label: "Enter OTP",
        place_holder: "Enter",
        fieldname: "otp",
        fieldtype: "Data",
      },
      (values) => {
        frappe.call({
          method:
            "india_banking.india_banking.doctype.bank_connector.bank_connector.make_payment",
          freeze: 1,
          args: {
            payment_order: frm.doc.name,
            otp: values.otp || "",
          },
          callback: function (r) {
            // frm.reload_doc();
          },
        });
      },
      "Sent an OTP to the registered Mobile number",
      "Proceed"
    );
  },

  remove_button: function (frm) {
    // remove custom button of order type that is not importedz
    frm.remove_custom_button("Create Journal Entries");
    if (
      (frm.doc.references.length > 0 && frm.doc.payment_order_type) ||
      frm.doc.docstatus != 0
    ) {
      if (
        frm.doc.payment_order_type == "Payment Request" ||
        frm.doc.docstatus != 0
      ) {
        frm.remove_custom_button("Bank Entry(JV)", "Get Payments from");
        frm.remove_custom_button("Payment Entry", "Get Payments from");
      }
      if (
        frm.doc.payment_order_type == "Payment Entry" ||
        frm.doc.docstatus != 0
      ) {
        frm.remove_custom_button("Bank Entry(JV)", "Get Payments from");
        frm.remove_custom_button("Payment Request", "Get Payments from");
      }
      if (
        frm.doc.payment_order_type == "Payment Entry" ||
        frm.doc.docstatus != 0
      ) {
        frm.remove_custom_button("Payment Request", "Get Payments from");
        frm.remove_custom_button("Bank Entry(JV)", "Get Payments from");
      }
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
      },
      freeze: true,
      callback: function (r) {
        let is_party_wise = 0;
        if (r.message && !r.exc) {
          let summary_data = r.message;
          frm.clear_table("summary");
          var doc_total = 0;
          for (var i = 0; i < summary_data.length; i++) {
            if (summary_data[i].is_party_wise && !is_party_wise) {
              is_party_wise = 1;
            }
            doc_total += summary_data[i].amount;
            let row = frm.add_child("summary");
            row.party_type = summary_data[i].party_type;
            row.party = summary_data[i].party;
            row.amount = summary_data[i].amount;
            row.bank_account = summary_data[i].bank_account;
            row.account = summary_data[i].account;
            row.mode_of_transfer = summary_data[i].mode_of_transfer;
            row.cost_center = summary_data[i].cost_center;
            row.project = summary_data[i].project;
            row.tax_withholding_category =
              summary_data[i].tax_withholding_category;
            row.reference_doctype = summary_data[i].reference_doctype;
            row.reference_name = summary_data[i].reference_name;
            row.payment_entry = summary_data[i].payment_entry;
            row.journal_entry = summary_data[i].journal_entry;
            row.journal_entry_account = summary_data[i].journal_entry_account;
          }
          if (is_party_wise) {
            frm.set_value("is_party_wise", 1);
          } else {
            frm.set_value("is_party_wise", 0);
          }
          frm.refresh_field("summary");
          frm.doc.total = doc_total;
          frm.refresh_fields();
        }
      },
    });
  },
});
