import os

import frappe
from frappe.query_builder import DocType

from india_banking.default import BANK_CARD_COLORS

ICON_DIR = frappe.get_app_path(
	"india_banking", "public", "assets", "bank-logos", "icons"
)


def get_bank_icon(bank_name):
	basename = bank_name.replace(" ", "_")
	for ext in ("svg", "png"):
		filename = f"{basename}.{ext}"
		if os.path.exists(os.path.join(ICON_DIR, filename)):
			return f"/assets/india_banking/assets/bank-logos/icons/{filename}"
	return None


@frappe.whitelist()
def get_standard_bank():
	bank_details = []
	available_banks = frappe.db.get_list("Bank", {"is_standard": 1}, pluck="name")
	connected_banks = set(
		frappe.db.get_list(
			"Bank Account",
			{"is_company_account": 1, "disabled": 0},
			pluck="bank",
		)
	)

	for bank in available_banks:
		colors = BANK_CARD_COLORS.get(bank, ["#1a1a2e", "#ffffff"])
		bank_details.append(
			{
				"name": bank,
				"logo": get_bank_icon(bank),
				"primary_color": colors[0],
				"status": "Connected" if bank in connected_banks else "Available",
			}
		)

	return bank_details


@frappe.whitelist()
def get_connected_bank_accounts():
	connected_bank_details = []

	IBC = DocType("Bank Connector")
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
				"logo": get_bank_icon(row.get("bank_name")),
				"primary_color": colors[0],
				"secondary_color": colors[1],
			}
		)
		connected_bank_details.append(row)

	return connected_bank_details
