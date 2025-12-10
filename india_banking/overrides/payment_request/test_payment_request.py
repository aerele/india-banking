import frappe
from frappe.tests.utils import FrappeTestCase

from india_banking.setup.utils import (
	create_bank_account,
	create_company,
	create_supplier,
)


class TestPaymentRequestOverrides(FrappeTestCase):
	def setUp(self):
		super().setUp()

		self.company = create_company("IB Company")
		self.supplier = create_supplier("IB Supplier")
		self.supplier_bank_account = create_bank_account(
			bank_name="HDFC Bank",
			account_no="9876543210",
			ifsc_code="HDFC0005943",
			party_type="Supplier",
			party=self.supplier.name,
			is_default=1,
		)

	def tearDown(self):
		super().tearDown()
		frappe.db.rollback()

	def create_bank_payment_request(
		self, is_adhoc, party_type, party, payment_request_type, net_total, **kwargs
	):
		pr = frappe.get_doc(
			{
				"is_adhoc": is_adhoc,
				"doctype": "Payment Request",
				"company": self.company.name,
				"party_type": party_type,
				"party": party,
				"payment_request_type": payment_request_type,
				"net_total": net_total,
				"reference_doctype": kwargs.get("reference_doctype"),
				"reference_name": kwargs.get("reference_name"),
			}
		)

		if kwargs.get("tax_withholding_category"):
			pr.update(
				{
					"tax_withholding_category": kwargs.get("tax_withholding_category"),
					"apply_tax_withholding_amount": 1,
				}
			)

		return pr

	def create_tds_category(self):
		"""Helper method to create a TDS category for testing"""
		from frappe.utils import add_days, today

		category_name = "Test TDS Category"

		# Check if category already exists
		if frappe.db.exists("Tax Withholding Category", category_name):
			return frappe.get_doc("Tax Withholding Category", category_name)

		# Create TDS account if not exists
		tds_account = f"TDS Payable - {self.company.abbr}"
		if not frappe.db.exists("Account", tds_account):
			frappe.get_doc(
				{
					"doctype": "Account",
					"account_name": "TDS Payable",
					"company": self.company.name,
					"parent_account": f"Duties and Taxes - {self.company.abbr}",
					"account_type": "Tax",
					"report_type": "Balance Sheet",
					"root_type": "Liability",
				}
			).insert()

		# Create the tax withholding category
		tds_category = frappe.get_doc(
			{
				"doctype": "Tax Withholding Category",
				"name": category_name,
				"category_name": category_name,
				"rates": [
					{
						"from_date": add_days(today(), -365),
						"to_date": add_days(today(), 365),
						"tax_withholding_rate": 10,
						"single_threshold": 1,
						"cumulative_threshold": 1,
					}
				],
				"accounts": [{"company": self.company.name, "account": tds_account}],
			}
		)
		tds_category.insert()

		return tds_category

	def test_default_value_in_payment_request(self):
		"""Test to verify default value in Payment Request document"""
		# Create a new Payment Request document
		payment_request = self.create_bank_payment_request(
			is_adhoc=True,
			party_type="Supplier",
			party=self.supplier.name,
			payment_request_type="Outward",
			net_total=1500.00,
		)
		# Check default values before inserting the document
		self.assertFalse(payment_request.grand_total)
		self.assertFalse(payment_request.transaction_date)
		self.assertFalse(payment_request.bank_account)
		self.assertFalse(payment_request.mode_of_payment)

		# Insert the document and verify the default values again
		payment_request.insert()
		payment_request.reload()
		self.assertEqual(payment_request.grand_total, payment_request.net_total)
		self.assertEqual(payment_request.transaction_date, frappe.utils.getdate())
		self.assertEqual(payment_request.bank_account, self.supplier_bank_account.name)
		self.assertEqual(payment_request.mode_of_payment, "Wire Transfer")

	def test_ad_hoc_payment_with_reference_not_allowed(self):
		"""Test to verify that ad-hoc payment with reference is not allowed"""
		# Create a new Payment Request document with reference
		payment_request = self.create_bank_payment_request(
			is_adhoc=True,
			party_type="Supplier",
			party=self.supplier.name,
			payment_request_type="Bank Payment",
			net_total=2000.00,
			reference_doctype="Purchase Order",
		)

		# Attempt to insert the document and expect a ValidationError
		with self.assertRaises(frappe.ValidationError) as error:
			payment_request.insert()

		self.assertIn(
			"Payments with references cannot be marked as ad-hoc",
			str(error.exception),
		)

	def test_non_ad_hoc_payment_without_reference_not_allowed(self):
		"""Test to verify that non ad-hoc payment without reference is not allowed"""
		# Create a new Payment Request document without reference
		payment_request = self.create_bank_payment_request(
			is_adhoc=False,
			party_type="Supplier",
			party=self.supplier.name,
			payment_request_type="Bank Payment",
			net_total=2500.00,
		)

		# Attempt to insert the document and expect a ValidationError
		with self.assertRaises(frappe.ValidationError):
			payment_request.insert()

	def test_adhoc_payment_with_tax_category(self):
		# Create a Payment Request with TDS category
		tds_category = self.create_tds_category()

		payment_request = self.create_bank_payment_request(
			is_adhoc=True,
			party_type="Supplier",
			party=self.supplier.name,
			payment_request_type="Outward",
			net_total=10000.00,
			reference_doctype=None,
			tax_withholding_category=tds_category.name,
		)

		# Insert the document and reload
		payment_request.insert()
		payment_request.reload()

		# Calculate expected TDS amount (10% of net total)
		expected_tds = 1000.00

		# Verify TDS calculation
		self.assertEqual(payment_request.taxes_deducted, expected_tds)
		self.assertEqual(
			payment_request.grand_total, payment_request.net_total - expected_tds
		)

	def test_tax_calculation_without_tds(self):
		# Create a Payment Request without TDS
		payment_request = self.create_bank_payment_request(
			is_adhoc=True,
			party_type="Supplier",
			party=self.supplier.name,
			payment_request_type="Outward",
			net_total=5000.00,
		)

		payment_request.insert()
		payment_request.reload()

		# Without TDS, grand_total should equal net_total
		self.assertEqual(payment_request.grand_total, payment_request.net_total)
		self.assertEqual(payment_request.grand_total, 5000.00)
		self.assertFalse(payment_request.taxes_deducted or 0)
