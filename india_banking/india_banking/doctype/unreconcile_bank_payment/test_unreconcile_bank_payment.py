# Copyright (c) 2026, Aerele Technologies Private Limited and Contributors
# See license.txt

from unittest import TestCase
from unittest.mock import MagicMock, patch

import frappe

from india_banking.india_banking.doctype.unreconcile_bank_payment.unreconcile_bank_payment import (
	UnreconcileBankPayment,
	is_unlink_allocation_enabled,
)

IGNORE_TEST_RECORD_DEPENDENCIES = [
	"Account",
	"Bank",
	"Bank Account",
	"Bank Payment Allocation",
	"Company",
	"Cost Center",
	"DocType",
	"Letter Head",
	"Mode of Transfer",
	"Payment Gateway",
	"Payment Gateway Account",
	"Payment Request",
	"Print Format",
	"Project",
	"Tax Withholding Category",
	"Unreconcile Bank Payment",
]


class TestUnreconcileBankPayment(TestCase):
	def get_unreconcile_doc(self):
		doc = frappe.get_doc(
			{
				"doctype": "Unreconcile Bank Payment",
				"company": "Test Company",
				"voucher_type": "Payment Order",
				"voucher_no": "PO-001",
			}
		)
		doc.append(
			"allocations",
			{
				"party_type": "Supplier",
				"party": "SUP-001",
				"reference_type": "Purchase Invoice",
				"reference_name": "PINV-001",
				"amount": 100,
				"payment_request": "PR-001",
			},
		)
		return doc

	def test_unlink_button_setting_uses_payment_order_connector(self):
		for enabled in (0, 1):
			with self.subTest(enabled=enabled):
				payment_order = MagicMock(company_bank_account="Test Bank Account")
				with (
					patch("frappe.get_doc", return_value=payment_order),
					patch("frappe.db.get_value", return_value=enabled),
				):
					result = is_unlink_allocation_enabled("PO-001")

				payment_order.check_permission.assert_called_once_with("read")
				self.assertEqual(result, bool(enabled))

	def test_manual_unlink_settings_are_independent(self):
		for unreconcile_entry, cancel_request in (
			(0, 0),
			(0, 1),
			(1, 0),
			(1, 1),
		):
			with self.subTest(
				unreconcile_entry=unreconcile_entry,
				cancel_request=cancel_request,
			):
				doc = self.get_unreconcile_doc()
				payment_request = MagicMock()

				def get_value(doctype, name_or_filters, fieldname=None, **kwargs):
					if doctype == "Payment Order":
						return "Test Bank Account"
					if doctype == "India Banking Connector":
						return frappe._dict(
							{
								"unreconcile_payment_entries_on_unlink_allocation": unreconcile_entry,
								"cancel_payment_requests_on_unlink_allocation": cancel_request,
							}
						)
					if doctype == "Payment Entry":
						return "PE-001"

				def get_doc(doctype, name):
					if doctype == "Payment Request":
						return payment_request
					return MagicMock()

				with (
					patch("frappe.db.get_value", side_effect=get_value) as db_get_value,
					patch("frappe.db.delete") as db_delete,
					patch("frappe.get_doc", side_effect=get_doc),
					patch("frappe.has_permission", return_value=True),
					patch("frappe.utils.fmt_money", return_value="100.00"),
					patch(
						"india_banking.india_banking.doctype.unreconcile_bank_payment.unreconcile_bank_payment.create_unreconcile_doc_for_selection"
					) as create_unreconcile,
				):
					if unreconcile_entry:
						doc.unlink_allocations()
					else:
						with self.assertRaises(frappe.ValidationError):
							doc.unlink_allocations()

				self.assertEqual(db_delete.call_count, unreconcile_entry)
				payment_entry_lookups = [
					call
					for call in db_get_value.call_args_list
					if call.args and call.args[0] == "Payment Entry"
				]
				self.assertEqual(len(payment_entry_lookups), unreconcile_entry)
				self.assertEqual(create_unreconcile.call_count, unreconcile_entry)
				self.assertEqual(
					payment_request.cancel.call_count,
					unreconcile_entry and cancel_request,
				)

	def test_payment_request_can_be_cancelled_without_payment_entry(self):
		doc = self.get_unreconcile_doc()
		payment_request = MagicMock()

		def get_value(doctype, name_or_filters, fieldname=None, **kwargs):
			if doctype == "Payment Order":
				return "Test Bank Account"
			if doctype == "India Banking Connector":
				return frappe._dict(
					{
						"unreconcile_payment_entries_on_unlink_allocation": 1,
						"cancel_payment_requests_on_unlink_allocation": 1,
					}
				)
			if doctype == "Payment Entry":
				return None

		with (
			patch("frappe.db.get_value", side_effect=get_value),
			patch("frappe.db.delete"),
			patch("frappe.get_doc", side_effect=[payment_request, MagicMock()]),
			patch("frappe.has_permission", return_value=True),
			patch("frappe.utils.fmt_money", return_value="100.00"),
			patch(
				"india_banking.india_banking.doctype.unreconcile_bank_payment.unreconcile_bank_payment.create_unreconcile_doc_for_selection"
			) as create_unreconcile,
		):
			doc.unlink_allocations()

		create_unreconcile.assert_not_called()
		payment_request.cancel.assert_called_once()

	def test_from_payment_order_flag_is_removed_after_success(self):
		doc = self.get_unreconcile_doc()
		frappe.flags.pop("from_payment_order", None)

		with patch.object(doc, "unlink_allocations"):
			UnreconcileBankPayment.on_submit(doc)

		self.assertNotIn("from_payment_order", frappe.flags)

	def test_from_payment_order_flag_is_restored_after_failure(self):
		doc = self.get_unreconcile_doc()
		frappe.flags.from_payment_order = "existing-value"

		with (
			patch.object(doc, "unlink_allocations", side_effect=RuntimeError("failed")),
			self.assertRaises(RuntimeError),
		):
			UnreconcileBankPayment.on_submit(doc)

		self.assertEqual(frappe.flags.from_payment_order, "existing-value")
