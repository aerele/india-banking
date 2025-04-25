// Copyright (c) 2025, Aerele Technologies Private Limited and contributors
// For license information, please see license.txt

frappe.ui.form.on("Beneficiary", {
    refresh: function(frm) {
        frm.add_custom_button(__('Discard Beneficiary'), function() {
            if(frm.doc.beneficiary_status != "Rejected") {
                frappe.throw(__('You can only discard a rejected Beneficiary'));
            }
            frappe.confirm(__('Are you sure you want to discard this beneficiary?'),
                function() {
                    frm.call({
                        method: "discard_beneficiary",
                        doc: frm.doc,
                        freeze: true,
                        freeze_message: __('Discarding Beneficiary...'),
                        callback: function(r) {
                            if (r.message) {
                                frm.reload_doc();
                            }
                        }
                    });
                });
        }, __('Actions'))
        .addClass('btn-danger')
        frm.disable_form()
    },
    bank_connector: function(frm) {
        if(frm.doc.bank_connector) {
            frappe.db.get_value('Bank Connector', frm.doc.bank_connector, 'bank', function(r) {
                frm.set_value('connector_bank', r.bank);
                frm.trigger('set_payment_type');
            });
        }
    },
    bank_account: function(frm) {
        if(frm.doc.bank_account) {
            frappe.db.get_value('Bank Account', frm.doc.bank_account, 'bank', function(r) {
                frm.set_value('bank', r.bank);
                frm.trigger('set_payment_type');
            });
        }
    },
    set_payment_type: function(frm) {
        if(frm.doc.bank == frm.doc.connector_bank){
            frm.set_value('payment_type', "INHOUSE-TRANSFER");
        }
        else if(frm.doc.bank && frm.doc.connector_bank && frm.doc.bank != frm.doc.connector_bank){
            frm.set_value('payment_type', "INTERBANK-TRANSFER");
        }
    }
});
