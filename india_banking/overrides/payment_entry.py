import frappe
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_accounting_dimensions,
)
from india_banking.utils import get_party_bank_account
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
				"India Banking Settings", "enable_bank_account_workflow"
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
				**_update_dimensions(source),
			}

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
	po = DocType("Payment Order")
	por = DocType("Payment Order Reference")

	rows = (
		frappe.qb.from_(po)
		.inner_join(por)
		.on(po.name == por.parent)
		.select(por.payment_entry, por.reference_doctype, por.reference_name)
		.where((po.payment_order_type == "Payment Entry") & (po.docstatus != 2))
	).run(as_dict=True)

	already_ordered = {
		(
			row.reference_name
			if row.reference_doctype == "Payment Entry"
			else row.payment_entry
		)
		for row in rows
	} - {None, ""}

	existing = set(filters.pop("existing_payment_entries", None) or []) - {None, ""}
	excluded = already_ordered | existing

	# Pop source_doctype so we can apply a NULL-safe condition manually.
	# frappe.get_all with "!=" silently drops rows where the column IS NULL
	# because SQL evaluates NULL != 'x' as NULL (not TRUE).
	source_doctype_filter = filters.pop("source_doctype", None)

	pe = DocType("Payment Entry")
	query = frappe.qb.from_(pe).select(pe.name, pe.party, pe.paid_amount)

	simple_op = {"=": lambda f, v: f == v, "!=": lambda f, v: f != v}
	for field, condition in filters.items():
		col = pe[field]
		if isinstance(condition, list):
			op, val = condition
			if op in ("in", "not in"):
				query = query.where(col.isin(val) if op == "in" else col.notin(val))
			elif op in simple_op:
				query = query.where(simple_op[op](col, val))
		else:
			query = query.where(col == condition)

	if excluded:
		query = query.where(pe.name.notin(list(excluded)))

	# Include entries where source_doctype is NULL or doesn't match the excluded value.
	if (
		source_doctype_filter
		and isinstance(source_doctype_filter, list)
		and source_doctype_filter[0] == "!="
	):
		excluded_source = source_doctype_filter[1]
		query = query.where(
			(pe.source_doctype != excluded_source) | pe.source_doctype.isnull()
		)

	return query.run(as_dict=True) or []
