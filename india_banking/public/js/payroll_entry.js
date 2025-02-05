frappe.ui.form.on('Payroll Entry', {
	add_context_buttons: function (frm) {
        console.log("now triggers");
        
		if (
			frm.doc.salary_slips_submitted ||
			(frm.doc.__onload && frm.doc.__onload.submitted_ss)
		) {
			frm.events.add_bank_entry_button(frm);
            frm.call("has_bank_entries").then((r) => {
                if (r.message.has_bank_entries) {
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
    add_bank_payment_reuest_button(frm){
        frm.add_custom_button(__("Bank Payment Request"), function () {
            frappe.confirm(`${frm.doc.employees.length} Bank Payment Request will be create`,
                ()=> {
                    frappe.call({
                        method:"india_banking.india_banking.doctype.bank_payment_request.bank_payment_request.make_payment_request_for_payroll_entry",
                        args: {
                            payroll_entry: frm.doc.name,
                        },
                        callback: function(r) {
                            frappe.set_route("List", "Bank Payment Request");
                            if(!r.exc){
                                frappe.model.sync(r.message);
                                frappe.set_route("List", "Bank Payment Request");
                            }
                        }
                    })
                }
            )
        }).addClass("btn-primary");
    },
})