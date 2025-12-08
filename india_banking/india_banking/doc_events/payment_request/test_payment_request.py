import frappe
from frappe.tests.utils import FrappeTestCase

from india_banking.setup.utils import create_company, create_supplier


class TestPaymentRequest(FrappeTestCase):
	def setUp(self):
		from frappe import make_property_setter

		self.company = create_company("IB Company")
		self.supplier = create_supplier("IB Supplier")

		make_property_setter(
			{
				"doctype_or_field": "DocField",
				"doctype": "Payment Request",
				"fieldname": "naming_series",
				"property": "options",
				"property_type": "Select",
				"value": "ACC-PRQ-.YYYY.-\nTEST-",
			}
		)

		super().setUp()

	def tearDown(self):
		super().tearDown()
		frappe.db.rollback()

	def test_payment_request_without_naming_series_map(self):
		# Crate Payment Request without naming series map settings
		payment_request = frappe.get_doc(
			{
				"is_adhoc": 1,
				"doctype": "Payment Request",
				"naming_series": "ACC-PRQ-.YYYY.",
				"company": self.company.name,
				"party_type": "Supplier",
				"party": self.supplier.name,
				"payment_request_type": "Outward",
				"net_total": 1000,
				"amount": 1000,
			}
		)
		payment_request.save()
		self.assertIn("ACC-PRQ", payment_request.name)

	def test_payment_request_with_naming_series_map(self):
		# Update naming series Map
		frappe.get_doc(
			{
				"doctype": "Naming Series Map",
				"parenttype": "India Banking Settings",
				"parent": "India Banking Settings",
				"parentfield": "doctype_naming_series",
				"company": self.company,
				"doctype_name": "Payment Request",
				"series": "TEST-",
			}
		).insert(ignore_permissions=True)

		# Create Payment Request with naming series map settings
		payment_request = frappe.get_doc(
			{
				"is_adhoc": 1,
				"doctype": "Payment Request",
				"naming_series": "ACC-PRQ-.YYYY.",
				"company": self.company.name,
				"party_type": "Supplier",
				"party": self.supplier.name,
				"payment_request_type": "Outward",
				"net_total": 1000,
				"amount": 1000,
			}
		)
		payment_request.save()
		self.assertIn("TEST-", payment_request.name)
