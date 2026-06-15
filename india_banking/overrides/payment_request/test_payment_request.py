from unittest import TestCase
from unittest.mock import patch

import frappe

from india_banking.overrides.payment_request.payment_request import (
	BankPaymentRequest,
	get_party_account,
)


class TestPaymentRequestOverrides(TestCase):
	def get_payment_request(self, **kwargs):
		doc = frappe._dict(
			{
				"doctype": "Payment Request",
				"name": "TEST-PAYMENT-REQUEST",
				"company": "Test Company",
				"party_type": "Supplier",
				"party": "Test Supplier",
				"payment_request_type": "Outward",
				"net_total": 1000,
				"grand_total": 1000,
				"transaction_date": None,
				"bank_account": None,
				"mode_of_payment": None,
				"reference_doctype": "Purchase Invoice",
				"reference_name": "TEST-PINV",
				"currency": "INR",
				"docstatus": 0,
				"hold_gst_payables": 0,
				"cost_center": None,
				"project": None,
				"get": lambda key, default=None: doc[key] if key in doc else default,
			}
		)
		doc.update(kwargs)
		return doc

	def test_set_default_value_sets_date_bank_account_and_mode(self):
		payment_request = self.get_payment_request(grand_total=1500, net_total=None)

		with patch("frappe.get_value", return_value="Test Bank Account"):
			BankPaymentRequest.set_default_value(payment_request)

		self.assertEqual(payment_request.net_total, 1500)
		self.assertEqual(payment_request.transaction_date, frappe.utils.getdate())
		self.assertEqual(payment_request.bank_account, "Test Bank Account")
		self.assertEqual(payment_request.mode_of_payment, "Wire Transfer")

	def test_validate_and_update_gst_payables_skips_without_india_compliance(self):
		payment_request = self.get_payment_request(hold_gst_payables=1)

		with (
			patch("frappe.get_installed_apps", return_value=["frappe", "erpnext"]),
			patch("frappe.get_doc") as get_doc,
		):
			BankPaymentRequest.validate_and_update_gst_payables(
				payment_request, update=True
			)

		get_doc.assert_not_called()

	def test_get_gst_payable_amount_returns_zero_without_supported_reference(self):
		payment_request = self.get_payment_request(
			reference_doctype=None,
			reference_name=None,
		)

		gst_amount = BankPaymentRequest.get_gst_payable_amount(payment_request)

		self.assertEqual(gst_amount, 0)

	def test_get_gst_payable_amount_sums_reference_item_taxes(self):
		payment_request = self.get_payment_request()

		with patch(
			"frappe.db.get_all",
			return_value=[
				frappe._dict(
					{
						"total_igst": 10,
						"total_cgst": 4,
						"total_sgst": 4,
					}
				)
			],
		):
			gst_amount = BankPaymentRequest.get_gst_payable_amount(payment_request)

		self.assertEqual(gst_amount, 18)

	def test_validate_bank_account_requires_default_bank_account(self):
		payment_request = self.get_payment_request(bank_account=None)

		with patch(
			"india_banking.overrides.payment_request.payment_request.get_party_bank_account",
			return_value=None,
		):
			with self.assertRaises(frappe.ValidationError):
				BankPaymentRequest.validate_bank_account(payment_request)

	def test_validate_bank_account_rejects_currency_mismatch(self):
		payment_request = self.get_payment_request(bank_account="Test Bank Account")
		bank_account = frappe._dict(
			{
				"name": "Test Bank Account",
				"currency": "USD",
				"party_type": "Supplier",
				"party": "Test Supplier",
				"workflow_state": "Approved",
			}
		)

		with (
			patch(
				"india_banking.overrides.payment_request.payment_request.get_party_bank_account",
				return_value="Test Bank Account",
			),
			patch("frappe.get_doc", return_value=bank_account),
			patch("frappe.db.get_single_value", return_value=0),
		):
			with self.assertRaises(frappe.ValidationError):
				BankPaymentRequest.validate_bank_account(payment_request)

	def test_get_party_account_uses_purchase_invoice_credit_to(self):
		source = self.get_payment_request(reference_doctype="Purchase Invoice")

		with patch("frappe.db.get_value", return_value="Creditors - TC"):
			account = get_party_account(source)

		self.assertEqual(account, "Creditors - TC")

	def test_get_party_account_uses_party_account_for_other_references(self):
		source = self.get_payment_request(reference_doctype="Purchase Order")

		with patch(
			"india_banking.overrides.payment_request.payment_request._get_party_account",
			return_value="Creditors - TC",
		):
			account = get_party_account(source)

		self.assertEqual(account, "Creditors - TC")
