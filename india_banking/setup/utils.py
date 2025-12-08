import frappe
from frappe.utils import get_abbr


def before_tests():
	from erpnext.setup.utils import before_tests as erpnext_before_tests

	erpnext_before_tests()


def create_company(company_name, **kwargs):
	if frappe.db.exists("Company", company_name):
		return frappe.get_doc("Company", company_name)

	company = frappe.get_doc(
		{
			"doctype": "Company",
			"company_name": company_name or "IB Company",
			"country": kwargs.get("country") or "India",
			"default_currency": kwargs.get("default_currency") or "INR",
			"abbr": kwargs.get("abbr") or get_abbr(company_name),
		}
	)

	if not kwargs.get("do_not_save"):
		company.save()

	return company


def create_bank_account(
	bank_name, account_no, is_company_account=0, account=None, **kwargs
):
	if bank_account := frappe.db.exists(
		"Bank Account",
		{
			"bank": bank_name,
			"account_number": account_no,
			"is_company_account": is_company_account,
		},
	):
		return frappe.get_doc("Bank Account", bank_account)

	bank_account = frappe.get_doc(
		{
			"doctype": "Bank Account",
			"account_name": kwargs.get("account_name") or account_no,
			"bank_account_no": account_no,
			"bank": bank_name,
			"branch_code": kwargs.get("branch_code") or kwargs.get("ifsc_code"),
			"currency": kwargs.get("currency") or "INR",
			"email": kwargs.get("email") or "bank1@test.in",
			"is_company_account": is_company_account,
			"company": kwargs.get("company") or "IB Company",
			"account": account,
			"party_type": kwargs.get("party_type"),
			"party": kwargs.get("party"),
		}
	)

	if not kwargs.get("do_not_save"):
		return bank_account.save()

	return bank_account


def create_supplier(supplier_name, default_currency=None, **kwargs):
	if frappe.db.exists("Supplier", supplier_name):
		return frappe.get_doc("Supplier", supplier_name)

	supplier = frappe.get_doc(
		{
			"doctype": "Supplier",
			"supplier_name": supplier_name,
			"default_currency": default_currency,
		}
	)

	if not kwargs.get("do_not_save"):
		supplier.save()

	return supplier
