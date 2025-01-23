frappe.ui.form.on("Bank Account", {
  refresh(frm) {
    if (
      frm.doc.is_company_account &&
      !frm.doc.disabled
    ) {
      frm.add_custom_button(__("Fetch Balance"), function () {
        frappe.call({
          method:
            "india_banking.india_banking.doctype.bank_connector.bank_connector.get_bank_balance",
          freeze: true,
          args: {
            bank_account_name: frm.doc.name,
          },
          callback: (res) => {
            cur_frm.reload_doc();
          },
        });
      });
    }
    if (frm.doc.workflow_state == "Approved") {
      frm.set_read_only();
    }
  },
  onload(frm) {
    if (frm.doc.workflow_state == "Approved") {
      frm.set_read_only();
    }
  },
  after_workflow_action: function (frm) {
    if (frm.doc.workflow_state == "Approved") {
      frm.set_read_only();
    }
    frm.reload_doc();
  },
});
