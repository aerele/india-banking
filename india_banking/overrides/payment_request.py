import frappe
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_accounting_dimensions,
)
from erpnext.accounts.doctype.payment_request.payment_request import (
	PaymentRequest,
	get_dummy_message,
	get_existing_paid_amount,
	get_gateway_details,
)
from erpnext.accounts.doctype.tax_withholding_category.tax_withholding_category import (
	get_party_tax_withholding_details,
)
from frappe import _
from frappe.query_builder.functions import Sum
from frappe.utils import flt, get_url_to_form

from india_banking.utils import get_party_bank_account


class BankPaymentRequest(PaymentRequest):
	def validate(self):
		self.set_default_value()
		if not self.net_total:
			self.net_total = self.grand_total

		if (
			self.apply_tax_withholding_amount
			and self.tax_withholding_category
			and self.payment_request_type == "Outward"
		):
			tds_amount = self.calculate_pr_tds(self.net_total)
			self.taxes_deducted = tds_amount
			self.grand_total = self.net_total - self.taxes_deducted
		else:
			self.grand_total = self.net_total or self.grand_total

		if not self.is_adhoc:
			super().validate()
		else:
			if self.is_new():
				self.status = "Draft"
			if self.reference_doctype or self.reference_name:
				frappe.throw(_("Payments with references cannot be marked as ad-hoc"))

		if self.remarks:
			self.remarks = self.remarks[:48]

		self.valdidate_bank_for_wire_transfer()

	def validate_payment_request_amount(self):
		if self.reference_doctype not in [
			"Payroll Entry"
		]:  # ignoring validation for Payroll Entry
			super().validate_payment_request_amount()

	def set_default_value(self):
		if not self.payment_type:
			if payment_type := frappe.db.exists(
				"Payment Type",
				{
					"company": self.company,
					"is_default": 1,
				},
			):
				self.payment_type = payment_type
			else:
				frappe.throw(
					_(
						f"Set Default <b><a href='/app/payment-type'>Payment Type</a></b> for company {frappe.bold(self.company)}".format(
							self.company
						)
					)
				)

		filters = {
			"party_type": self.party_type,
			"party": self.party,
			"is_default": 1,
			"disabled": 0,
			"currency": self.currency,
		}

		if frappe.db.get_single_value(
			"India Banking Settings", "activate_workflow_on_bank_account"
		):
			filters["workflow_state"] = "Approved"

		if not self.bank_account:
			self.bank_account = frappe.get_value("Bank Account", filters, "name")

	def on_submit(self):
		if not self.grand_total or not self.net_total:
			frappe.throw(_("Amount cannot be zero"))

		self.validate_payment_type()
		self.validate_bank_account()

		if not self.is_adhoc:
			super().on_submit()
		else:
			if self.payment_request_type == "Outward":
				self.db_set("status", "Initiated")

	def validate_payment_type(self):
		if self.payment_type:
			payment_type_company = frappe.db.get_value(
				"Payment Type", self.payment_type, "company"
			)
			if self.company != payment_type_company:
				frappe.throw(
					_(
						"Payment Type <b>{0}</b> is not valid for company <b>{1}</b>".format(
							self.payment_type, self.company
						)
					)
				)

		debit_account = frappe.db.get_value(
			"Payment Type", self.payment_type, "account"
		) or frappe.db.get_value(
			self.reference_doctype, self.reference_name, "credit_to"
		)

		if not debit_account:
			frappe.throw(
				_(
					"Debit account for Payment Type <b>{}</b> cannot be determined"
				).format(self.payment_type or "")
			)

	def validate_bank_account(self):
		bank_account = get_party_bank_account(self.party_type, self.party)
		if not bank_account:
			frappe.throw(
				_(
					"Default Bank Account is missing for {0} - {1}".format(
						self.party_type, frappe.bold(self.party)
					)
				)
			)

		bank_account = frappe.get_doc("Bank Account", bank_account)
		if frappe.db.get_single_value(
			"India Banking Settings", "activate_workflow_on_bank_account"
		):
			if bank_account.workflow_state != "Approved":
				frappe.throw(
					title=_("Cannot proceed with un-approved bank account"),
					msg=_(
						"{}-{}- Bank Account <a href='{}'>{}</a>".format(
							self.party_type,
							self.party,
							get_url_to_form("Bank Account", bank_account),
							frappe.bold(bank_account),
						)
					),
				)

		if bank_account.currency != self.currency:
			frappe.throw(
				title=_(
					f"The party bank account currency should be in {self.currency}."
				),
				msg=_(
					"{}-{}- Bank Account <a href='{}'>{}</a>".format(
						self.party_type,
						self.party,
						get_url_to_form("Bank Account", bank_account.name),
						frappe.bold(bank_account.name),
					)
				),
			)

		if self.bank_account:
			bank_account_company = frappe.db.get_value(
				"Bank Account", self.bank_account, "company"
			)
			if self.company != bank_account_company:
				frappe.throw(
					_(
						"Bank Account <b>{0}</b> is not valid for company <b>{1}</b>".format(
							self.bank_account, self.company
						)
					)
				)

	def create_payment_entry(self, submit=True):
		payment_entry = super().create_payment_entry(submit=submit)
		if payment_entry.docstatus != 1 and self.payment_type:
			payment_entry.paid_to = (
				frappe.db.get_value("Payment Type", self.payment_type, "account") or ""
			)

		return payment_entry

	def calculate_pr_tds(self, amount):
		doc = self
		doc.supplier = self.party
		doc.company = self.company
		doc.base_tax_withholding_net_total = amount
		doc.tax_withholding_net_total = amount
		doc.taxes = []
		taxes = get_party_tax_withholding_details(doc, self.tax_withholding_category)
		if taxes:
			return taxes["tax_amount"]
		else:
			return 0

	def valdidate_bank_for_wire_transfer(self):
		if self.mode_of_payment == "Wire Transfer":
			if not self.bank_account:
				frappe.throw(_("Bank Account is missing for Wire Transfer Payments"))

			bank_account = frappe.get_doc("Bank Account", self.bank_account)

			if (
				frappe.db.get_single_value(
					"India Banking Settings", "activate_workflow_on_bank_account"
				)
				and bank_account.workflow_state != "Approved"
			):
				frappe.throw(
					title=_("Cannot proceed with un-approved bank account"),
					msg=_(
						"{}-{}- Bank Account <a href='{}'>{}</a>".format(
							self.party_type,
							self.party,
							get_url_to_form("Bank Account", self.bank_account),
							frappe.bold(self.bank_account),
						)
					),
				)
			if bank_account.currency != self.currency:
				frappe.throw(
					title=_(
						f"The party bank account currency should be in {self.currency}."
					),
					msg=_(
						"{}-{}- Bank Account <a href='{}'>{}</a>".format(
							bank_account.party_type,
							bank_account.party,
							get_url_to_form("Bank Account", self.bank_account),
							frappe.bold(self.bank_account),
						)
					),
				)


@frappe.whitelist()
def make_payment_order(source_name, target_doc=None):
	from frappe.model.mapper import get_mapped_doc

	def set_missing_values(source, target):
		target.payment_order_type = "Payment Request"
		account = ""
		if source.payment_type:
			account = frappe.db.get_value(
				"Payment Type", source.payment_type, "account"
			)
		if source.reference_doctype == "Purchase Invoice":
			account = frappe.db.get_value(
				source.reference_doctype, source.reference_name, "credit_to"
			)

		def _update_dimensions(source):
			return {
				dimension: source.get(dimension, "")
				for dimension in get_accounting_dimensions()
			}

		reference = {
			"reference_doctype": source.reference_doctype,
			"reference_name": source.reference_name,
			"amount": source.grand_total,
			"party_type": source.party_type,
			"party": source.party,
			"payment_request": source_name,
			"mode_of_payment": source.mode_of_payment,
			"bank_account": source.bank_account,
			"account": account,
			"is_adhoc": source.is_adhoc,
			"cost_center": source.cost_center,
			"project": source.project,
			"tax_withholding_category": source.tax_withholding_category,
		}
		reference.update(_update_dimensions(source))

		target.append(
			"references",
			reference,
		)
		target.status = "Pending"

	doclist = get_mapped_doc(
		"Payment Request",
		source_name,
		{
			"Payment Request": {
				"doctype": "Payment Order",
			}
		},
		target_doc,
		set_missing_values,
	)

	return doclist


@frappe.whitelist()
def make_payment_request_for_payroll(**args):
	"""Make payroll payment request"""

	args = frappe._dict(args)

	ref_doc = frappe.get_doc(args.doctype, args.docname)
	gateway_account = get_gateway_details(args) or frappe._dict()

	salary_slips = []
	if args.docname:
		salary_slips = frappe.get_list(
			"Salary Slip",
			{"payroll_entry": args.docname, "docstatus": 1},
			["name as salary_slip", "gross_pay as net_total", "employee as party"],
		)

	for count, salary_details in enumerate(salary_slips):
		grand_total = salary_details.get("net_total", 0)

		bank_account = get_party_bank_account("Employee", salary_details.get("party"))

		draft_payment_request = frappe.db.get_value(
			"Payment Request",
			{
				"reference_doctype": args.doctype,
				"reference_name": args.docname,
				"salary_slip": salary_details.get("salary_slip"),
				"docstatus": 0,
			},
		)

		# fetches existing payment request `grand_total` amount
		existing_payment_request_amount = get_existing_payment_request_amount(
			args.doctype, args.docname, salary_slip=salary_details.get("salary_slip")
		)

		existing_paid_amount = get_existing_paid_amount(args.doctype, args.docname)

		if existing_payment_request_amount:
			grand_total -= existing_payment_request_amount

		if existing_paid_amount:
			grand_total -= flt(existing_paid_amount)

		if grand_total < 0:
			continue
		else:
			count += 1

		if draft_payment_request:
			frappe.db.set_value(
				"Payment Request",
				draft_payment_request,
				"grand_total",
				grand_total,
				update_modified=False,
			)
			pr = frappe.get_doc("Payment Request", draft_payment_request)
		else:
			pr = frappe.new_doc("Payment Request")

			args["payment_request_type"] = "Outward"

			party_type = "Employee"
			party_name = ""
			if salary_details.get("party"):
				party_name = frappe.get_value(
					"Employee", salary_details.get("party"), "employee_name"
				)

			party_account_currency = "INR"

			pr.update(
				{
					"payment_gateway_account": gateway_account.get("name"),
					"payment_gateway": gateway_account.get("payment_gateway"),
					"payment_account": gateway_account.get("payment_account"),
					"payment_channel": gateway_account.get("payment_channel"),
					"payment_request_type": args.get("payment_request_type"),
					"currency": ref_doc.currency,
					"party_account_currency": party_account_currency,
					"grand_total": grand_total,
					"mode_of_payment": "Wire Transfer" if bank_account else "",
					"email_to": args.recipient_id or ref_doc.owner,
					"subject": _("Payment Request for {0}").format(args.docname),
					"message": gateway_account.get("message")
					or get_dummy_message(ref_doc),
					"reference_doctype": args.doctype,
					"reference_name": args.docname,
					"salary_slip": salary_details.get("salary_slip", ""),
					"company": ref_doc.get("company"),
					"party_type": party_type,
					"party": salary_details.get("party"),
					"bank_account": bank_account,
					"party_name": party_name,
				}
			)

			# Update dimensions
			pr.update(
				{
					"cost_center": ref_doc.get("cost_center"),
					"project": ref_doc.get("project"),
				}
			)

			for dimension in get_accounting_dimensions():
				pr.update({dimension: ref_doc.get(dimension)})

			if frappe.db.get_single_value(
				"Accounts Settings", "create_pr_in_draft_status", cache=True
			):
				pr.insert(ignore_permissions=True)
			if args.submit_doc:
				if pr.get("__unsaved"):
					pr.insert(ignore_permissions=True)
				pr.submit()
	else:
		frappe.msgprint(f"{count} Payment request Created")


def get_existing_payment_request_amount(
	ref_dt, ref_dn, statuses: list | None = None, salary_slip=None
) -> list:
	"""
	Return the total amount of Payment Requests against a reference document.
	"""
	PR = frappe.qb.DocType("Payment Request")

	query = (
		frappe.qb.from_(PR)
		.select(Sum(PR.grand_total))
		.where(PR.reference_doctype == ref_dt)
		.where(PR.reference_name == ref_dn)
		.where(PR.docstatus == 1)
	)

	if statuses:
		query = query.where(PR.status.isin(statuses))

	if salary_slip:
		try:
			query2 = query.where(PR.salary_silp.eq(salary_slip))
			response = query2.run()
		except Exception:
			response = query.run()

	return response[0][0] if response[0] else 0
