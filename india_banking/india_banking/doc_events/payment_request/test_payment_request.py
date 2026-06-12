from unittest import TestCase
from unittest.mock import patch

import frappe

from india_banking.india_banking.doc_events.payment_request.payment_request import (
	autoname,
	is_valid_invoice,
)


class TestPaymentRequest(TestCase):
	def get_payment_request(self, **kwargs):
		doc = frappe._dict(
			{
				"doctype": "Payment Request",
				"company": "Test Company",
				"payment_request_type": "Outward",
				"naming_series": "ACC-PRQ-.YYYY.-",
			}
		)
		doc.update(kwargs)
		return doc

	def test_payment_request_without_naming_series_map(self):
		payment_request = self.get_payment_request()

		with patch(
			"india_banking.utils.get_bank_payment_naming_series", return_value=None
		):
			autoname(payment_request)

		self.assertEqual(payment_request.naming_series, "ACC-PRQ-.YYYY.-")

	def test_payment_request_with_naming_series_map(self):
		payment_request = self.get_payment_request()

		with patch(
			"india_banking.utils.get_bank_payment_naming_series",
			return_value="TEST-",
		):
			autoname(payment_request)

		self.assertEqual(payment_request.naming_series, "TEST-")

	def test_payment_request_inward_does_not_use_naming_series_map(self):
		payment_request = self.get_payment_request(payment_request_type="Inward")

		with patch("india_banking.utils.get_bank_payment_naming_series") as get_series:
			autoname(payment_request)

		get_series.assert_not_called()
		self.assertEqual(payment_request.naming_series, "ACC-PRQ-.YYYY.-")

	def test_is_valid_invoice_uses_v16_payment_request_amount_api(self):
		invoice = frappe._dict({"outstanding_amount": 1000})

		with patch(
			"india_banking.india_banking.doc_events.payment_request.payment_request.get_existing_payment_request_amount",
			return_value=400,
		) as get_existing_payment_request_amount:
			self.assertTrue(is_valid_invoice(invoice))

		get_existing_payment_request_amount.assert_called_once_with(invoice)

	def test_is_valid_invoice_rejects_fully_requested_invoice(self):
		invoice = frappe._dict({"outstanding_amount": 1000})

		with patch(
			"india_banking.india_banking.doc_events.payment_request.payment_request.get_existing_payment_request_amount",
			return_value=1000,
		):
			self.assertFalse(is_valid_invoice(invoice))
