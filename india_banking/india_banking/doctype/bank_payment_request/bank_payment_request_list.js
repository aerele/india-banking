frappe.listview_settings["Bank Payment Request"] = {
	add_fields: ["status"],
	get_indicator: function (doc) {
		if (doc.status == "Draft") {
			return [__("Draft"), "gray", "status,=,Draft"];
		}
		if (doc.status == "Requested") {
			return [__("Requested"), "green", "status,=,Requested"];
		} else if (doc.status == "Initiated") {
			return [__("Initiated"), "green", "status,=,Initiated"];
		} else if (doc.status == 'Payment Ordered') {
			return [__('Payment Ordered'), "green", "status,=,Payment Ordered"];
		} else if (doc.status == "Partially Paid") {
			return [__("Partially Paid"), "orange", "status,=,Partially Paid"];
		} else if (doc.status == "Paid") {
			return [__("Paid"), "blue", "status,=,Paid"];
		} else if (doc.status == "Cancelled") {
			return [__("Cancelled"), "red", "status,=,Cancelled"];
		} else if (doc.status == "Failed") {
			return [__("Failed"), "red", "status,=,Failed"];
		}
	},
	onload: function (listview) {
		listview.page.add_action_item(__("Payment Order"), ()=>{create_bulk_order(listview)});
		listview.page.add_inner_button(__("Payment Order"), () => {
			frappe.set_route("List", "Payment Order");
		  });
	}
};


const create_bulk_order = function (listview) {
	if(!listview.page.fields_dict.company.value){
		frappe.throw({ message: __("Please select a Company filter first."), title: __("Mandatory") });
	}

	let checked_items = listview.get_checked_items();
	const doc_name = [];
	const requestsed = [];
	checked_items.forEach((Item) => {
	  if (Item.docstatus != 1) {
		doc_name.push(Item.name);
	  }
	  else if (Item.status != "Initiated") {
		requestsed.push(Item.name);
	  }
	});

	let count_of_rows = checked_items.length;
	frappe.confirm(__("Create Payment Order"), () => {
	  if (doc_name.length == 0 && requestsed.length == 0) {
		frappe
		  .call({
			method: "india_banking.india_banking.doctype.bank_payment_request.bank_payment_request.make_bulk_bank_payment_order",
			args: { requests: checked_items },
			freeze: true,
			freeze_message: __("Creating Payment Order"),
		  })
		  .then((r) => {
			if(r.message){
			  setTimeout(()=>{
				  frappe.msgprint("Payment order created successfully");
				  cur_list.refresh();
				},
				3000
			  )
			}
		  });
		if (count_of_rows > 10) {
		  frappe.show_alert("Starting a background job to create {0} {1}", [
			count_of_rows,
			__("Payment Order"),
		  ]);
		}
	  } else {
		if (doc_name.length > 0) {
		  frappe.msgprint(__("Selected document must be in submitted state"));
		}
		if (requestsed.length > 0) {
		  frappe.msgprint(__("Selected document must be in Initiated state"));
		}
	  }
	});
}
