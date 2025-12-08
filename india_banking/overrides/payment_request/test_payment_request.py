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

	def test_default_value_in_payment_request(self):
		"""Test to verify default value in Payment Request document"""
		# Create a new Payment Request document
		payment_request = frappe.get_doc(
			{
				"is_adhoc": 1,
				"doctype": "Payment Request",
				"company": self.company.name,
				"party_type": "Supplier",
				"party": self.supplier.name,
				"payment_request_type": "Outward",
				"net_total": 1000,
			}
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
