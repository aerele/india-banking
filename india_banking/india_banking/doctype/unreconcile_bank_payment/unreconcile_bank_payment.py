# Copyright (c) 2026, Aerele Technologies Private Limited and contributors
# For license information, please see license.txt

import json

import frappe
from erpnext.accounts.doctype.unreconcile_payment.unreconcile_payment import (
	create_unreconcile_doc_for_selection,
)
from frappe import _
from frappe.model.document import Document
from frappe.utils import comma_and, get_link_to_form


class UnreconcileBankPayment(Document):
	def validate(self):
		self.supported_types = ["Payment Order"]
		if self.voucher_type not in self.supported_types:
			frappe.throw(
				_("Only {0} are supported").format(comma_and(self.supported_types))
			)

		if not self.allocations:
			frappe.throw(_("At least one Allocation is required before submission."))

	def add_references(self):
		allocations = self.get_reference_from_payment_order()

		for alloc in allocations:
			self.append(
				"allocations",
				{
					"party_type": alloc.party_type,
					"party": alloc.party,
					"reference_type": alloc.reference_doctype,
					"reference_name": alloc.reference_name,
					"amount": alloc.amount,
					"account": alloc.account,
					"payment_request": alloc.payment_request,
				},
			)

	def on_submit(self):
		frappe.flags.from_payment_order = True
		voucher_nos = frappe._dict()

		comment_msg = [_("The following vouchers are unlinked from the Payment Order:")]
		for alloc in self.allocations:
			key = (alloc.party_type, alloc.party)
			voucher_nos.setdefault(key, []).append(
				{
					"voucher_type": alloc.reference_type,
					"voucher_no": alloc.reference_name,
					"amount": alloc.amount,
					"payment_request": alloc.payment_request,
				}
			)

			frappe.db.delete(
				"Payment Order Reference",
				{
					"parent": self.voucher_no,
					"reference_doctype": alloc.reference_type,
					"reference_name": alloc.reference_name,
				},
			)
			comment_msg.append(
				" - {0}: {1} - {2}".format(
					alloc.reference_type,
					get_link_to_form(alloc.reference_type, alloc.reference_name),
					frappe.utils.fmt_money(alloc.amount),
				)
			)

		for (party_type, party), vouchers in voucher_nos.items():
			payment_entry = frappe.db.get_value(
				"Payment Entry",
				{
					"party_type": party_type,
					"party": party,
					"payment_order": self.voucher_no,
					"docstatus": 1,
				},
			)

			if not payment_entry:
				continue

			selections = [
				{
					"company": self.company,
					"voucher_type": "Payment Entry",
					"voucher_no": payment_entry,
					"against_voucher_type": voucher["voucher_type"],
					"against_voucher_no": voucher["voucher_no"],
				}
				for voucher in vouchers
			]

			create_unreconcile_doc_for_selection(json.dumps(selections))

			for voucher in vouchers:
				if voucher["payment_request"]:
					if not frappe.has_permission(
						"Payment Request", "cancel", voucher["payment_request"]
					):
						frappe.throw(
							_(
								"You do not have permission to cancel Payment Request {0}."
							).format(voucher["payment_request"])
						)

					payment_request = frappe.get_doc(
						"Payment Request", voucher["payment_request"]
					)
					payment_request.cancel()
					payment_request.add_comment(
						"Comment",
						_("{0}: {1} unlinked from the Payment Order: {2}").format(
							voucher["voucher_type"],
							get_link_to_form(
								voucher["voucher_type"], voucher["voucher_no"]
							),
							get_link_to_form(self.voucher_type, self.voucher_no),
						),
					)

		if len(comment_msg) > 1:
			frappe.get_doc(self.voucher_type, self.voucher_no).add_comment(
				"Comment", "<br>".join(comment_msg)
			)

		frappe.flags.from_payment_order = False

	@frappe.whitelist()
	def get_reference_from_payment_order(self):
		return get_payment_order_reference(self.voucher_no)


@frappe.whitelist()
def get_payment_order_reference(docname: str) -> list:
	return frappe.db.get_all(
		"Payment Order Reference",
		{"parenttype": "Payment Order", "parent": docname},
		[
			"party_type",
			"party",
			"reference_doctype",
			"reference_name",
			"amount",
			"account",
			"payment_request",
		],
	)


@frappe.whitelist()
def create_unreconcile_bank_doc_for_selection(args):
	if args:
		if isinstance(args, str):
			args = json.loads(args)

		unrecon = frappe.new_doc("Unreconcile Bank Payment")
		unrecon.company = args["company"]
		unrecon.voucher_type = args["voucher_type"]
		unrecon.voucher_no = args["voucher_no"]

		for row in args["selections"]:
			unrecon.append(
				"allocations",
				{
					"party_type": row["party_type"],
					"party": row["party"],
					"reference_type": row["reference_type"],
					"reference_name": row["reference_name"],
					"amount": row["amount"],
					"account": row["account"],
					"payment_request": row["payment_request"],
				},
			)

		unrecon.save().submit()
