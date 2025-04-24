// Copyright (c) 2025, Aerele Technologies Private Limited and contributors
// For license information, please see license.txt

frappe.ui.form.on("Beneficiary", {
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
