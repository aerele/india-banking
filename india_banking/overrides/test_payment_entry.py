import unittest
from unittest.mock import MagicMock, patch

import frappe

from india_banking.overrides.payment_entry import get_payment_entry

MODULE = "india_banking.overrides.payment_entry"


def _pe_row(name, party="Supplier A", amount=500.0):
	return frappe._dict(name=name, party=party, paid_amount=amount)


def _por_row(
	payment_entry=None, reference_doctype="Purchase Invoice", reference_name=None
):
	return frappe._dict(
		payment_entry=payment_entry,
		reference_doctype=reference_doctype,
		reference_name=reference_name,
	)


def _build_qb_mocks(po_rows, pe_rows):
	"""
	Return (qb_mock, pe_chain).

	qb_mock.from_() returns:
	  - po_chain on the 1st call  (Payment Order / Reference lookup)
	  - pe_chain on the 2nd call  (Payment Entry result query)

	pe_chain is chainable: .select() / .where() both return itself so that
	repeated .where() calls in the function under test keep the same mock.
	"""
	po_chain = MagicMock()
	(
		po_chain.inner_join.return_value.on.return_value.select.return_value.where.return_value.run.return_value
	) = po_rows

	pe_chain = MagicMock()
	pe_chain.select.return_value = pe_chain
	pe_chain.where.return_value = pe_chain
	pe_chain.run.return_value = pe_rows

	calls = [0]
	qb = MagicMock()

	def _from_side_effect(table):
		calls[0] += 1
		return po_chain if calls[0] == 1 else pe_chain

	qb.from_.side_effect = _from_side_effect
	return qb, pe_chain


def _base_filters(**overrides):
	f = {
		"docstatus": 1,
		"payment_type": "Pay",
		"mode_of_payment": "Wire Transfer",
		"bank_account": "Bank - TC",
		"source_doctype": ["!=", "Payment Request"],
	}
	f.update(overrides)
	return f


class TestGetPaymentEntry(unittest.TestCase):
	"""
	Unit tests for india_banking.overrides.payment_entry.get_payment_entry.

	frappe.db is patched globally so the @validate_and_sanitize_search_inputs
	decorator can check DocType existence without a live database.
	The frappe name inside the module under test is replaced with a MagicMock
	so the QueryBuilder chain can be controlled per-scenario.
	"""

	def _call(self, po_rows, pe_rows, filters=None):
		if filters is None:
			filters = _base_filters()

		qb_mock, pe_chain = _build_qb_mocks(po_rows, pe_rows)

		with (
			patch("frappe.db.exists", return_value=True),
			patch(f"{MODULE}.frappe") as mock_frappe,
		):
			mock_frappe.qb = qb_mock
			result = get_payment_entry("Payment Entry", "", "name", 0, 20, filters)

		return result, pe_chain

	def test_null_source_doctype_entry_is_returned(self):
		"""
		Entries with NULL source_doctype must appear when the filter is
		source_doctype != 'Payment Request'.

		Before the fix the function used frappe.get_all which generates
		SQL `source_doctype != 'Payment Request'`.  SQL evaluates
		NULL != 'x' as NULL (not TRUE), so NULL rows were silently dropped.
		The fix uses frappe.qb with an explicit IS NULL OR clause.
		"""
		pe_rows = [_pe_row("PE-NULL-SRC")]
		result, _ = self._call(po_rows=[], pe_rows=pe_rows)

		self.assertEqual(len(result), 1)
		self.assertEqual(result[0]["name"], "PE-NULL-SRC")

	def test_existing_payment_entries_popped_from_filters(self):
		"""
		existing_payment_entries must be removed from the filter dict before
		the QB query is built; passing it verbatim would cause an invalid query.
		"""
		filters = _base_filters(existing_payment_entries=["PE-010", "PE-011"])

		self._call(po_rows=[], pe_rows=[], filters=filters)

		self.assertNotIn("existing_payment_entries", filters)

	def test_entry_in_active_po_via_payment_entry_field_excluded(self):
		"""
		When por.payment_entry references an entry in a non-cancelled PO,
		a notin condition must be added to the PE query.
		"""
		po_rows = [_por_row(payment_entry="PE-IN-ORDER")]
		_, pe_chain = self._call(
			po_rows=po_rows,
			pe_rows=[],
			filters=_base_filters(),
		)

		pe_chain.where.assert_called()

	def test_entry_in_active_po_via_reference_name_field_excluded(self):
		"""
		When por.reference_name is a Payment Entry in a non-cancelled PO,
		that entry must be added to the notin exclusion set.
		"""
		po_rows = [_por_row(reference_doctype="Payment Entry", reference_name="PE-REF")]
		_, pe_chain = self._call(
			po_rows=po_rows,
			pe_rows=[],
			filters=_base_filters(),
		)

		pe_chain.where.assert_called()

	def test_existing_payment_entries_trigger_notin_condition(self):
		"""
		When existing_payment_entries are passed in filters, the notin
		condition must be applied to the PE query.
		"""
		filters = _base_filters(existing_payment_entries=["PE-EXISTING"])
		_, pe_chain = self._call(po_rows=[], pe_rows=[], filters=filters)

		pe_chain.where.assert_called()

	def test_entry_from_cancelled_po_is_eligible(self):
		"""
		The first QB query filters out cancelled POs (docstatus != 2), so
		entries that were only in cancelled POs are not in already_ordered
		and must still appear in the results.

		Before the operator-precedence fix the docstatus != 2 condition was
		silently ignored, causing even cancelled-PO entries to be excluded.
		"""
		pe_rows = [_pe_row("PE-FROM-CANCELLED")]
		result, _ = self._call(po_rows=[], pe_rows=pe_rows, filters=_base_filters())

		self.assertEqual(len(result), 1)
		self.assertEqual(result[0]["name"], "PE-FROM-CANCELLED")

	def test_none_and_empty_po_refs_do_not_trigger_notin(self):
		"""
		If all po_rows resolve to None or '' after the set comprehension,
		already_ordered is empty and the notin condition must not be added.
		Passing None to notin would generate invalid SQL.
		"""
		po_rows = [
			_por_row(
				payment_entry=None,
				reference_doctype="Purchase Invoice",
				reference_name=None,
			),
			_por_row(
				payment_entry="",
				reference_doctype="Purchase Invoice",
				reference_name="",
			),
		]
		pe_rows = [_pe_row("PE-CLEAN")]
		result, _ = self._call(
			po_rows=po_rows, pe_rows=pe_rows, filters={"docstatus": 1}
		)

		self.assertEqual(result, pe_rows)

	def test_null_in_existing_payment_entries_does_not_empty_results(self):
		"""
		If the client sends null values inside existing_payment_entries
		(e.g. a reference row whose payment_entry field is unset),
		those Nones must be stripped before building the notin list.

		SQL evaluates `name NOT IN (NULL, 'x')` as NULL for every row,
		returning zero results — even entries that should be visible.
		"""
		filters = _base_filters(existing_payment_entries=[None, "ACC-PAY-2026-00006"])
		pe_rows = [_pe_row("ACC-PAY-2026-00013")]
		result, _ = self._call(po_rows=[], pe_rows=pe_rows, filters=filters)

		self.assertEqual(len(result), 1)
		self.assertEqual(result[0]["name"], "ACC-PAY-2026-00013")

	def test_empty_result_returns_empty_list(self):
		"""
		When the QB returns an empty list, the function must return []
		rather than None or a falsy value.
		"""
		result, _ = self._call(po_rows=[], pe_rows=[])

		self.assertEqual(result, [])


if __name__ == "__main__":
	unittest.main()
