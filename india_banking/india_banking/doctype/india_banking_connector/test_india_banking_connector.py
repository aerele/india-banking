# Copyright (c) 2026, Aerele Technologies Private Limited and Contributors
# See license.txt

from unittest import TestCase
from unittest.mock import MagicMock, PropertyMock, patch

import frappe

from india_banking.india_banking.doc_events.payment_entry import (
	on_cancel as on_payment_entry_cancel,
)
from india_banking.india_banking.doctype.india_banking_connector.india_banking_connector import (
	IndiaBankingConnector,
)

IGNORE_TEST_RECORD_DEPENDENCIES = [
	"Account",
	"Bank Account",
	"Company",
	"Cost Center",
	"DocType",
	"Letter Head",
	"Mode of Transfer",
	"Naming Series Map",
	"Payment Gateway",
	"Payment Gateway Account",
	"Payment Notification",
	"Payment Request",
	"Print Format",
	"Project",
	"Tax Withholding Category",
]


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

	def test_status_response_handles_mixed_processed_and_failed_summaries(self):
		connector = self.get_connector()
		payment_order = self.get_payment_order(
			[
				{"name": "processed-row", "payment_entry": None},
				{"name": "failed-row", "payment_entry": "PE-FAILED"},
			]
		)
		response = frappe._dict({"ok": True})
		response_details = {
			"payment_status": "PROCESSED",
			"summary_details": {
				"processed-row": {
					"status": "Processed",
					"utr_number": "UTR-001",
					"message": "Payment completed",
				},
				"failed-row": {"status": "Failed", "message": "Insufficient funds"},
			},
		}

		with (
			patch.object(
				connector, "get_response_details", return_value=response_details
			),
			patch.object(connector, "handle_failed_summary") as handle_failed_summary,
			patch("frappe.db.set_value"),
		):
			connector.verify_status_response(response, payment_order)

		handle_failed_summary.assert_called_once_with(
			payment_order, payment_order.summary[1]
		)
		self.assertEqual(connector.status_count_map["Processed"], 1)
		self.assertEqual(connector.status_count_map["Failed"], 1)

	def test_failed_payment_entry_cancellation_ignores_payment_order_link_only(self):
		payment_order = self.get_payment_order([])
		connector = self.get_connector()
		summary = frappe._dict(
			{
				"name": "summary-row",
				"payment_entry": "PE-FAILED",
				"journal_entry_account": None,
			}
		)
		payment_entry = MagicMock(docstatus=1, name="PE-FAILED")
		payment_entry.flags = frappe._dict()

		def get_value(fieldname):
			if fieldname == "ignore_linked_doctypes":
				return getattr(payment_entry, "ignore_linked_doctypes", None)
			return None

		def cancel():
			self.assertTrue(payment_entry.flags.from_bank_failure)
			payment_entry.ignore_linked_doctypes = ["GL Entry"]
			on_payment_entry_cancel(payment_entry)

		payment_entry.get.side_effect = get_value
		payment_entry.cancel.side_effect = cancel

		with (
			patch.object(
				connector, "process_bank_payment_requests"
			) as process_requests,
			patch("frappe.get_doc", return_value=payment_entry),
		):
			connector.handle_failed_summary(payment_order, summary)

		process_requests.assert_called_once_with(payment_order, summary)
		self.assertEqual(
			payment_entry.ignore_linked_doctypes, ["GL Entry", "Payment Order"]
		)
		self.assertNotIn("from_bank_failure", payment_entry.flags)
		payment_entry.cancel.assert_called_once()

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
