import frappe
from frappe.tests.utils import FrappeTestCase, change_settings

from india_banking.setup.utils import (
	create_bank_account,
	create_company,
	create_supplier,
)


class TestBankAccount(FrappeTestCase):
	def setUp(self):
		super().setUp()
		self.company = create_company("IB Company")

	def tearDown(self):
		frappe.db.rollback()

	def test_validate_bank_acc_details(self):
		# Create Bank Account with valid details
		bank_account = create_bank_account(
			bank_name="HDFC Bank",
			account_no="9876543210",
			ifsc_code="HDFC0005943",
		)

		# Validate Bank Account details
		self.assertEqual(bank_account.bank, "HDFC Bank")
		self.assertEqual(bank_account.branch_code, "HDFC0005943")
		self.assertEqual(bank_account.bank_account_no, "9876543210")

	def test_invalid_ifsc_code(self):
		# Create Bank Account with valid details
		bank_account = create_bank_account(
			bank_name="HDFC Bank",
			account_no="9876543210",
			ifsc_code="HDFC0005943",
		)

		# Test with invalid IFSC code
		bank_account.branch_code = "INVALIDIFSC"
		with self.assertRaises(frappe.ValidationError) as error:
			bank_account.save()

		self.assertIn("IFSC/Branch Code is not valid", str(error.exception))

	def test_party_transaction_currency(self):
		supplier = create_supplier("IB Supplier", default_currency="INR")
		# Create Bank Account with specific currency
		bank_account = create_bank_account(
			bank_name="HDFC Bank",
			account_no="1234567890",
			ifsc_code="SBIN0005943",
			party_type="Supplier",
			party=supplier.name,
			currency="USD",
		)

		# Validate Bank Account currency
		self.assertEqual(bank_account.currency, "INR")

	def test_strip_whitespace_in_account_details(self):
		# Create Bank Account with whitespace in account number
		bank_account = create_bank_account(
			bank_name="ICICI Bank",
			account_no="1234567890",
			branch_code="ICIC0001234",
		)

		# Add whitespace to fields
		bank_account.bank_account_no = "  1234567890  "
		bank_account.branch_code = "  ICIC0001234  "
		bank_account.account_name = "  Test Account  "
		bank_account.mobile_number = "  9876543210  "
		bank_account.email = " test1@ib.in"

		# Save the bank account to trigger validation
		bank_account.save()
		bank_account.reload()

		# Validate that special characters are removed
		self.assertEqual(bank_account.bank_account_no, "1234567890")
		self.assertEqual(bank_account.branch_code, "ICIC0001234")
		self.assertEqual(bank_account.mobile_number, "9876543210")
		self.assertEqual(bank_account.email, "test1@ib.in")

	def test_special_characters_in_account_details(self):
		# Create Bank Account with special characters in account number
		bank_account = create_bank_account(
			bank_name="Axis Bank",
			account_no="1234567890",
			branch_code="UTIB0001234",
		)

		# Validate special characters in bank account no
		bank_account.reload()
		bank_account.bank_account_no = "1234-5678/90"
		with self.assertRaises(frappe.ValidationError) as error:
			bank_account.save()
		self.assertIn(
			"Bank Account No contains invalid characters", str(error.exception)
		)

		# Validate special characters in account name
		bank_account.reload()
		bank_account.account_name = "Test@Account!"
		with self.assertRaises(frappe.ValidationError) as error:
			bank_account.save()
		self.assertIn("Account Name contains invalid characters", str(error.exception))

		# Create New Bank for testing special characters in bank name
		bank_account.reload()
		bank = frappe.get_doc({"doctype": "Bank", "bank_name": "Axis Bank Ltd."})

		# Validate special characters in bank name
		bank_account.reload()
		bank_account.bank = bank.name
		with self.assertRaises(frappe.ValidationError) as error:
			bank_account.save()
		self.assertIn("Bank contains invalid characters", str(error.exception))

	@change_settings("India Banking Settings", {"enable_unique_account_no": 1})
	def test_unique_bank_account_with_disable(self):
		# Create Bank Account with valid details
		bank_account = create_bank_account(
			bank_name="HDFC Bank",
			account_no="9876543210",
			account_name="Savings Account",
			ifsc_code="HDFC0005943",
		)

		# Validate Bank Account details
		self.assertEqual(bank_account.bank, "HDFC Bank")
		self.assertEqual(bank_account.branch_code, "HDFC0005943")
		self.assertEqual(bank_account.bank_account_no, "9876543210")

		# New Account with same details should raise Validation Error
		duplicate_bank_account = create_bank_account(
			bank_name="HDFC Bank",
			account_no="9876543210",
			ifsc_code="HDFC0005943",
			do_not_save=1,
		)

		with self.assertRaises(frappe.ValidationError) as error:
			duplicate_bank_account.save()

		self.assertIn("Bank Account Number must be unique", str(error.exception))

		# Disable Bank Account 1
		bank_account.disabled = 1
		bank_account.save()

		# Now saving duplicate account should pass as original is disabled
		duplicate_bank_account.save()
		self.assertEqual(duplicate_bank_account.bank_account_no, "9876543210")

	@change_settings("India Banking Settings", {"enable_unique_account_no": 1})
	def test_unique_bank_account(self):
		# Create Bank Account
		bank_account1 = create_bank_account(
			bank_name="Kotak Mahindra Bank",
			account_no="1122334455",
			account_name="Primary Account",
			ifsc_code="KKBK0001234",
			do_not_save=True,
		)
		bank_account1.save()

		# Attempt to create another Bank Account with the same details
		bank_account2 = create_bank_account(
			bank_name="HDFC Bank",
			account_no="1122334455",
			ifsc_code="HDFC0001234",
			do_not_save=1,
		)

		with self.assertRaises(frappe.ValidationError) as error:
			bank_account2.save()

		self.assertIn(
			"Bank Account Number must be unique",
			str(error.exception),
		)

	@change_settings("India Banking Settings", {"enable_unique_account_no": 0})
	def test_bank_account_without_unique_validation(self):
		# Create Bank Account
		bank_account1 = create_bank_account(
			bank_name="Kotak Mahindra Bank",
			account_no="5566778899",
			account_name="Primary Account",
			ifsc_code="KKBK0001234",
			do_not_save=True,
		)
		bank_account1.save()

		# Create another Bank Account with the same details
		bank_account2 = create_bank_account(
			bank_name="HDFC Bank",
			account_no="5566778899",
			ifsc_code="HDFC0001234",
			do_not_save=1,
		)

		# Save should succeed without raising an error
		bank_account2.save()
		self.assertEqual(bank_account2.bank_account_no, "5566778899")
