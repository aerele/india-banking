import frappe
from erpnext import get_company_currency
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_accounting_dimensions,
)
from erpnext.accounts.doctype.payment_request.payment_request import (
	PaymentRequest,
)
from erpnext.accounts.doctype.tax_withholding_category.tax_withholding_category import (
	get_party_tax_withholding_details,
)
from erpnext.accounts.party import (
	get_party_account,
	get_party_account_currency,
	get_party_bank_account,
)
from erpnext.setup.utils import get_exchange_rate
from frappe import _, bold
from frappe.utils import flt, get_link_to_form, get_url_to_form, getdate

from india_banking.utils import (
	get_bank_address_details,
	validate_party_bank_account_details,
)


class BankPaymentRequest(PaymentRequest):
	def update_currency(self):
		if self.is_adhoc:
			currency_field = (
				"salary_currency"
				if self.party_type == "Employee"
				else "default_currency"
			)
			self.currency = frappe.get_value(
				self.party_type, self.party, currency_field
			) or get_company_currency(self.company)
			self.party_account_currency = get_party_account_currency(
				self.party_type, self.party, self.company
			)

	def validate(self):
		if not self.net_total:
			self.net_total = self.grand_total

		if self.payment_request_type != "Outward":
			super().validate()
			return

		self.set_default_value()

		if (
			self.apply_tax_withholding_amount
			and self.tax_withholding_category
			and self.is_adhoc
		):
			tds_amount = self.calculate_pr_tds(self.net_total)
			self.taxes_deducted = tds_amount
			self.grand_total = self.net_total - self.taxes_deducted
		else:
			self.grand_total = self.net_total or 0

		if not self.is_adhoc:
			self.set_exchange_rate()
			super().validate()
		else:
			self.update_currency()
			if self.is_new():
				self.status = "Draft"
			if self.reference_doctype or self.reference_name:
				frappe.throw(_("Payments with references cannot be marked as ad-hoc"))

		if self.remarks:
			self.remarks = self.remarks[:48]

	def validate_forex_transaction_mandatory_fields(self):
		mandatory_fields = [
			"swift_number",
			"branch_code",
			"bank_address",
		]
		missing_fields = [field for field in mandatory_fields if not self.get(field)]
		if missing_fields:
			link = get_link_to_form("Bank Account", self.bank_account)
			frappe.throw(
				_(
					"For non-INR currency, the following field's ({0}) required in bank account - {1}</br>"
				).format(bold(", ".join(missing_fields)), bold(link))
			)
		if self.bank_address:
			self.validate_forex_transaction_address_mandatory()

	def validate_forex_transaction_address_mandatory(self):
		get_bank_address_details(self.bank_account, validate=True)

	def set_exchange_rate(self):
		if self.reference_doctype and self.reference_name:
			conversion_rate = frappe.get_value(
				self.reference_doctype,
				self.reference_name,
				"conversion_rate",
			)
			self.conversion_rate = conversion_rate or 1.0
		else:
			self.convertion_rate = get_exchange_rate(
				self.currency, self.party_account_currency, self.transaction_date
			)

	def set_default_value(self):
		if not self.transaction_date:
			self.transaction_date = getdate()

		if not self.payment_type:
			if payment_type := frappe.db.exists(
				"Payment Type",
				{
					"company": self.company,
					"is_default": 1,
				},
			):
				self.payment_type = payment_type

		if not self.bank_account:
			filters = {
				"party_type": self.party_type,
				"party": self.party,
				"is_default": 1,
				"disabled": 0,
			}
			if bank_account := frappe.get_value("Bank Account", filters, "name"):
				frappe.msgprint(
					"The default bank account is set to {}".format(
						frappe.bold(bank_account)
					)
				)
				self.bank_account = bank_account
				self.update({**self.get_bank_account_details()})

		if self.bank_account:
			self.mode_of_payment = "Wire Transfer"

		if self.bank_account and not self.bank_address:
			address = get_bank_address_details(self.bank_account)
			if address and address.name:
				self.bank_address = address.name

	def get_bank_account_details(self):
		if self.bank_account:
			return (
				frappe.get_value(
					"Bank Account",
					self.bank_account,
					["bank", "bank_account_no", "branch_code", "iban"],
					as_dict=1,
				)
				or {}
			)

	def on_submit(self):
		super().on_submit()

		if self.payment_request_type != "Outward":
			return

		if self.is_adhoc:
			self.db_set("status", "Initiated")

		if not self.grand_total or not self.net_total:
			frappe.throw(_("Amount cannot be zero"))

		self.validate_payment_type()
		self.validate_bank_account()
		self.validate_currency()

	def before_submit(self):
		if not self.is_adhoc:
			super().before_submit()
			return

		if (
			self.is_adhoc
			and self.currency != self.party_account_currency
			and self.party_account_currency == get_company_currency(self.company)
		):
			grand_total = self.grand_total

			convertion_rate = get_exchange_rate(
				self.currency, self.party_account_currency
			)

			self.convertion_rate = convertion_rate
			if not convertion_rate:
				frappe.throw(
					_("Exchange rate not found for {0} to {1} on {2}").format(
						self.currency,
						self.party_account_currency,
						self.transaction_date,
					)
				)

			self.outstanding_amount = flt(
				grand_total * convertion_rate,
				self.precision("outstanding_amount"),
			)

		else:
			self.convertion_rate = 1.0
			self.outstanding_amount = self.grand_total

		if self.currency != "INR" and self.payment_request_type == "Outward":
			self.validate_forex_transaction_mandatory_fields()

	def validate_currency(self):
		if self.payment_request_type != "Outward":
			super().validate_currency()
			return
		currency_field = (
			"salary_currency" if self.party_type == "Employee" else "default_currency"
		)
		transaction_currency = frappe.get_value(
			self.party_type, self.party, currency_field
		) or get_company_currency(self.company)
		if transaction_currency != self.currency:
			frappe.throw(f"Transaction currency must be in {transaction_currency}")

		party_account_currency = get_party_account_currency(
			self.party_type, self.party, self.company
		)
		if party_account_currency != self.party_account_currency:
			frappe.throw(
				f"Party account currency should be in {party_account_currency}"
			)

	def validate_payment_type(self):
		if not self.is_adhoc:
			return

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
		else:
			frappe.throw(
				_(
					f"Set Default <b><a href='/app/payment-type'>Payment Type</a></b> for company {frappe.bold(self.company)}".format(
						self.company
					)
				)
			)

		debit_account = frappe.db.get_value(
			"Payment Type", self.payment_type, "account"
		)

		if not debit_account:
			frappe.throw(
				_(
					"Debit account for Payment Type <b>{}</b> cannot be determined"
				).format(self.payment_type or "")
			)

	def validate_bank_account(self):
		if not self.bank_account:
			if validate_party_bank_account_details(self, update=True):
				return

		bank_account = get_party_bank_account(self.party_type, self.party)
		if not self.bank_account:
			if not bank_account:
				frappe.throw(
					_(
						"Default Bank Account is missing for {0} - {1}".format(
							self.party_type, frappe.bold(self.party)
						)
					)
				)
			else:
				self.bank_account = bank_account

		bank_account = frappe.get_doc("Bank Account", self.bank_account)
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
							get_url_to_form("Bank Account", bank_account.name),
							frappe.bold(bank_account),
						)
					),
				)

		if bank_account.currency != self.currency:
			frappe.throw(
				title="Invalid currency",
				msg=_(
					f"The party bank account currency ({bold(bank_account.currency)})  and the transaction currency ({bold(self.currency)}) cannot be different. Please select a matching currency."
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


@frappe.whitelist()
def make_payment_order(source_name, target_doc=None):
	from frappe.model.mapper import get_mapped_doc

	def set_missing_values(source, target):
		if target.references:
			if target.references[0].currency != target.currency:
				msg = f"Only <b>{target.references[0].currency}</b>-currency payment requests are permitted. As <b>{target.references[0].currency}</b> is already selected"
				frappe.throw(title="Invalid selection", msg=msg)
		target.payment_order_type = "Payment Request"
		account = get_party_account(source.party_type, source.party, source.company)

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
			"currency": source.currency,
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
