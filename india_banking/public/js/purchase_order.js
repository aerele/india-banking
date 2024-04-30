frappe.ui.form.on('Purchase Order', {
	refresh(frm) {
        if (frm.doc.docstatus == 1) {
            if (frm.doc.status != "Closed") {
                if (frm.doc.status != "On Hold") { 
                    if (flt(frm.doc.per_billed, 2) < 100) {
                        frm.add_custom_button(__('Bank Payment Request'), function() {
                            this.make_bank_payment_request(frm)
                        }, "Create");
                    }
                }
            }
        }
	},
    onload_post_render(frm) {
        cur_frm.remove_custom_button("Payment Request", "Create")
        cur_frm.remove_custom_button("Payment", "Create")
    },
})

this.make_bank_payment_request = function(frm){
    const payment_request_type = (['Sales Order', 'Sales Invoice'].includes(frm.doc.doctype))
        ? "Inward" : "Outward";

    frappe.call({
        method:"india_banking.india_banking.doctype.bank_payment_request.bank_payment_request.make_bank_payment_request",
        args: {
            dt: frm.doc.doctype,
            dn: frm.doc.name,
            recipient_id: frm.doc.contact_email,
            payment_request_type: payment_request_type,
            party_type: payment_request_type == 'Outward' ? "Supplier" : "Customer",
            party: payment_request_type == 'Outward' ? frm.doc.supplier : frm.doc.customer
        },
        callback: function(r) {
            if(!r.exc){
                frappe.model.sync(r.message);
                frappe.set_route("Form", r.message.doctype, r.message.name);
            }
        }
    })
}