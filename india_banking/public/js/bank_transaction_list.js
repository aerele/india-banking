

frappe.listview_settings["Bank Transaction"] = {
    onload: function (listview) {
          listview.page.add_inner_button(__("Fetch Statements"), () => {
            make_statement_dialog();
          });
      },
  };

const make_statement_dialog = function () {
    const dialog = new frappe.ui.Dialog({
        title: __("Fetch Statements"),
        fields: [
        {
            fieldname: "bank_connector",
            fieldtype: "Link",
            label: __("Bank Connector"),
            options: "Bank Connector",
            reqd: 1,
            onchange: function (e) {
                const bank_connector = dialog.get_value("bank_connector");
                if (bank_connector) {
                    frappe.db.get_value("Bank Connector", bank_connector, "bank_account").then((r) => {
                        dialog.set_value("bank_account", r.message.bank_account);
                    });
                }
            },
        },
        {
            fieldtype: "Column Break",
        },
        {
            fieldname: "bank_account",
            fieldtype: "Link",
            label: __("Bank Account"),
            options: "Bank Account",
            fetch_from: "bank_connector.bank_account",
            reqd: 1,
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
        frappe.call({
            method:
            "india_banking.india_banking.doctype.bank_connector.bank_connector.get_bank_statements",
            args: {
                bank_account: dialog.get_value("bank_account"),
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
}