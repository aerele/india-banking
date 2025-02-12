# Copyright (c) 2024, Aerele Technologies Private Limited and contributors
# For license information, please see license.txt

import frappe
from frappe import _

from erpnext.accounts.doctype.payment_request.payment_request import ( 
	PaymentRequest, get_existing_payment_request_amount, get_dummy_message, get_gateway_details
)
from erpnext.accounts.doctype.tax_withholding_category.tax_withholding_category import get_party_tax_withholding_details


from erpnext.accounts.doctype.payment_request import payment_request as PR
from frappe.query_builder.functions import Abs, Sum

from erpnext.accounts.party import get_party_account, get_party_bank_account
from erpnext.accounts.utils import get_account_currency
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_accounting_dimensions,
)
from frappe.utils.data import flt, today

class BankPaymentRequest(PaymentRequest):
	def validate_adhoc_payment(self):
		if self.is_adhoc and not frappe.db.exists("Ad Hoc Comapny", {"company": self.company, "allow_ad_hoc": 1, "parent": 'India Banking Settings'}):
			frappe.throw(f"Ad hoc payments are not Accepted for <b>Company - {self.company}</b>")
		
		if self.party_type == "Employee" and self.party:
			if not frappe.get_value("Employee", self.party, "advance_payment_allowance"):
				frappe.throw("Employee Advance Payment Allowance Not Enabled")

	def validate(self):
		self.is_a_subscription = None
		self.validate_adhoc_payment()

		if self.apply_tax_withholding_amount and self.tax_withholding_category and self.payment_request_type == "Outward":
			if not self.net_total:
				self.net_total = self.grand_total
			tds_amount = self.calculate_pr_tds(self.net_total)
			self.taxes_deducted = tds_amount
			self.grand_total = self.net_total - self.taxes_deducted
		else:
			if self.net_total and not self.grand_total:
				self.grand_total = self.net_total
			if self.grand_total and self.net_total != self.grand_total and not self.apply_tax_withholding_amount:
				self.grand_total = self.net_total

		if not self.is_adhoc:
			if self.reference_doctype not in ["Payroll Entry"]:
				super().validate()
		else:
			if self.get("__islocal"):
				self.status = "Draft"
			if self.reference_doctype or self.reference_name:
				frappe.throw("Payments with references cannot be marked as ad-hoc")

		if self.docstatus == 1:
			self.valdidate_bank_for_wire_transfer()

	def validate_payment_request_amount(self):
		if self.reference_doctype in ["Payroll Entry"]:
			#bypass validation for payroll entry
			return

		existing_payment_request_amount = flt(
			get_existing_payment_request_amount(self.reference_doctype, self.reference_name)
		)

		docname = None
		if frappe.flags.update_amount or not self.is_new():
			docname = self.name

		existing_payment_request_amount_drafted = flt(
			get_existing_payment_request_amount(self.reference_doctype, self.reference_name, submitted=False, update=docname)
		)

		total_existing_payment_request_amount = existing_payment_request_amount + existing_payment_request_amount_drafted


		ref_doc = frappe.get_doc(self.reference_doctype, self.reference_name)

		if not hasattr(ref_doc, "order_type") or getattr(ref_doc, "order_type") != "Shopping Cart":
			if self.reference_doctype in ["Purchase Order"]:
				ref_amount = flt(ref_doc.rounded_total) or flt(ref_doc.grand_total)
			elif self.reference_doctype in ["Purchase Invoice"]:
				if ref_doc.rounded_total:
					ref_amount = flt(ref_doc.rounded_total)
				else:
					ref_amount = flt(ref_doc.grand_total)
			else:
				ref_amount = get_amount(ref_doc, self.payment_account)

			if total_existing_payment_request_amount + flt(self.net_total) > ref_amount:
				frappe.throw(
					frappe._("Total Bank Payment Request amount cannot be greater than {0} amount").format(
						self.reference_doctype
					)
				)

	def on_submit(self):
		debit_account = None
		if self.payment_type:
			debit_account = frappe.db.get_value("Payment Type", self.payment_type, "account")
		elif self.reference_doctype == "Purchase Invoice":
			debit_account = frappe.db.get_value(self.reference_doctype, self.reference_name, "credit_to")

		if not debit_account:
			frappe.throw("Debit account for Payment Type <b>{}</b> cannot be determined".format(self.payment_type))
		if not self.is_adhoc:
			super().on_submit()
		else:
			if self.payment_request_type == "Outward":
				self.db_set("status", "Initiated")
				return

		if self.reference_doctype == "Purchase Invoice":
			outstanding_amount = frappe.db.get_value("Purchase Invoice", self.reference_name, "outstanding_amount")
			if self.grand_total > outstanding_amount:
				frappe.throw("Grand Total cannot be greater than Invoice Outstanding Amount")

	def create_payment_entry(self, submit=True):
		payment_entry = super().create_payment_entry(submit=submit)
		payment_entry.source_doctype = self.payment_order_type
		if payment_entry.docstatus != 1 and self.payment_type:
			payment_entry.paid_to = frappe.db.get_value("Payment Type", self.payment_type, "account") or ""

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
		if self.mode_of_payment == "Wire Transfer" and not self.bank_account:
			frappe.throw(frappe._("Bank Account is missing for Wire Transfer Payments"))

		try:
			status = frappe.db.get_value("Bank Account", self.bank_account, "workflow_state")

			if self.mode_of_payment == "Wire Transfer" and status != "Approved":
				frappe.throw("Cannot proceed with un-approved bank account")
		except:
			frappe.throw("Workflow Not Found for Bank Account")


@frappe.whitelist()
def validate_payment_request_status(**args):
	total_bank_payment_request_amount = frappe.db.get_all(
		"Bank Payment Request", {
			"reference_doctype": args.get('ref_doctype'),
			"reference_name": args.get('ref_name'),
			"docstatus": 1
		},
		"sum(grand_total) as grand_total")

	if total_bank_payment_request_amount[0] and total_bank_payment_request_amount[0].get('grand_total'):
		if flt(total_bank_payment_request_amount[0].get('grand_total')) >= flt(args.get('grand_total')):
			return 'Completed'

	return ""

def get_employee_payemnt_details(journal_accounts):
	employee_bank_account_details = frappe.db.get_all('Bank Account',
		{
			'party_type': 'Employee',
			'disabled': 0,
			'is_default': 1
		}, 
		['name','party', 'party_type', 'bank', 'branch_code', 'bank_account_no', 'mobile_number', 'email', 'workflow_state']
	)

	employee_bank_account_details = {detail.get('party'): detail for detail in employee_bank_account_details}

	payment_details = []

	for journal_account in journal_accounts:
		employee_bank_details = employee_bank_account_details.get(journal_account.get('employee', ''))
		if not employee_bank_details:
			frappe.throw('Default Bank Account not found for Employee {0}'.format(journal_account.get('employee')))
		else:
			if employee_bank_details.get('workflow_state') != 'Approved':
				link = frappe.utils.get_link_to_form("Bank Account", employee_bank_details.get('name'))
				frappe.throw("Bank Account<b>({1})</b> for Employee {0} is not approved".format(
					journal_account.get('employee'), link)
				)

		journal_account = frappe._dict(journal_account)
		details = {
			"reference_doctype": "Journal Entry",
			"reference_name": journal_account.journal,
			"journal_entry_account": journal_account.name,
			"amount": journal_account.amount,
			"party_type": "Employee",
			"party": journal_account.employee,
			"mode_of_payment": "",
			"bank_account": employee_bank_details.name,
			"account": journal_account.account,
		}
		payment_details.append(details)

	return payment_details

@frappe.whitelist(allow_guest=True)
def make_bank_payment_request(**args):
	"""Make Bank payment request"""

	args = frappe._dict(args)

	ref_doc = frappe.get_doc(args.dt, args.dn)
	gateway_account = PR.get_gateway_details(args) or frappe._dict()

	grand_total = get_amount(ref_doc, gateway_account.get("payment_account"))

	bank_account = (
		get_party_bank_account(args.get("party_type"), args.get("party")) if args.get("party_type") else ""
	)

	if not bank_account:
		frappe.throw(frappe._("Default Bank Account is missing for {0} - {1}").format(args.get("party_type"), args.get("party")))

	draft_payment_request = frappe.db.get_value(
		"Bank Payment Request",
		{"reference_doctype": args.dt, "reference_name": args.dn, "docstatus": 0},
	)

	existing_paid_amount = get_existing_paid_amount(ref_doc.doctype, ref_doc.name)
	existing_payment_request_amount = get_existing_payment_request_amount(args.dt, args.dn)


	if existing_paid_amount:
		if ref_doc.party_account_currency == ref_doc.currency:
			if ref_doc.conversion_rate:
				grand_total -= flt(existing_paid_amount / ref_doc.conversion_rate)
			else:
				grand_total -= flt(existing_paid_amount)
		else:
			grand_total -= flt(existing_paid_amount / ref_doc.conversion_rate)

	if existing_payment_request_amount:
		grand_total -= existing_payment_request_amount

	party_account_currency = ref_doc.get("party_account_currency", "")

	if not party_account_currency:
		party_account = get_party_account(args.get("party_type"), ref_doc.get(args.get("party_type").lower()), ref_doc.company)
		party_account_currency = get_account_currency(party_account)

	if draft_payment_request:
		bpr = frappe.get_doc("Bank Payment Request", draft_payment_request)
		bpr.db_set("net_total", grand_total, update_modified=False)
		bpr.validate()
		frappe.db.set_value(
			"Bank Payment Request", draft_payment_request, {
				"net_total": bpr.net_total,
				"grand_total": bpr.grand_total,
				"taxes_deducted": bpr.taxes_deducted
				},
			update_modified=False
		)

	else:
		if grand_total <= 0:
			frappe.throw(frappe._("Bank Payment Entry is already created"))

		bpr = frappe.new_doc("Bank Payment Request")

		if not args.get("payment_request_type"):
			args["payment_request_type"] = (
				"Outward" if args.get("dt") in ["Purchase Order", "Purchase Invoice"] else "Inward"
			)

		bpr.payment_type = get_payment_type(ref_doc.company)

		bpr.update(
			{
				"payment_gateway_account": gateway_account.get("name"),
				"payment_gateway": gateway_account.get("payment_gateway"),
				"payment_account": gateway_account.get("payment_account"),
				"payment_channel": gateway_account.get("payment_channel"),
				"payment_request_type": args.get("payment_request_type"),
				"currency": ref_doc.currency,
				"company": ref_doc.company,
				"party_account_currency": party_account_currency,
				"grand_total": grand_total,
				"mode_of_payment": "Wire Transfer",
				"transaction_date": today(),
				"email_to": args.recipient_id or ref_doc.owner,
				"subject": frappe._("Bank Payment Request for {0}").format(args.dn),
				"message": gateway_account.get("message") or PR.get_dummy_message(ref_doc),
				"reference_doctype": args.dt,
				"reference_name": args.dn,
				"party_type": args.get("party_type") or "Customer",
				"party": args.get("party") or ref_doc.get("customer"),
				"bank_account": bank_account,
				"net_total": grand_total
			}
		)

		# Update dimensions
		bpr.update(
			{
				"cost_center": ref_doc.get("cost_center") or 
					frappe.get_value(ref_doc.get("doctype") + " Item",
						{'parent': ref_doc.get("name")}, 'cost_center'
					),
				"project": ref_doc.get("project") or 
					frappe.get_value(ref_doc.get("doctype") + " Item",
						{'parent': ref_doc.get("name")}, 'project'
					)
			}
		)

		for dimension in get_accounting_dimensions():
			bpr.update({dimension: ref_doc.get(dimension)})

		bpr.insert(ignore_permissions=True)

		if args.submit_doc:
			bpr.submit()

	if args.return_doc:
		return bpr

	return bpr.as_dict()

def update_payroll_entry(source, target):
	target.payment_order_type = "Payroll Entry"
	target.docstaus = 0
	target.status = 'Pending'

	for dimension in get_accounting_dimensions():
		target.update({dimension: source.get(dimension, '')})

	if get_employee_payemnt_details(source):
		for ref in get_employee_payemnt_details(source):
			target.append("references",ref)

def update_bank_entry(source, target):
	target.payment_order_type = "Journal Entry"
	target.docstaus = 0
	target.status = 'Pending'

	journal_accounts = frappe.db.sql("""
		SELECT 
			name, account, against_account, cost_center, debit as amount, exchange_rate, parent,
			party as employee, party_type, parent as journal
		FROM 
			`tabJournal Entry Account`
		WHERE
			parent = %s AND party_type = 'Employee' AND payment_status NOT IN ('Paid', 'Ordered')""", source.name, as_dict=1)
		
	if get_employee_payemnt_details(journal_accounts):
		for ref in get_employee_payemnt_details(journal_accounts):
			target.append("references",ref)
	

@frappe.whitelist()
def make_payment_order(source_name, target_doc=None, args= None):
	from frappe.model.mapper import get_mapped_doc

	def set_missing_values(source, target):
		target.payment_order_type = "Bank Payment Request"
		account = ""
		if source.payment_type:
			account = frappe.db.get_value("Payment Type", source.payment_type, "account")
		if source.reference_doctype == "Purchase Invoice":
			account = frappe.db.get_value(source.reference_doctype, source.reference_name, "credit_to")

		if source.is_adhoc and source.payment_type and source.party_type == "Supplier" and source.docstatus == 1:
			party_account = frappe.db.get_value("Party Account", {"parent": source.party, "parenttype": source.party_type, "company": source.company}, "account")
			if party_account:
				account = party_account

		for dimension in get_accounting_dimensions():
			target.update({dimension: source.get(dimension, '')})

		target.append(
			"references",
			{
				"reference_doctype": source.reference_doctype,
				"reference_name": source.reference_name,
				"amount": source.grand_total,
				"party_type": source.party_type,
				"party": source.party,
				"bank_payment_request": source_name,
				"mode_of_payment": source.mode_of_payment,
				"bank_account": source.bank_account,
				"account": account,
				"is_adhoc": source.is_adhoc,
				"cost_center": source.cost_center,
				"project": source.project,
				"tax_withholding_category": source.tax_withholding_category
			},
		)
		target.status = "Pending"

	def update_missing_values(source, target):
		target.payment_order_type = "Payment Entry"
		target.company_bank_account = source.bank_account
		target.party = ''

		account = ""
		if source.paid_to:
			account = source.paid_to

		for dimension in get_accounting_dimensions():
			target.update({dimension: source.get(dimension, '')})

		if source.references:
			target.append(
				"references",
				{
					"reference_doctype": source.references[0].reference_doctype,
					"reference_name": source.references[0].reference_name,
					"amount": source.references[0].total_amount,
					"party_type": source.party_type,
					"party": source.party,
					"mode_of_payment": source.mode_of_payment,
					"bank_account": get_party_bank_account(source.get("party_type"), source.get("party")) if source.get("party_type") else "",
					"account": account,
					"cost_center": source.cost_center,
					"project": source.project,
					"payment_entry":  source.name
				}
			)
		else:
			target.append(
				"references",
				{
					"reference_doctype": "Payment Entry",
					"reference_name": source.name,
					"amount": source.paid_amount,
					"party_type": source.party_type,
					"party": source.party,
					"mode_of_payment": "Wire Transfer",
					"bank_account": source.party_bank_account or get_party_bank_account(source.get("party_type"), source.get("party")),
					"account": source.paid_to,
					"cost_center": source.cost_center,
					"project": source.project,
					"payment_entry":  source.name
				}
			)
		target.status = "Pending"

	if args.get('ref_doctype') not in ["Payment Entry", "Payroll Entry", "Journal Entry"]:
		doclist = get_mapped_doc(
			"Bank Payment Request",
			source_name,
			{
				"Bank Payment Request": {
					"doctype": "Payment Order",
				}
			},
			target_doc,
			set_missing_values,
		)
	elif args.get('ref_doctype') == "Payment Entry":
		doclist = get_mapped_doc(
			"Payment Entry",
			source_name,
			{
				"Payment Entry": {
					"doctype": "Payment Order",
				}
			},
			target_doc,
			update_missing_values,
		)
	elif args.get('ref_doctype') == "Payroll Entry":
		doclist = get_mapped_doc(
			"Payroll Entry",
			source_name,
			{
				"Payroll Entry": {
					"doctype": "Payment Order",
				}
			},
			target_doc,
			update_payroll_entry,
		)
	elif args.get('ref_doctype') == "Journal Entry":
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

def get_existing_payment_request_amount(ref_dt, ref_dn, submitted= True, update=None, payment_term= None, salary_slip=None):
	"""
	Get the existing Bank payment request which are unpaid or partially paid for payment channel other than Phone
	and get the summation of existing paid Bank payment request for Phone payment channel.
	"""
			
	docstatus = 1 if submitted else 0

	where_conditions = "AND payment_term = '{0}'".format(payment_term.replace("%", "%%")) if payment_term  else "AND payment_term is null"

	if salary_slip:
		where_conditions += " AND salary_slip = '{0}'".format(salary_slip.replace("%", "%%"))

	existing_payment_request_amount = frappe.db.sql(
		"""
		select sum(net_total)
		from `tabBank Payment Request`
		where
			name != %s
			and reference_doctype = %s
			and reference_name = %s
			and docstatus = %s {0}
	""".format(where_conditions),
		(update or "", ref_dt, ref_dn, docstatus)
	)
	return flt(existing_payment_request_amount[0][0]) if existing_payment_request_amount else 0

def get_amount(ref_doc, payment_account=None):
	"""get amount based on doctype"""
	dt = ref_doc.doctype
	if dt in ["Sales Order", "Purchase Order"]:
		grand_total = flt(ref_doc.rounded_total) or flt(ref_doc.grand_total)
	elif dt in ["Sales Invoice", "Purchase Invoice"]:
		if not ref_doc.get("is_pos"):
			if ref_doc.party_account_currency == ref_doc.currency:
				if ref_doc.rounded_total:
					grand_total = flt(ref_doc.rounded_total)
				else:
					grand_total = flt(ref_doc.grand_total)
			else:
				if ref_doc.base_rounded_total:
					grand_total = flt(ref_doc.base_rounded_total) / ref_doc.conversion_rate
				else:
					grand_total = flt(ref_doc.base_grand_total) / ref_doc.conversion_rate
		elif dt == "Sales Invoice":
			for pay in ref_doc.payments:
				if pay.type == "Phone" and pay.account == payment_account:
					grand_total = pay.amount
					break
	elif dt == "POS Invoice":
		for pay in ref_doc.payments:
			if pay.type == "Phone" and pay.account == payment_account:
				grand_total = pay.amount
				break
	elif dt == "Fees":
		grand_total = ref_doc.outstanding_amount

	if grand_total > 0:
		return grand_total
	else:
		frappe.throw(frappe._("Bank Payment Entry is already created"))


@frappe.whitelist()
def get_existing_bank_entry(filters= None):
	condition = ''
	if filters and filters.get('refrence_name'):
		condition += "AND jea.reference_name = '{0}'".format(filters.get('refrence_name'))

	payroll_entries= frappe.db.sql(f"""
		SELECT 
			DISTINCT jea.reference_name as payroll_entry
		FROM 
			`tabJournal Entry`je 
		JOIN 
			`tabJournal Entry Account`jea 
		ON
			je.name = jea.parent 
		WHERE 
	 		je.docstatus != 2 AND jea.reference_type = 'Payroll Entry' AND je.voucher_type = 'Bank Entry'
			{condition}
	 """, as_dict= 1 )
	return [payroll_entry.payroll_entry for payroll_entry in payroll_entries]

@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_bank_entry(doctype, txt, searchfield, start, page_len, filters, as_dict):
	search_condition = ''
	if filters and filters.get('docs'):
		filters.get('docs').append('')
		exist_account = str(tuple(filters.get('docs')))
		search_condition += f" AND je.name NOT IN {exist_account} "

	if filters and filters.get('company'):
		search_condition += f"AND je.company = '{filters.get('company')}'"
	if txt:
		search_condition += f"AND je.name LIKE '%{txt}%'"

	bank_entries = frappe.db.sql(f"""
		SELECT 
			DISTINCT je.name, je.company, sum(jea.debit) as total, je.voucher_type
		FROM 
			`tabJournal Entry`je
		JOIN 
			`tabJournal Entry Account`jea
		ON
			je.name = jea.parent
		WHERE
	 		je.docstatus = 1 AND  jea.payment_status NOT IN ('Paid', 'Ordered') AND
			je.voucher_type = 'Bank Entry' AND jea.party_type= "Employee" {search_condition}
		GROUP BY 
			je.name, je.company, je.voucher_type
	 """, as_dict= 1)

	return bank_entries

def get_existing_paid_amount(doctype, name):
	PL = frappe.qb.DocType("Payment Ledger Entry")
	PER = frappe.qb.DocType("Payment Entry Reference")

	query = (
		frappe.qb.from_(PL)
		.select(Abs(Sum(PL.amount)).as_("total_paid_amount"))
		.where(PL.voucher_type.eq("Payment Entry"))
		.where(PL.against_voucher_type.eq(doctype))
		.where(PL.against_voucher_no.eq(name))
		.where(PL.amount < 0)
		.where(PL.delinked == 0)
	)
	response = query.run()

	return response[0][0] if response[0] else 0

def get_payment_type(company):
	payment_type = frappe.db.get_value(
			"Payment Type", {
				"company": company,
				"is_default": 1
			},
			"name"
		)
	if not payment_type:
		link = "<a href= '/app/payment-type'><b>Payment Type</b></a>"
		frappe.throw("Default {link} not found for Company <b>{0}</b>".format(company, link=link))

	return payment_type

@frappe.whitelist()
def make_payment_request_for_payroll_entry(**args):
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
			"Bank Payment Request",
			{
				"reference_doctype": args.doctype,
				"reference_name": args.docname,
				"salary_slip": salary_details.get("salary_slip"),
				"docstatus": 0,
			},
		)

		# fetches existing bank payment request `grand_total` amount
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
				"Bank Payment Request",
				draft_payment_request,
				"grand_total",
				grand_total,
				update_modified=False,
			)
			pr = frappe.get_doc("Bank Payment Request", draft_payment_request)
		else:
			pr = frappe.new_doc("Bank Payment Request")
			pr.company = ref_doc.company

			args["payment_request_type"] = "Outward"

			party_type = "Employee"
			party_name = ""
			if salary_details.get("party"):
				party_name = frappe.get_value(
					"Employee", salary_details.get("party"), "employee_name"
				)

			party_account_currency = "INR"

			payment_type = get_payment_type(ref_doc.company)

			pr.update(
				{
					"payment_gateway_account": gateway_account.get("name"),
					"payment_gateway": gateway_account.get("payment_gateway"),
					"payment_account": gateway_account.get("payment_account"),
					"payment_channel": gateway_account.get("payment_channel"),
					"payment_request_type": args.get("payment_request_type"),
					"currency": ref_doc.currency,
					"payment_type": payment_type,
					"party_account_currency": party_account_currency,
					"net_total": grand_total,
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
		frappe.msgprint(f"{count} Bank Payment request Created")