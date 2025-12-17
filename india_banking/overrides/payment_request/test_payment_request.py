import click
import frappe
from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import (
	make_purchase_invoice,
)
from erpnext.buying.doctype.purchase_order.test_purchase_order import (
	create_purchase_order,
)
from frappe.tests.utils import FrappeTestCase, change_settings

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

		if not is_adhoc:
			pr.grand_total = kwargs.get("grand_total") or net_total

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

	def test_validate_remark_size(self):
		# Create a new Payment Request document with oversized remark
		remarks = "A" * 50
		payment_request = self.create_bank_payment_request(
			is_adhoc=True,
			party_type="Supplier",
			party=self.supplier.name,
			payment_request_type="Outward",
			net_total=3000.00,
		)
		payment_request.remark = remarks
		payment_request.insert()
		payment_request.reload()

		# Verify that remark is truncated to below 50 characters
		self.assertLessEqual(len(payment_request.remark), 50)

	@change_settings("GST Settings", {"require_supplier_invoice_no": 0})
	def make_purchase_invoice_with_gst(self, **kwargs):
		from india_banking.setup.utils import GSTCompanySetup

		gst_setup = GSTCompanySetup()

		# Make Purchase invoice
		pi = make_purchase_invoice(
			company=gst_setup.company_name or kwargs.get("company"),
			supplier=gst_setup.supplier.name or kwargs.get("supplier"),
			item_code=gst_setup.item.name or kwargs.get("item_code"),
			item_name=gst_setup.item.name or kwargs.get("item_name"),
			qty=1,
			rate=100,
			price_list_rate=100,
			uom="Nos",
			warehouse=f"Stores - {gst_setup.abbr}",
			supplier_warehouse=f"Stores - {gst_setup.abbr}",
			expense_account=f"Cost of Goods Sold - {gst_setup.abbr}",
			cost_center=f"Main - {gst_setup.abbr}",
			do_not_save=True,
		)

		for item in pi.items:
			item.item_tax_template = f"GST 18% - {gst_setup.abbr}"
		pi.tax_category = "In-State"
		pi.taxes_and_charges = f"Input GST In-state - {gst_setup.abbr}"

		pi.set_taxes()
		pi.calculate_taxes_and_totals()
		pi.save()
		pi.submit()

		return pi

	@change_settings("GST Settings", {"require_supplier_invoice_no": 0})
	def make_purchase_order_with_gst(self, **kwargs):
		from india_banking.setup.utils import GSTCompanySetup

		gst_setup = GSTCompanySetup()

		# Make Purchase Order
		po = create_purchase_order(
			company=gst_setup.company_name or kwargs.get("company"),
			supplier=gst_setup.supplier.name or kwargs.get("supplier"),
			item_code=gst_setup.item.name or kwargs.get("item_code"),
			item_name=gst_setup.item.name or kwargs.get("item_name"),
			qty=1,
			rate=100,
			price_list_rate=100,
			uom="Nos",
			warehouse=f"Stores - {gst_setup.abbr}",
			supplier_warehouse=f"Stores - {gst_setup.abbr}",
			expense_account=f"Cost of Goods Sold - {gst_setup.abbr}",
			cost_center=f"Main - {gst_setup.abbr}",
			do_not_save=True,
		)

		for item in po.items:
			item.item_tax_template = f"GST 18% - {gst_setup.abbr}"
		po.tax_category = "In-State"
		po.taxes_and_charges = f"Input GST In-state - {gst_setup.abbr}"

		po.set_taxes()
		po.calculate_taxes_and_totals()
		po.save()
		po.submit()

		return po

	def test_gst_hold_payable_with_purchase_invoice(self):
		if "india_compliance" not in frappe.get_installed_apps():
			click.echo(
				"india_compliance not installed, skipping test_gst_hold_payable_with_purchase_invoice"
			)
			return

		# Create a Purchase Invoice with GST
		purchase_invoice = self.make_purchase_invoice_with_gst()

		# Enable hold_gst_payables on supplier
		frappe.db.set_value("Supplier", self.supplier.name, "hold_gst_payables", 1)

		# Create Payment Request for the Purchase Invoice
		payment_request = self.create_bank_payment_request(
			is_adhoc=False,
			party_type="Supplier",
			party=self.supplier.name,
			payment_request_type="Outward",
			net_total=118.00,
			reference_doctype="Purchase Invoice",
			reference_name=purchase_invoice.name,
		)

		# Insert should auto-adjust net_total to exclude GST
		payment_request.insert()
		payment_request.reload()

		# Expected: net_total should be 10000 (excluding 1800 GST)
		self.assertEqual(payment_request.net_total, 100.00)
		self.assertEqual(payment_request.hold_gst_payables, 1)

		# Clean up older data
		payment_request.delete(ignore_permissions=True)

		frappe.clear_cache("Payment Request")

		frappe.db.set_value("Supplier", self.supplier.name, "hold_gst_payables", 0)

		payment_request1 = self.create_bank_payment_request(
			is_adhoc=False,
			party_type="Supplier",
			party=self.supplier.name,
			payment_request_type="Outward",
			net_total=118.00,
			reference_doctype="Purchase Invoice",
			reference_name=purchase_invoice.name,
		)

		# Insert should NOT adjust net_total to exclude GST
		payment_request1.insert()
		payment_request1.reload()

		# Expected: net_total should be 118.00 as hold_gst_payables is disabled
		self.assertEqual(payment_request1.net_total, 118.00)
		self.assertEqual(payment_request1.hold_gst_payables, 0)

	def test_gst_hold_payable_with_purchase_order(self):
		if "india_compliance" not in frappe.get_installed_apps():
			click.echo(
				"India Compliance not installed, skipping test_gst_hold_payable_with_purchase_invoice"
			)

			return

		# Create a Purchase Order with GST
		purchase_order = self.make_purchase_order_with_gst()

		# Enable hold_gst_payables on supplier
		frappe.db.set_value("Supplier", self.supplier.name, "hold_gst_payables", 1)

		# Create Payment Request for the Purchase Order
		payment_request = self.create_bank_payment_request(
			is_adhoc=False,
			party_type="Supplier",
			party=self.supplier.name,
			payment_request_type="Outward",
			net_total=118.00,
			reference_doctype="Purchase Order",
			reference_name=purchase_order.name,
		)

		# Insert should auto-adjust net_total to exclude GST
		payment_request.insert()
		payment_request.reload()

		# Expected: net_total should be 10000 (excluding 1800 GST)
		self.assertEqual(payment_request.net_total, 100.00)
		self.assertEqual(payment_request.hold_gst_payables, 1)

		# Clean up older data
		payment_request.delete(ignore_permissions=True)
		frappe.clear_cache("Payment Request")

		frappe.db.set_value("Supplier", self.supplier.name, "hold_gst_payables", 0)
		payment_request1 = self.create_bank_payment_request(
			is_adhoc=False,
			party_type="Supplier",
			party=self.supplier.name,
			payment_request_type="Outward",
			net_total=118.00,
			reference_doctype="Purchase Order",
			reference_name=purchase_order.name,
		)

		# Insert should NOT adjust net_total to exclude GST
		payment_request1.insert()
		payment_request1.reload()

		# Expected: net_total should be 118.00 as hold_gst_payables is disabled
		self.assertEqual(payment_request1.net_total, 118.00)
		self.assertEqual(payment_request1.hold_gst_payables, 0)

	def test_hold_gst_payable_amount_exceeds_payment_amount(self):
		if "india_compliance" not in frappe.get_installed_apps():
			click.echo(
				"india_compliance not installed, skipping test_gst_hold_payable_with_purchase_invoice"
			)
			return

		# Create a Purchase Invoice with GST
		purchase_invoice = self.make_purchase_invoice_with_gst()

		# Enable hold_gst_payables on supplier
		frappe.db.set_value("Supplier", self.supplier.name, "hold_gst_payables", 1)

		# Create Payment Request for the Purchase Invoice
		payment_request = self.create_bank_payment_request(
			is_adhoc=False,
			party_type="Supplier",
			party=self.supplier.name,
			payment_request_type="Outward",
			net_total=118.00,
			reference_doctype="Purchase Invoice",
			reference_name=purchase_invoice.name,
		)

		# Insert should auto-adjust net_total to exclude GST
		payment_request.insert()
		payment_request.reload()

		# Expected: net_total should be 10000 (excluding 1800 GST)
		self.assertEqual(payment_request.net_total, 100.00)
		self.assertEqual(payment_request.hold_gst_payables, 1)

		payment_request1 = self.create_bank_payment_request(
			is_adhoc=False,
			party_type="Supplier",
			party=self.supplier.name,
			payment_request_type="Outward",
			net_total=18.00,
			reference_doctype="Purchase Invoice",
			reference_name=purchase_invoice.name,
		)

		# Insert should raise ValidationError as hold_gst_payable exceeds payment amount
		with self.assertRaises(frappe.ValidationError):
			payment_request1.insert()

	def test_validate_and_update_gst_payables_adhoc_payment_skipped(self):
		"""Test that validate_and_update_gst_payables is skipped for ad-hoc payments"""
		if "india_compliance" not in frappe.get_installed_apps():
			click.echo(
				"india_compliance not installed, skipping test_validate_and_update_gst_payables_adhoc_payment_skipped"
			)
			return

		# Enable hold_gst_payables on supplier
		frappe.db.set_value("Supplier", self.supplier.name, "hold_gst_payables", 1)

		# Create an ad-hoc payment request
		payment_request = self.create_bank_payment_request(
			is_adhoc=True,
			party_type="Supplier",
			party=self.supplier.name,
			payment_request_type="Outward",
			net_total=1000.00,
		)

		# Insert should not raise error even though hold_gst_payables is enabled
		# because ad-hoc payments skip the validation
		payment_request.insert()
		payment_request.reload()

		# Verify that the payment was created successfully
		self.assertEqual(payment_request.net_total, 1000.00)
		self.assertFalse(payment_request.reference_doctype)
		self.assertFalse(payment_request.reference_name)

	def test_validate_and_update_gst_payables_without_compliance_app(self):
		"""Test that validate_and_update_gst_payables returns early when india_compliance is not installed"""
		# Create payment request without any issue
		payment_request = self.create_bank_payment_request(
			is_adhoc=False,
			party_type="Supplier",
			party=self.supplier.name,
			payment_request_type="Outward",
			net_total=500.00,
			reference_doctype="Purchase Order",
			reference_name="PO001",
		)

		# Mock india_compliance not installed scenario
		installed_apps = frappe.get_installed_apps()
		if "india_compliance" not in installed_apps:
			# The function should return early, so no validation error should occur
			# This test passes if no error is raised
			payment_request.validate()
			self.assertTrue(True)

	def test_validate_and_update_gst_payables_with_flag_ignore(self):
		"""Test that validate_and_update_gst_payables returns early when ignore flag is set"""
		if "india_compliance" not in frappe.get_installed_apps():
			click.echo(
				"india_compliance not installed, skipping test_validate_and_update_gst_payables_with_flag_ignore"
			)
			return

		# Create a Purchase Invoice with GST
		purchase_invoice = self.make_purchase_invoice_with_gst()

		# Enable hold_gst_payables on supplier
		frappe.db.set_value("Supplier", self.supplier.name, "hold_gst_payables", 1)

		# Set the ignore flag
		frappe.flags.ignore_hold_gst_payables = True

		payment_request = self.create_bank_payment_request(
			is_adhoc=False,
			party_type="Supplier",
			party=self.supplier.name,
			payment_request_type="Outward",
			net_total=118.00,
			reference_doctype="Purchase Invoice",
			reference_name=purchase_invoice.name,
		)

		# Insert should succeed because the flag skips the validation
		payment_request.insert()
		payment_request.reload()

		self.assertEqual(payment_request.net_total, 118.00)

		# Clean up
		frappe.flags.ignore_hold_gst_payables = False

	def test_validate_and_update_gst_payables_auto_populate_hold_flag(self):
		"""Test that hold_gst_payables flag is auto-populated from supplier if not set"""
		if "india_compliance" not in frappe.get_installed_apps():
			click.echo(
				"india_compliance not installed, skipping test_validate_and_update_gst_payables_auto_populate_hold_flag"
			)
			return

		# Create a Purchase Invoice with GST
		purchase_invoice = self.make_purchase_invoice_with_gst()

		# Enable hold_gst_payables on supplier
		frappe.db.set_value("Supplier", self.supplier.name, "hold_gst_payables", 1)

		# Create payment request without explicitly setting hold_gst_payables
		payment_request = self.create_bank_payment_request(
			is_adhoc=False,
			party_type="Supplier",
			party=self.supplier.name,
			payment_request_type="Outward",
			net_total=118.00,
			reference_doctype="Purchase Invoice",
			reference_name=purchase_invoice.name,
		)

		# At this point hold_gst_payables should be False (not set yet)
		self.assertFalse(payment_request.hold_gst_payables)

		# After insert, the flag should be auto-populated from supplier
		payment_request.insert()
		payment_request.reload()

		# Verify that hold_gst_payables was auto-populated from supplier
		self.assertEqual(payment_request.hold_gst_payables, 1)

	def test_validate_and_update_gst_payables_calculates_applicable_payment_amount(
		self,
	):
		"""Test that applicable payment amount is correctly calculated based on GST"""
		if "india_compliance" not in frappe.get_installed_apps():
			click.echo(
				"india_compliance not installed, skipping test_validate_and_update_gst_payables_calculates_applicable_payment_amount"
			)
			return

		# Create a Purchase Order with GST
		purchase_order = self.make_purchase_order_with_gst()

		# Enable hold_gst_payables on supplier
		frappe.db.set_value("Supplier", self.supplier.name, "hold_gst_payables", 1)

		# Create Payment Request for the Purchase Order
		# The PO has base_grand_total = 118 (100 + 18 GST)
		payment_request = self.create_bank_payment_request(
			is_adhoc=False,
			party_type="Supplier",
			party=self.supplier.name,
			payment_request_type="Outward",
			net_total=118.00,
			reference_doctype="Purchase Order",
			reference_name=purchase_order.name,
		)

		payment_request.insert()
		payment_request.reload()

		# Expected: net_total should be 100 (excluding 18 GST)
		self.assertEqual(payment_request.net_total, 100.00)

	def test_validate_and_update_gst_payables_no_hold_gst_flag(self):
		"""Test validate_and_update_gst_payables when hold_gst_payables is not set"""
		if "india_compliance" not in frappe.get_installed_apps():
			click.echo(
				"india_compliance not installed, skipping test_validate_and_update_gst_payables_no_hold_gst_flag"
			)
			return

		# Create a Purchase Invoice with GST
		purchase_invoice = self.make_purchase_invoice_with_gst()

		# Do NOT enable hold_gst_payables on supplier (default is 0)
		frappe.db.set_value("Supplier", self.supplier.name, "hold_gst_payables", 0)

		# Create Payment Request for the Purchase Invoice
		payment_request = self.create_bank_payment_request(
			is_adhoc=False,
			party_type="Supplier",
			party=self.supplier.name,
			payment_request_type="Outward",
			net_total=118.00,
			reference_doctype="Purchase Invoice",
			reference_name=purchase_invoice.name,
		)

		# Insert should succeed without any GST payable validation
		payment_request.insert()
		payment_request.reload()

		# Expected: net_total should remain as 118.00 (no GST adjustment)
		self.assertEqual(payment_request.net_total, 118.00)
