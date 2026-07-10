// Copyright (c) 2024, Aerele Technologies Private Limited and contributors
// For license information, please see license.txt

frappe.ui.form.on("India Banking Settings", {
  refresh(frm) {
    frm.set_query("default_email_format", function () {
      return {
        filters: {
          doc_type: "Payment Entry",
        },
      };
    });
    frm.set_query("doctype_name", "allowed_doctypes", function (doc, cdt, cdn) {
      let row = locals[cdt][cdn];
      return {
        query: "india_banking.utils.get_allowed_doctypes",
      };
    });
    frm.set_df_property(
      "unlink_allowed_roles",
      "read_only",
      !frappe.user.has_role("Administrator")
    );
  },
});
