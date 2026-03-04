import frappe


def execute():
	fields = [
		{
			"filters": {
				"dt": "Payment Request",
				"fieldname": "is_adhoc",
			},
			"property": {"read_only": 1},
		},
		{
			"filters": {
				"dt": "Payment Request",
				"fieldname": "apply_tax_withholding_amount",
			},
			"property": {"read_only": 1},
		},
		{
			"filters": {
				"dt": "Payment Request",
				"fieldname": "tax_withholding_category",
			},
			"property": {"read_only": 1},
		},
		{
			"filters": {
				"dt": "Payment Order Reference",
				"fieldname": "tax_withholding_category",
			},
			"property": {"read_only": 1},
		},
		{
			"filters": {
				"dt": "Payment Order Reference",
				"fieldname": "is_adhoc",
			},
			"property": {"read_only": 1},
		},
	]

	for i in fields:
		frappe.db.set_value("Custom Field", i["filters"], i["property"])
