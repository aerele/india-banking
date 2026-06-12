import frappe
from frappe.utils import get_abbr


def before_tests():
	try:
		from erpnext.setup.utils import before_tests as erpnext_before_tests
	except ImportError:
		return
	else:
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
			"is_default": kwargs.get("is_default") or 0,
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

	if kwargs.get("gstin"):
		supplier.gstin = kwargs.get("gstin")
		supplier.gst_category = kwargs.get("gst_category") or "Registered Regular"

	if not kwargs.get("do_not_save"):
		supplier.save()

	return supplier


def create_item(item_name, item_group=None, **kwargs):
	if frappe.db.exists("Item", item_name):
		return frappe.get_doc("Item", item_name)

	item = frappe.new_doc("Item")
	item.item_code = kwargs.get("item_code") or item_name
	item.item_name = item_name
	item.item_group = item_group or "All Item Groups"
	item.is_stock_item = kwargs.get("is_stock_item") or 0
	if kwargs.get("is_stock_item"):
		item.stock_uom = kwargs.get("stock_uom") or "Nos"
	item.gst_hsn_code = kwargs.get("gst_hsn_code")

	if not kwargs.get("do_not_save"):
		item.save()

	return item


def create_address(address_title, address_line1, address_type="Billing", **kwargs):
	if address := frappe.db.exists(
		"Address",
		{
			"address_title": address_title,
			"address_type": address_type,
		},
	):
		return frappe.new_doc("Address", address)

	address = frappe.new_doc("Address")
	address.address_title = address_title
	address.address_type = address_type
	address.address_line1 = address_line1
	address.city = kwargs.get("city", "Tirupur")
	address.state = kwargs.get("state", "Tamil Nadu")
	address.country = "India"
	address.pincode = kwargs.get("pincode")
	address.gstin = kwargs.get("gstin")
	address.append(
		"links",
		{
			"link_doctype": kwargs.get("link_doctype"),
			"link_name": kwargs.get("link_name"),
		},
	)
	address.save()

	return address


class GSTCompanySetup:
	def __init__(self):
		self.company_name = "IB GST Company"
		self.abbr = "IBGC"
		self._create_gst_company()
		self._create_fiscal_year()
		self.supplier = self.create_gst_supplier()
		self.item = self.create_gst_item()

	def _create_fiscal_year(self):
		fy = frappe.get_all("Fiscal Year", pluck="name")
		for f in fy:
			fy_doc = frappe.get_doc("Fiscal Year", f)
			fy_doc.append("companies", {"company": self.company_name})
			fy_doc.save()

		frappe.clear_cache(doctype="Fiscal Year")

	def _create_gst_company(self):
		create_company(
			company_name=self.company_name,
			abbr=self.abbr,
			country="India",
			default_currency="INR",
			gstin="33AASCA2210M1ZQ",
		)
		create_address(
			address_title="IB GST Company Address",
			address_line1="123, GST Road, Tirupur",
			pincode="641602",
			gstin="33AASCA2210M1ZQ",
			link_doctype="Company",
			link_name=self.company_name,
		)

	def create_gst_supplier(self):
		supplier = create_supplier(
			supplier_name="IB GST Supplier",
			default_currency="INR",
			gstin="33AAICT9714H1Z5",
			gst_category="Registered Regular",
		)
		create_address(
			address_title="IB GST Supplier Address",
			address_line1="456, Supplier Street, Chennai",
			pincode="600001",
			gstin="33AAICT9714H1Z5",
			link_doctype="Supplier",
			link_name=supplier.name,
		)
		return supplier

	def create_gst_item(self):
		item = create_item(
			item_name="IB GST Item",
			item_group="All Item Groups",
			gst_hsn_code="010121",
			do_not_save=True,
		)
		item.append(
			"taxes",
			{
				"item_tax_template": f"GST 18% - {self.abbr}",
				"tax_category": "In-State",
				"valid_from": "2020-01-01",
				"minimum_net_rate": 1,
				"maximum_net_rate": 100000,
			},
		)
		item.save()
		return item
