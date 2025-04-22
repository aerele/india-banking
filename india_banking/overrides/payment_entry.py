import frappe
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_accounting_dimensions,
)
from erpnext.accounts.party import get_party_bank_account
from frappe import _
from frappe.model.mapper import get_mapped_doc
from frappe.query_builder import DocType
from frappe.utils import get_url_to_form


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

			bank_account = frappe.get_doc("Bank Account", party_bank_account)
			if frappe.db.get_single_value(
				"India Banking Settings", "activate_workflow_on_bank_account"
			):
				if bank_account.workflow_state != "Approved":
					frappe.throw(
						title=_("Cannot proceed with un-approved bank account"),
						msg=_(
							"{}-{}- Bank Account <a href='{}'>{}</a>".format(
								party_type,
								party,
								get_url_to_form("Bank Account", bank_account.name),
								frappe.bold(bank_account.name),
							)
						),
					)

			if bank_account.currency != "INR":
				frappe.throw(
					title=_("The party bank account currency should be in INR."),
					msg=_(
						"{}-{}- Bank Account <a href='{}'>{}</a>".format(
							party_type,
							party,
							get_url_to_form("Bank Account", bank_account.name),
							frappe.bold(bank_account.name),
						)
					),
				)
			return bank_account.name

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


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_payment_entry(doctype, txt, searchfield, start, page_len, filters):
	payment_order = DocType("Payment Order")
	payment_order_reference = DocType("Payment Order Reference")
	query = (
		frappe.qb.from_(payment_order)
		.left_join(payment_order_reference)
		.on(payment_order.name == payment_order_reference.parent)
		.select(
			payment_order_reference.payment_entry,
		)
		.where(
			payment_order.payment_order_type.eq("Payment Entry")
			& payment_order.docstatus
			!= 2
		)
	)
	order_entry = query.run()

	existing_payment_entries = filters["existing_payment_entries"] or []
	order_entry = [d[0] for d in order_entry] or []

	order_entry += existing_payment_entries
	if order_entry:
		filters["name"] = ["not in", order_entry]
	if "existing_payment_entries" in filters:
		del filters["existing_payment_entries"]

	payment_entry = (
		frappe.get_all(
			"Payment Entry", filters=filters, fields=["name", "party", "paid_amount"]
		)
		or []
	)

	return payment_entry
