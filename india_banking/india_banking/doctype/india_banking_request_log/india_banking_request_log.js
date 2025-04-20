// Copyright (c) 2024, Aerele Technologies Private Limited and contributors
// For license information, please see license.txt

frappe.ui.form.on("India Banking Request Log", {
  refresh(frm) {
    frm
      .add_custom_button("Show Formated Response", function () {
        frm.call("show_failure_message");
      })
      .addClass("btn-primary");
  },
});
