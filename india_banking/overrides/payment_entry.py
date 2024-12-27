import frappe
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_accounting_dimensions,
)
from erpnext.accounts.doctype.payment_entry.payment_entry import PaymentEntry
from erpnext.accounts.party import get_party_bank_account
from frappe import _


class CustomPaymentEntry(PaymentEntry):
	def validate_duplicate_entry(self):
		reference_names = []
		for d in self.get("references"):
			reference_names.append(
				(d.reference_doctype, d.reference_name, d.payment_term)
			)


@frappe.whitelist()
def make_payment_order(source_name, target_doc=None):
	from frappe.model.mapper import get_mapped_doc

	def set_missing_values(source, target):
		target.payment_order_type = "Payment Entry"
		target.company_bank_account = source.bank_account
		target.party = ""

		account = ""
		if source.paid_to:
			account = source.paid_to

		def _update_dimensions(source):
			return {
				dimension: source.get(dimension, "")
				for dimension in get_accounting_dimensions()
			}

		def _get_default_bank_account(party_type, party):
			party_bank_account = get_party_bank_account(party_type, party)
			if not party_bank_account:
				frappe.throw(
					_("Default Bank Account is missing for {0} - {1}").format(
						party_type, party
					)
				)
			return party_bank_account

		for count, reference in enumerate(source.references, 1):
			reference = {
				"reference_doctype": reference.reference_doctype,
				"reference_name": reference.reference_name,
				"amount": reference.allocated_amount,
				"party_type": source.party_type,
				"party": source.party,
				"mode_of_payment": source.mode_of_payment,
				"bank_account": _get_default_bank_account(
					source.party_type, source.party
				),
				"account": account,
				"cost_center": source.cost_center,
				"project": source.project,
				"payment_entry": source.name,
			}
			reference.update(_update_dimensions(source))

			target.append(
				"references",
				reference,
			)
			if count == len(source.references):
				break
		else:
			reference = {
				"reference_doctype": "Payment Entry",
				"reference_name": source.name,
				"amount": source.paid_amount,
				"party_type": source.party_type,
				"party": source.party,
				"mode_of_payment": "Wire Transfer",
				"bank_account": _get_default_bank_account(
					source.party_type, source.party
				),
				"account": source.paid_to,
				"cost_center": source.cost_center,
				"project": source.project,
				"payment_entry": source.name,
			}
			reference.update(_update_dimensions(source))

			target.append(
				"references",
				reference,
			)
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
