import frappe
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_accounting_dimensions,
)
from frappe import _
from frappe.query_builder import DocType
from frappe.utils import get_link_to_form
from pypika.terms import ExistsCriterion


@frappe.whitelist()
def make_payment_order(source_name, target_doc=None, args=None):
	from frappe.model.mapper import get_mapped_doc

	def validate_party_bank_account(
		party_details, party_bank_details, invalid_party_details
	):
		for party_detail in party_details:
			party_type, party = party_detail.values()
			msg = ""
			if (party_type, party) in party_bank_details:
				continue

			bank_account = frappe.get_value(
				"Bank Account",
				{
					"party_type": party_type,
					"party": party,
				},
				["name", "disabled", "is_default"],
				as_dict=1,
			)

			if not bank_account:
				msg += f"<b>{party_type}-{party}</b> does not have a bank account.<br>"
			if bank_account and not bank_account.is_default:
				msg += f"<b>{party_type}-{party}</b> has no default bank account.<br>"
			if bank_account and bank_account.disabled:
				bank_account_link = get_link_to_form("Bank Account", bank_account.name)
				msg += f"<b>{party_type}-{party}</b> bank account {bank_account_link} is disabled.<br>"

			if msg:
				if msg not in invalid_party_details:
					invalid_party_details.append(msg)
			else:
				party_bank_details.update({(party_type, party): bank_account.name})

	def update_bank_entry(source, target):
		net_payable = 0
		net_receivable = 0

		party_receivables = {}
		invalid_party_details = []
		party_bank_details = {}

		if source.accounts:
			party_details = [
				{"party_type": acc.party_type, "party": acc.party}
				for acc in source.accounts
				if acc.party_type and acc.party
			]
			validate_party_bank_account(
				party_details, party_bank_details, invalid_party_details
			)
			if invalid_party_details:
				if msg := "".join(invalid_party_details):
					journal_entry_link = get_link_to_form("Journal Entry", source.name)
					frappe.msgprint(
						_(
							(
								"We can see Some bank entries are missing bank account details and have been ignored."
								"Please update the bank account information and try again."
								f"</br></br><p style='color:red'><b>The missing details for {journal_entry_link} are provided below.</b></p>"
							)
							+ msg
						),
						title=_("Missing Bank Account"),
						indicator="orange",
					)
					return

			for acc in source.accounts:
				if acc.account == target.account:
					net_payable += (
						acc.debit_in_account_currency - acc.credit_in_account_currency
					)
				else:
					if acc.party_type and acc.party:
						key = (acc.party_type, acc.party)
						if key in party_receivables:
							net_receivable += (
								acc.debit_in_account_currency
								- acc.credit_in_account_currency
							)
							receivables = (
								acc.debit_in_account_currency
								- acc.credit_in_account_currency
							)
							net_receivable += receivables
							party_receivables[key].payable_amount += receivables
						else:
							party_receivables[key] = acc
							receivables = (
								acc.debit_in_account_currency
								- acc.credit_in_account_currency
							)
							net_receivable += receivables
							party_receivables[key].payable_amount = receivables

			amount = net_payable + net_receivable
			if amount > 0:
				entry_link = get_link_to_form("Journal Entry", source.name)
				frappe.msgprint(
					_(
						f"Bank Entry {frappe.bold(entry_link)} is ambiguous and will be ignored."
					)
				)
				return

		ordered_bank_entries = frappe.get_all(
			"Payment Order Reference",
			filters={
				"docstatus": ["in", [0, 1]],
				"reference_doctype": "Journal Entry",
				"parent": ["!=", target.name],
			},
			fields=["reference_doctype", "reference_name", "journal_entry_account"],
			order_by="idx",
			as_list=True,
		)

		already_fetched = [
			(
				reference.reference_doctype,
				reference.reference_name,
				reference.journal_entry_account,
			)
			for reference in target.references
		]
		journal_accounts = []

		for entry in party_receivables.values():
			if entry.payable_amount > 0:
				if (entry.parenttype, entry.parent, entry.name) in ordered_bank_entries:
					continue
				if (entry.parenttype, entry.parent, entry.name) in already_fetched:
					continue
				entry.payment_amount = entry.payable_amount
				entry.party_bank_account = party_bank_details[
					(entry.party_type, entry.party)
				]
				if entry.party_bank_account:
					journal_accounts.append(entry)

		target.payment_order_type = "Journal Entry"
		target.docstaus = 0
		target.status = "Pending"

		def _update_dimensions(source):
			return {
				dimension: source.get(dimension, "")
				for dimension in get_accounting_dimensions()
			}

		for journal_account in journal_accounts:
			details = {
				"reference_doctype": "Journal Entry",
				"reference_name": journal_account.parent,
				"journal_entry_account": journal_account.name,
				"amount": journal_account.payment_amount,
				"party_type": journal_account.party_type,
				"party": journal_account.party,
				"mode_of_payment": "",
				"bank_account": journal_account.party_bank_account,
				"account": journal_account.account,
				"project": journal_account.project,
				"cost_center": journal_account.cost_center,
			}
			details.update(_update_dimensions(journal_account))

			target.append("references", details)

	doclist = get_mapped_doc(
		"Journal Entry",
		source_name,
		{
			"Journal Entry": {
				"doctype": "Payment Order",
			}
		},
		target_doc,
		update_bank_entry,
	)

	return doclist


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_bank_entry(doctype, txt, searchfield, start, page_len, filters, as_dict):
	filters = frappe._dict(filters)

	JournalEntry = DocType("Journal Entry")
	JournalEntryAccount = DocType("Journal Entry Account")

	ordered_bank_entries = frappe.get_all(
		"Payment Order Reference",
		filters={
			"docstatus": ["in", [0, 1]],
			"reference_doctype": "Journal Entry",
		},
		pluck="reference_name",
	)

	query = (
		frappe.qb.from_(JournalEntry)
		.join(JournalEntryAccount)
		.on(JournalEntry.name == JournalEntryAccount.parent)
		.select(
			JournalEntryAccount.parent.as_("name"),
			JournalEntry.company,
			JournalEntry.voucher_type,
		)
		.where(
			(JournalEntry.name.notin(ordered_bank_entries))
			& (JournalEntry.docstatus == 1)
			& (JournalEntry.voucher_type.eq("Bank Entry"))
			& (
				ExistsCriterion(
					frappe.qb.from_(JournalEntryAccount)
					.select("name")
					.where(
						(JournalEntryAccount.parent == JournalEntry.name)
						& (JournalEntryAccount.account == filters.company_account)
					)
				)
			)
			& (
				ExistsCriterion(
					frappe.qb.from_(JournalEntryAccount)
					.select("name")
					.where(
						(JournalEntryAccount.parent == JournalEntry.name)
						& (JournalEntryAccount.account != filters.company_account)
						& (JournalEntryAccount.party_type.isnotnull())
						& (
							JournalEntryAccount.payment_status.notin(
								["Ordered", "Payment Ordered", "Paid"]
							)
						)
					)
				)
			)
		)
		.groupby(JournalEntryAccount.parent)
	)

	if searchfield:
		if searchfield == "name":
			query = query.where(JournalEntry.name.like(f"%{txt}%"))

	return query.run(as_dict=as_dict)
