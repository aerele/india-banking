import frappe
from frappe.query_builder import DocType

from india_banking.default import BANK_CARD_COLORS


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
		colors = BANK_CARD_COLORS.get(row.bank_name, ["#1a1a2e", "#ffffff"])
		row.update(
			{
				"logo": f"/assets/india_banking/assets/bank-logos/{row.get('bank_name').replace(' ', '_')}.png",
				"primary_color": colors[0],
				"secondary_color": colors[1],
			}
		)
		connected_bank_details.append(row)

	return connected_bank_details
