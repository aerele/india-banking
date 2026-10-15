# Copyright (c) 2026, Aerele Technologies Private Limited and Contributors
# See license.txt

from unittest import TestCase
from unittest.mock import MagicMock, patch

import frappe

from india_banking.overrides.payment_order import CustomPaymentOrder


class TestCustomPaymentOrder(TestCase):
	def get_payment_order(self):
		payment_order = frappe._dict(
			{
				"payment_order_type": "Payment Request",
				"references": [
					frappe._dict(payment_request="PR-CANCELLED"),
					frappe._dict(payment_request="PR-SUBMITTED"),
				],
			}
		)
		payment_order.db_set = MagicMock()
		return payment_order

	def test_cancel_does_not_reopen_cancelled_payment_requests(self):
		payment_order = self.get_payment_order()

		with (
			patch("frappe.get_all", return_value=["PR-CANCELLED"]) as get_all,
			patch("frappe.db.set_value") as set_value,
		):
			CustomPaymentOrder.update_payment_status(payment_order, cancel=True)

		get_all.assert_called_once_with(
			"Payment Request",
			filters={
				"name": ["in", ["PR-CANCELLED", "PR-SUBMITTED"]],
				"docstatus": 2,
			},
			pluck="name",
		)
		set_value.assert_called_once_with(
			"Payment Request", "PR-SUBMITTED", "status", "Initiated"
		)

	def test_submit_updates_all_payment_requests(self):
		payment_order = self.get_payment_order()

		with (
			patch("frappe.get_all") as get_all,
			patch("frappe.db.set_value") as set_value,
		):
			CustomPaymentOrder.update_payment_status(payment_order)

		get_all.assert_not_called()
		self.assertEqual(set_value.call_count, 2)
		set_value.assert_any_call(
			"Payment Request", "PR-CANCELLED", "status", "Payment Ordered"
		)
		set_value.assert_any_call(
			"Payment Request", "PR-SUBMITTED", "status", "Payment Ordered"
		)
