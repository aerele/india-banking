# Copyright (c) 2026, Aerele Technologies Private Limited and Contributors
# See license.txt

from unittest import TestCase
from unittest.mock import PropertyMock, patch

import frappe

from india_banking.india_banking.doctype.india_banking_connector.india_banking_connector import (
	IndiaBankingConnector,
)


class TestIndiaBankingConnector(TestCase):
	def get_connector(self):
		return frappe.get_doc(
			{
				"doctype": "India Banking Connector",
				"bank_account": "Test Bank Account",
				"bulk_transaction": 0,
				"url": "https://bank.example.test",
			}
		)

	def get_payment_order(self, summaries):
		return frappe._dict(
			{
				"doctype": "Payment Order",
				"name": "TEST-PAYMENT-ORDER",
				"company_bank_account": "Test Bank Account",
				"summary": [frappe._dict(summary) for summary in summaries],
				"reload": lambda: None,
			}
		)

	def test_processed_payment_retry_ignores_empty_payment_date(self):
		connector = self.get_connector()
		payment_order = self.get_payment_order(
			[
				{
					"name": "pending-row",
					"payment_status": "Pending",
					"payment_date": None,
				},
				{
					"name": "processed-row",
					"payment_status": "Processed",
					"payment_date": None,
				},
			]
		)

		with (
			patch.object(connector, "check_user_permission"),
			patch.object(connector, "make_single_request") as make_single_request,
			patch("frappe.db.get_value", return_value=3),
		):
			connector.make_post_request(
				payment_order,
				action="get_payment_status",
				check_processed_payments=True,
			)

		make_single_request.assert_called_once_with(
			payment_order, payment_order.summary[0]
		)

	def test_single_processed_row_with_failures_marks_partially_approved(self):
		connector = self.get_connector()
		payment_order = self.get_payment_order(
			[
				{"payment_status": "Processed"},
				{"payment_status": "Failed"},
			]
		)

		with patch("frappe.db.set_value") as set_value:
			IndiaBankingConnector.update_payment_status(connector, payment_order)

		set_value.assert_called_once_with(
			"Payment Order",
			payment_order.name,
			"status",
			"Partially Approved",
		)

	def test_get_bank_statement_uses_request_timeout(self):
		connector = self.get_connector()
		bank_account = frappe._dict(
			{
				"name": "Test Bank Account",
				"bank": "Test Bank",
				"bank_account_no": "1234567890",
			}
		)

		response = frappe._dict({"status_code": 500})

		with (
			patch.object(
				type(connector), "headers", new_callable=PropertyMock, return_value={}
			),
			patch(
				"india_banking.india_banking.doctype.india_banking_connector.india_banking_connector.request.post",
				return_value=response,
			) as post,
			patch(
				"india_banking.india_banking.doctype.india_banking_connector.india_banking_connector.create_api_log"
			),
		):
			connector.get_bank_statement(bank_account)

		self.assertEqual(post.call_args.kwargs["timeout"], 100)
