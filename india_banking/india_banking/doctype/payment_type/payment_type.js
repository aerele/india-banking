// Copyright (c) 2024, Aerele Technologies Private Limited and contributors
// For license information, please see license.txt

frappe.ui.form.on("Payment Type", {
  refresh(frm) {
	frm.set_query("account", function () {
	  return {
		  filters: {
			company: frm.doc.company,
		  is_group: 0,
		  disabled: 0,
		  account_type: "Payable",
		},
	  };
	});
  },
});
