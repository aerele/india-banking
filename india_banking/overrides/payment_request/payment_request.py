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
		self.grand_total = self.net_total or self.grand_total

		super().validate()

		if self.remarks:
			self.remarks = self.remarks[:48]

	def validate_and_update_gst_payables(self, update=False):
		if "india_compliance" not in frappe.get_installed_apps():
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
			gst_payable_totals = frappe.db.get_all(
				f"{self.reference_doctype} Item",
				filters={"parent": self.reference_name},
				fields=[
					"SUM(igst_amount) as total_igst",
					"SUM(cgst_amount) as total_cgst",
					"SUM(sgst_amount) as total_sgst",
				],
			)

			total_igst, total_cgst, total_sgst = 0, 0, 0
			if gst_payable_totals:
				total_igst = gst_payable_totals[0].total_igst or 0
				total_cgst = gst_payable_totals[0].total_cgst or 0
				total_sgst = gst_payable_totals[0].total_sgst or 0

			total_gst_payable_amount = total_igst + total_cgst + total_sgst

		return total_gst_payable_amount

	def set_default_value(self):
		# Update net total if not set
		if not self.net_total:
			self.net_total = self.grand_total

		# Set transaction date as today if not set
		if not self.transaction_date:
			self.transaction_date = getdate()

		# Set default bank account if not set
		if not self.bank_account:
			filters = {
				"party_type": self.party_type,
				"party": self.party,
				"is_default": 1,
				"disabled": 0,
			}
			self.bank_account = frappe.get_value("Bank Account", filters, "name")

		# Set default mode of payment if bank account is set
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

		self.validate_bank_account()
		self.validate_party_account()

		super().on_submit()

	def validate_party_account(self):
		party_account = _get_party_account(
			self.party_type,
			self.party,
			self.company,
		)
		if not party_account:
			frappe.throw(
				_(
					"No accounting {0} Account is defined for {1} - {2}".format(
						self.party_type,
						self.party_type,
						frappe.bold(self.party),
					)
				)
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
			"India Banking Settings", "enable_bank_account_workflow"
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
			"cost_center": source.cost_center,
			"project": source.project,
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
	if source.reference_doctype == "Purchase Invoice":
		account = frappe.db.get_value(
			source.reference_doctype, source.reference_name, "credit_to"
		)
	else:
		party_account = _get_party_account(
			source.party_type, source.party, source.company
		)
		account = party_account

	return account
