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
		return frappe.get_doc(
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
		with self.assertRaises(frappe.ValidationError):
			payment_request.insert()

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
