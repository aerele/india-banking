frappe.listview_settings["Payment Order"] = {
	add_fields: ["status"],
	get_indicator: function (doc) {
		if (doc.status == "Pending") {
			return [__("Pending"), "orange", "status,=,Pending"];
		}
		else if (doc.status == "Initiated") {
			return [__("Initiated"), "blue", "status,=,Initiated"];
		} else if (doc.status == "Completed") {
			return [__("Completed"), "green", "status,=,Completed"];
		}else if (doc.status == 'Rejected') {
			return [__('Rejected'), "red", "status,=,Rejected"];
		}else if (doc.status == 'Failed') {
			return [__('Failed'), "red", "status,=,Failed"];
		}
	},
};
