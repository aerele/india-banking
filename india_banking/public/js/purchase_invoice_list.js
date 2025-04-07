frappe.listview_settings["Purchase Invoice"] = {
  onload: function (listview) {
	listview.page.add_action_item(__("Payment Request"), () => {
	  create_bulk_request(listview, "Purchase Invoice");
	});
	listview.page.add_inner_button(__("Payment Request"), () => {
	  frappe.set_route("List", "Payment Request");
	});
  },
};

const create_bulk_request = function (listview, doctype) {
  let checked_items = listview.get_checked_items();
  const doc_name = [];
  checked_items.forEach((Item) => {
	if (Item.docstatus == 0) {
	  doc_name.push(Item.name);
	}
  });
  let count_of_rows = checked_items.length;
  frappe.confirm(
	__("Create {0} {1} ?", [count_of_rows, __("Bank Payment Request")]),
	() => {
	  if (doc_name.length == 0) {
		frappe
		  .call({
			method:
			  "india_banking.india_banking.doc_events.payment_request.make_bulk_bank_payment_request",
			args: { invoices: checked_items, doctype: doctype },
		  })
		  .then((r) => {
			if (r.message.success_request > 0) {
			  setTimeout(() => {
				frappe.msgprint(
				  `<b>${r.message.success_request} Payment Request Created</b>`
				);
			  }, 1000);
			}
		  });
		if (count_of_rows > 10) {
		  frappe.show_alert("Starting a background job to create {0} {1}", [
			count_of_rows,
			__("Payment Request"),
		  ]);
		}
	  } else {
		frappe.msgprint(__("Selected document must be in submitted state"));
	  }
	}
  );
};
