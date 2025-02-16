frappe.ui.form.on("Purchase Invoice", {
  refresh(frm) {
    if (
      frm.doc.outstanding_amount > 0 &&
      !cint(frm.doc.is_return) &&
      !frm.doc.on_hold
    ) {
      enable_bank_payment_request(frm);
    }
  },
});

const make_bank_payment_request = function (frm) {
  const payment_request_type = ["Sales Order", "Sales Invoice"].includes(
    frm.doc.doctype
  )
    ? "Inward"
    : "Outward";

  frappe.call({
    method:
      "india_banking.india_banking.doctype.bank_payment_request.bank_payment_request.make_bank_payment_request",
    args: {
      dt: frm.doc.doctype,
      dn: frm.doc.name,
      recipient_id: frm.doc.contact_email,
      payment_request_type: payment_request_type,
      party_type: payment_request_type == "Outward" ? "Supplier" : "Customer",
      party:
        payment_request_type == "Outward" ? frm.doc.supplier : frm.doc.customer,
    },
    callback: function (r) {
      if (!r.exc) {
        frappe.model.sync(r.message);
        frappe.set_route("Form", r.message.doctype, r.message.name);
      }
    },
  });
};

const enable_bank_payment_request = function (frm) {
  frappe.call({
    method: "india_banking.utils.is_bank_payment_request_enabled",
    args: {
      doctype: frm.doc.doctype,
      workflow: frm.doc.workflow_state,
    },
    callback: function (r) {
      if (!r.exc && r.message.enabled == 1) {
        cur_frm.add_custom_button(
          __("Bank Payment Request"),
          function () {
            make_bank_payment_request(frm);
          },
          __("Create")
        );
        setTimeout(() => {
          toggle_custom_button(frm);
        }, 1000);
      }
    },
  });
};

const toggle_custom_button = function (frm) {
  frm.remove_custom_button("Payment Request", "Create");
  frm.remove_custom_button("Payment", "Create");
};
