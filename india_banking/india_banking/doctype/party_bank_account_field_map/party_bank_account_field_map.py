# Copyright (c) 2025, Aerele Technologies Private Limited and contributors
# For license information, please see license.txt

import frappe
from frappe import _, bold
from frappe.model.document import Document
from frappe.query_builder import DocType
from frappe.utils import cstr


class PartyBankAccountFieldMap(Document):
	def validate(self):
		for field in self.field_map:
			if not frappe.get_meta(self.party_type).has_field(
				cstr(field.party_bank_account_field)
			):
				frappe.throw(
					_(
						"Field {0} does not exist in {1} - {2}".format(
							bold(field.party_bank_account_field),
							bold("Party Type"),
							bold(self.name),
						)
					)
				)


@frappe.whitelist()
def get_party_bank_fields(party_type=None):
	if party_type:
		FM = DocType("Field Map")
		party_bank_fields = (
			frappe.qb.from_(FM)
			.select(FM.bank_account_field, FM.party_bank_account_field)
			.where(
				(FM.parent == party_type)
				& (FM.parenttype == "Party Bank Account Field Map")
			)
		).run(as_dict=True)

		return {
			d.get("bank_account_field"): d.get("party_bank_account_field")
			for d in party_bank_fields
		}
	else:
		return {}
