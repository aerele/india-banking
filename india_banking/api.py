import frappe
from frappe.query_builder import DocType

BANK_COLORS = {
	"Axis Bank": ["#ae285d", "#ffffff"],
	"HDFC Bank": ["#004c8f", "#ed232a"],
	"ICICI Bank": ["#ae282e", "#f06321"],
	"Kotak Mahindra Bank": ["#ed1c24", "#003874"],
	"Union Bank of India": ["#da251c", "#03599d"],
	"Bank of Baroda": ["#f15a29", "#ffffff"],
	"IDFC First Bank": ["#9d1d27", "#fefefe"],
	"HSBC Bank": ["#db0011", "#000000"],
	"Citi Bank": ["#255be3", "#ff3c28"],
	"Yes Bank": ["#002eda", "#eb1f48"],
}


@frappe.whitelist()
def get_standard_bank():
	bank_details = []
	available_banks = frappe.db.get_list("Bank", {"is_standard": 1}, pluck="name")
	for bank in available_banks:
		bank_details.append(
			{
				"name": bank,
				"logo": f"/assets/india_banking/assets/bank-logos/{bank.replace(' ', '_')}.png",
			}
		)

	return bank_details


@frappe.whitelist()
def get_connected_bank_accounts():
	connected_bank_details = []

	IBC = DocType("India Banking Connector")
	BA = DocType("Bank Account")

	connected_banks = (
		frappe.qb.from_(IBC)
		.join(BA)
		.on(BA.name == IBC.bank_account)
		.select(
			BA.name.as_("name"),
			BA.account_name,
			BA.bank_account_no.as_("account_number"),
			BA.bank.as_("bank_name"),
			BA.branch_code,
		)
	).run(as_dict=True)

	for row in connected_banks:
		row.update(
			{
				"logo": f"/assets/india_banking/assets/bank-logos/{row.get('bank_name').replace(' ', '_')}.png",
				"primary_color": BANK_COLORS[row.bank_name][0],
				"secondary_color": BANK_COLORS[row.bank_name][1],
			}
		)
		connected_bank_details.append(row)

	return connected_bank_details
