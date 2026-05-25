import frappe
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_accounting_dimensions,
)
from erpnext.accounts.doctype.payment_request.payment_request import (
	PaymentRequest,
	get_existing_payment_request_amount,
)
from erpnext.accounts.party import get_party_account as _get_party_account
from erpnext.accounts.party import get_party_bank_account
from frappe import _, bold
from frappe.query_builder.functions import Sum
from frappe.utils import (
	flt,
	get_link_to_form,
	get_link_to_report,
	get_url_to_form,
	getdate,
)


class BankPaymentRequest(PaymentRequest):
	def validate(self):
		self.set_default_value()
		if not self.net_total:
			self.net_total = self.grand_total

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

	def validate_and_update_gst_payables(self, update=False):
		if self.is_adhoc or "india_compliance" not in frappe.get_installed_apps():
			return

		if frappe.flags.ignore_hold_gst_payables:
			return

		if (
			self.party_type == "Supplier"
			and not self.hold_gst_payables
			and self.docstatus == 0
		):
			self.hold_gst_payables = frappe.db.get_value(
				self.party_type, self.party, "hold_gst_payables"
			)

		if not self.hold_gst_payables:
			return

		ref_doc = frappe.get_doc(self.reference_doctype, self.reference_name)
		existing_payment_request_amount = get_existing_payment_request_amount(ref_doc)
		gst_payable_amount = self.get_gst_payable_amount()

		if update:
			applicable_payment_amount = self.grand_total - gst_payable_amount
			if applicable_payment_amount <= 0:
				applicable_payment_amount = 0
				link = get_link_to_report("Bank GST Payables")
				msg = "We observed the following:"
				msg += "<ul><li>Total Requested Amount: {}</li>".format(
					bold(existing_payment_request_amount)
				)
				if ref_doc.doctype == "Purchase Invoice":
					msg += "<li>Outstanding Amount: {}</li>".format(
						ref_doc.outstanding_amount
					)
				elif ref_doc.doctype == "Purchase Order":
					msg += "<li>Order Total: {}</li>".format(
						bold(ref_doc.base_grand_total)
					)
					msg += "<li>Advance Paid: {}</li>".format(
						bold(ref_doc.advance_paid)
					)

				msg += "<li>Net Payable(GST Exclusive): {}</li>".format(
					bold(applicable_payment_amount)
				)
				msg += "<li>GST Payables: {}</li></ul>".format(
					bold(flt(gst_payable_amount))
				)
				msg += "Please use the {} report to process GST payables.".format(
					bold(link)
				)
				frappe.throw(title="Hold Supplier GST Payable", msg=msg)
			self.net_total = applicable_payment_amount
		else:
			if self.hold_gst_payables:
				outstanding_amount = 0
				if ref_doc.doctype == "Purchase Invoice":
					outstanding_amount = ref_doc.outstanding_amount
				elif ref_doc.doctype == "Purchase Order":
					outstanding_amount = ref_doc.base_grand_total - flt(
						ref_doc.advance_paid
					)
				applicable_payment_amount = (
					outstanding_amount
					- existing_payment_request_amount
					- gst_payable_amount
				)
				if gst_payable_amount and applicable_payment_amount < 0:
					applicable_payment_amount = 0
					link = get_link_to_report("Bank GST Payables")
					frappe.throw(
						title="Hold Supplier GST Payable",
						msg="Supplier {} is marked for Hold GST. The eligible payment amount is < {}. use {} report to make GST payable against".format(
							bold(link), bold(applicable_payment_amount), link
						),
					)

				if (self.net_total or self.grand_total) > applicable_payment_amount:
					link = get_link_to_form("Supplier", self.party)
					frappe.throw(
						title="Hold Supplier GST Payable",
						msg="Supplier {} is marked for Hold GST. The eligible payment <b>amount</b> is <b><=</b> {}".format(
							bold(link), bold(applicable_payment_amount)
						),
					)

	def get_gst_payable_amount(self):
		total_gst_payable_amount = 0
		if (
			self.reference_doctype
			and self.reference_doctype in ["Purchase Invoice", "Purchase Order"]
			and self.reference_name
		):
			Item = frappe.qb.DocType(f"{self.reference_doctype} Item")
			gst_payable_totals = (
				frappe.qb.from_(Item)
				.select(
					Sum(Item.igst_amount).as_("total_igst"),
					Sum(Item.cgst_amount).as_("total_cgst"),
					Sum(Item.sgst_amount).as_("total_sgst"),
				)
				.where(Item.parent == self.reference_name)
				.run(as_dict=True)
			)

			total_igst, total_cgst, total_sgst = 0, 0, 0
			if gst_payable_totals:
				total_igst = gst_payable_totals[0].total_igst or 0
				total_cgst = gst_payable_totals[0].total_cgst or 0
				total_sgst = gst_payable_totals[0].total_sgst or 0

			total_gst_payable_amount = total_igst + total_cgst + total_sgst

		return total_gst_payable_amount

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
			self.bank_account = frappe.get_value("Bank Account", filters, "name")

		if self.bank_account:
			self.mode_of_payment = "Wire Transfer"

	def before_insert(self):
		self.validate_and_update_gst_payables(update=True)

	def before_submit(self):
		super().before_submit()
		self.validate_and_update_gst_payables()

	def on_submit(self):
		if not self.grand_total or not self.net_total:
			frappe.throw(_("Amount cannot be zero"))

		# self.validate_payment_type() # will be deprecated in v16
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
				title=_(
					f"The party bank account currency should be in {self.currency}."
				),
				msg=_(
					"{}-{}- Bank Account <a href='{}'>{}</a>".format(
						self.party_type,
						self.party,
						get_url_to_form("Bank Account", self.bank_account),
						frappe.bold(self.bank_account),
					)
				),
			)

		if self.bank_account:
			bank_doc = frappe.get_doc("Bank Account", self.bank_account)
			if bank_doc.party_type and bank_doc.party:
				if (
					bank_doc.party_type != self.party_type
					or bank_doc.party != self.party
				):
					frappe.throw(
						_(
							"Bank Account {0} does not belong to {1}-{2}".format(
								frappe.bold(self.bank_account),
								frappe.bold(self.party_type),
								frappe.bold(self.party),
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


@frappe.whitelist()
def make_payment_order(source_name, target_doc=None):
	from frappe.model.mapper import get_mapped_doc

	def set_missing_values(source, target):
		target.payment_order_type = "Payment Request"
		account = get_party_account(source)

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


def get_party_account(source):
	account = None
	if source.payment_type:
		account = frappe.db.get_value("Payment Type", source.payment_type, "account")
	if source.reference_doctype == "Purchase Invoice":
		account = frappe.db.get_value(
			source.reference_doctype, source.reference_name, "credit_to"
		)
	if not account:
		account = _get_party_account(
			source.party_type,
			source.party,
			source.company,
		)

		if not account:
			frappe.throw(
				_(
					"Cannot find default account for {0} {1}".format(
						source.party_type, source.party
					)
				)
			)

	return account
