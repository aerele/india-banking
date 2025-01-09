import frappe
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_accounting_dimensions,
)
from erpnext.accounts.party import get_party_bank_account
from frappe import _
from frappe.model.mapper import get_mapped_doc


@frappe.whitelist()
def make_payment_order(source_name, target_doc=None):
	def set_missing_values(source, target):
		target.payment_order_type = "Payment Entry"
		target.company_bank_account = source.bank_account
		target.party = ""

		account = source.paid_to if source.paid_to else ""

		def _update_dimensions(source):
			return {
				dimension: source.get(dimension, "")
				for dimension in get_accounting_dimensions()
			}

		def _get_default_bank_account(party_type, party):
			party_bank_account = get_party_bank_account(party_type, party)
			if not party_bank_account:
				frappe.throw(
					_(
						"Default Bank Account is missing for {0} - {1}".format(
							party_type, party
						)
					)
				)
			return party_bank_account

		def _get_reference_data(reference=None):
			return {
				"reference_doctype": reference.reference_doctype
				if reference
				else "Payment Entry",
				"reference_name": reference.reference_name
				if reference
				else source.name,
				"amount": reference.allocated_amount
				if reference
				else source.paid_amount,
				"party_type": source.party_type,
				"party": source.party,
				"mode_of_payment": source.mode_of_payment
				if reference
				else "Wire Transfer",
				"bank_account": _get_default_bank_account(
					source.party_type, source.party
				),
				"account": account if reference else source.paid_to,
				"cost_center": source.cost_center,
				"project": source.project,
				"payment_entry": source.name,
				**_update_dimensions(source),
			}

		for reference in source.references:
			target.append("references", _get_reference_data(reference))

		if not source.references:
			target.append("references", _get_reference_data())

		target.status = "Pending"

	doclist = get_mapped_doc(
		"Payment Entry",
		source_name,
		{
			"Payment Entry": {
				"doctype": "Payment Order",
			}
		},
		target_doc,
		set_missing_values,
	)

	return doclist
