import frappe
from frappe.tests.utils import FrappeTestCase


class TestBank(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_restrict_deletion_of_standard_banks(self):
		"""Test that standard banks cannot be deleted."""
		# Create a standard bank
		bank = frappe.get_doc(
			{"doctype": "Bank", "bank_name": "Standard Bank", "is_standard": 1}
		)
		bank.insert()

		# Attempt to delete the standard bank
		with self.assertRaises(frappe.ValidationError) as error:
			bank.delete()

		self.assertIn("Standard Bank cannot be deleted", str(error.exception))

		# Verify that the bank still exists
		self.assertTrue(frappe.db.exists("Bank", bank.name))
