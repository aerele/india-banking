frappe.ui.form.on('Payroll Entry', {
	add_context_buttons: function (frm) {
        console.log("now triggers");
        
		if (
			frm.doc.salary_slips_submitted ||
			(frm.doc.__onload && frm.doc.__onload.submitted_ss)
		) {
			frm.events.add_bank_entry_button(frm);
            frm.call("has_bank_entries").then((r) => {
                if (!r.message.has_bank_entries) {
                    frm.events.add_bank_payment_reuest_button(frm);
                }
            });
		} else if (frm.doc.salary_slips_created && frm.doc.status !== "Queued") {
			frm.add_custom_button(__("Submit Salary Slip"), function () {
				submit_salary_slip(frm);
			}).addClass("btn-primary");
		} else if (!frm.doc.salary_slips_created && frm.doc.status === "Failed") {
			frm.add_custom_button(__("Create Salary Slips"), function () {
				frm.trigger("create_salary_slips");
			}).addClass("btn-primary");
		}
	},
    add_bank_payment_reuest_button: function (frm) {
        frm.call("has_bank_entries").then((r) => {
          if (!r.message.has_bank_entries) {
            frm
              .add_custom_button(__("Create Bank Payment Request"), function () {
                make_payment_request(frm);
              })
              .addClass("btn-primary");
          }
        });
      },
})

const make_payment_request = function (frm) {
    const payment_request_type = "Outward";
  
    frappe.call({
      method:
        "india_banking.india_banking.doctype.bank_payment_request.bank_payment_request.make_payment_request_for_payroll_entry",
      args: {
        doctype: frm.doc.doctype,
        docname: frm.doc.name,
        recipient_id: "",
        payment_request_type: payment_request_type,
      },
    });
  };
  