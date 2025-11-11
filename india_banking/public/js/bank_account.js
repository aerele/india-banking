frappe.ui.form.on("Bank Account", {
  refresh(frm) {
    if (frm.doc.is_company_account && !frm.doc.disabled) {
      frm.add_custom_button(__("Fetch Balance"), function () {
        frappe.call({
          method:
            "india_banking.india_banking.doctype.backend_connector.backend_connector.get_bank_balance",
          freeze: true,
          args: {
            bank_account_name: frm.doc.name,
          },
          callback: (res) => {
            cur_frm.reload_doc();
          },
        });
      });
      frm.add_custom_button(__("Fetch Statements"), function () {
        const dialog = new frappe.ui.Dialog({
          title: __("Fetch Statements"),
          fields: [
            {
              fieldname: "company",
              fieldtype: "Link",
              label: __("Company"),
              options: "Company",
              default: frm.doc.company,
              read_only: 1,
            },
            {
              fieldtype: "Column Break",
            },
            {
              fieldname: "bank_account",
              fieldtype: "Link",
              label: __("Bank Account"),
              options: "Bank Account",
              default: frm.doc.name,
              read_only: 1,
            },
            {
              fieldtype: "Section Break",
            },
            {
              fieldname: "from_date",
              fieldtype: "Date",
              label: __("From Date"),
            },
            {
              fieldtype: "Column Break",
            },
            {
              fieldname: "to_date",
              fieldtype: "Date",
              label: __("To Date"),
            },
          ],
          primary_action: () => {
            frm.call({
              method:
                "india_banking.india_banking.doctype.backend_connector.backend_connector.get_bank_statements",
              args: {
                bank_account_name: dialog.get_value("bank_account"),
                from_date: dialog.get_value("from_date"),
                to_date: dialog.get_value("to_date"),
              },
              freeze: true,
              freeze_message: __("Fetching..."),
              callback: function (r) {
                dialog.hide();
              },
            });
          },
          primary_action_label: __("Fetch"),
        });
        dialog.show();
      });
    }
    frappe.db
      .get_single_value(
        "India Banking Settings",
        "activate_workflow_on_bank_account"
      )
      .then((r) => {
        if (r && frm.doc.workflow_state == "Approved") {
          frm.set_read_only();
        }
      });
  },
  after_workflow_action: function (frm) {
    if (frm.doc.workflow_state == "Approved") {
      frm.set_read_only();
    }
    frm.reload_doc();
  },
});
