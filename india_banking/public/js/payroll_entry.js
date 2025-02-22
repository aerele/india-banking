frappe.ui.form.on("Payroll Entry", {
  refresh(frm) {
    if (
      frm.doc.salary_slips_submitted ||
      (frm.doc.__onload && frm.doc.__onload.submitted_ss)
    ) {
      frm.events.add_payment_request_button(frm);
    }
  },
  add_payment_request_button: function (frm) {
    frm.call("has_bank_entries").then((r) => {
      if (!r.message.has_bank_entries) {
        frm
          .add_custom_button(__("Create Payment Request"), function () {
            make_payment_request(frm);
          })
          .addClass("btn-primary");
      }
    });
  },
});

const make_payment_request = function (frm) {
  const payment_request_type = "Outward";

  frappe.call({
    method:
      "india_banking.overrides.payment_request.make_payment_request_for_payroll",
    args: {
      doctype: frm.doc.doctype,
      docname: frm.doc.name,
      recipient_id: "",
      payment_request_type: payment_request_type,
    },
  });
};
