import frappe


@frappe.whitelist()
def make_payment_order(source_name, target_doc=None, args=None):
	from frappe.model.mapper import get_mapped_doc

	def update_bank_entry(source, target):
		target.payment_order_type = "Journal Entry"
		target.docstaus = 0
		target.status = "Pending"

		journal_accounts = frappe.db.sql(
			"""
			SELECT
				name, account, against_account, cost_center, debit as amount, exchange_rate, parent,
				party as employee, party_type, parent as journal
			FROM
				`tabJournal Entry Account`
			WHERE
				parent = %s AND party_type = 'Employee' AND payment_status NOT IN ('Paid', 'Ordered')""",
			source.name,
			as_dict=1,
		)

		if employee_payemnt_details := get_employee_payemnt_details(journal_accounts):
			for ref in employee_payemnt_details:
				target.append("references", ref)

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


def get_employee_payemnt_details(journal_accounts):
	fields = [
		"name",
		"party",
		"party_type",
		"bank",
		"branch_code",
		"bank_account_no",
		"mobile_number",
		"email",
	]
	activate_workflow_on_bank_account = frappe.get_single(
		"India Banking Settings"
	).activate_workflow_on_bank_account
	if activate_workflow_on_bank_account:
		fields.append("workflow_state")

	employee_bank_account_details = frappe.db.get_all(
		"Bank Account",
		{"party_type": "Employee", "disabled": 0, "is_default": 1},
	)

	employee_bank_account_details = {
		detail.get("party"): detail for detail in employee_bank_account_details
	}

	payment_details = []

	for journal_account in journal_accounts:
		employee_bank_details = employee_bank_account_details.get(
			journal_account.get("employee", "")
		)
		if not employee_bank_details:
			frappe.throw(
				"Default Bank Account not found for Employee {0}".format(
					journal_account.get("employee")
				)
			)
		else:
			if (
				employee_bank_details.get("workflow_state") != "Approved"
				and activate_workflow_on_bank_account
			):
				link = frappe.utils.get_link_to_form(
					"Bank Account", employee_bank_details.get("name")
				)
				frappe.throw(
					"Bank Account<b>({1})</b> for Employee {0} is not approved".format(
						journal_account.get("employee"), link
					)
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


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_bank_entry(doctype, txt, searchfield, start, page_len, filters, as_dict):
	search_condition = ""
	if filters and filters.get("docs"):
		filters.get("docs").append("")
		exist_account = str(tuple(filters.get("docs")))
		search_condition += f" AND je.name NOT IN {exist_account} "

	if filters and filters.get("company"):
		search_condition += f"AND je.company = '{filters.get('company')}'"
	if txt:
		search_condition += f"AND je.name LIKE '%{txt}%'"

	bank_entries = frappe.db.sql(
		f"""
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
	 """,
		as_dict=1,
	)

	return bank_entries
