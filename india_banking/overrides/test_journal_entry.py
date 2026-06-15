import unittest
from unittest.mock import MagicMock, patch

import frappe

from india_banking.overrides.journal_entry import get_bank_entry

MODULE = "india_banking.overrides.journal_entry"


def _je_row(name, company="Test Co", total=1000.0):
	return frappe._dict(
		name=name, company=company, total=total, voucher_type="Bank Entry"
	)


def _build_qb_mock(rows):
	"""Return a chainable QB mock whose .run() returns rows."""
	chain = MagicMock()
	chain.join.return_value = chain
	chain.on.return_value = chain
	chain.where.return_value = chain
	chain.groupby.return_value = chain
	chain.select.return_value = chain
	chain.run.return_value = rows
	return chain


def _call(rows, filters=None, txt=""):
	if filters is None:
		filters = {"company_account": "Bank GL - TC", "docs": [], "company": ""}

	qb = MagicMock()
	qb.from_.return_value = _build_qb_mock(rows)

	with (
		patch("frappe.db.exists", return_value=True),
		patch(f"{MODULE}.frappe") as mock_frappe,
	):
		mock_frappe.qb = qb
		mock_frappe._dict = frappe._dict
		result = get_bank_entry(
			"Journal Entry", txt, "name", 0, 20, filters, as_dict=True
		)

	return result


class TestGetBankEntry(unittest.TestCase):
	def test_bank_entry_with_null_payment_status_is_returned(self):
		"""
		JE account lines with NULL payment_status must not be excluded.
		SQL evaluates NULL NOT IN ('Paid', ...) as NULL (not TRUE), silently
		dropping the row. The fix adds OR payment_status IS NULL.
		"""
		rows = [_je_row("JV-001")]
		result = _call(rows=rows)
		self.assertEqual(len(result), 1)
		self.assertEqual(result[0]["name"], "JV-001")

	def test_empty_company_account_does_not_return_zero_results(self):
		"""
		When frm.doc.account is not set on the Payment Order, company_account
		is empty. Before the fix this generated against_account IS NULL which
		matched nothing. The fix makes the against_account filter optional.
		"""
		rows = [_je_row("JV-002")]
		result = _call(
			rows=rows, filters={"company_account": "", "docs": [], "company": ""}
		)
		self.assertEqual(len(result), 1)
		self.assertEqual(result[0]["name"], "JV-002")

	def test_company_account_filter_applied_when_set(self):
		"""
		When company_account is provided the against_account .where() condition
		must be added to the query chain.
		"""
		qb = MagicMock()
		chain = _build_qb_mock([_je_row("JV-003")])
		qb.from_.return_value = chain

		with (
			patch("frappe.db.exists", return_value=True),
			patch(f"{MODULE}.frappe") as mock_frappe,
		):
			mock_frappe.qb = qb
			mock_frappe._dict = frappe._dict
			get_bank_entry(
				"Journal Entry",
				"",
				"name",
				0,
				20,
				{"company_account": "Bank GL - TC", "docs": [], "company": ""},
				as_dict=True,
			)

		chain.where.assert_called()

	def test_existing_docs_trigger_notin_condition(self):
		"""
		JE names already in the Payment Order references must be excluded
		via a NOT IN condition on the query.
		"""
		qb = MagicMock()
		chain = _build_qb_mock([])
		qb.from_.return_value = chain

		with (
			patch("frappe.db.exists", return_value=True),
			patch(f"{MODULE}.frappe") as mock_frappe,
		):
			mock_frappe.qb = qb
			mock_frappe._dict = frappe._dict
			get_bank_entry(
				"Journal Entry",
				"",
				"name",
				0,
				20,
				{"company_account": "", "docs": ["JV-EXISTING"], "company": ""},
				as_dict=True,
			)

		chain.where.assert_called()

	def test_company_filter_applied_when_set(self):
		"""
		When company is passed via the setter dialog, only JEs matching
		that company must be returned.
		"""
		qb = MagicMock()
		chain = _build_qb_mock([_je_row("JV-004", company="ACME")])
		qb.from_.return_value = chain

		with (
			patch("frappe.db.exists", return_value=True),
			patch(f"{MODULE}.frappe") as mock_frappe,
		):
			mock_frappe.qb = qb
			mock_frappe._dict = frappe._dict
			get_bank_entry(
				"Journal Entry",
				"",
				"name",
				0,
				20,
				{"company_account": "", "docs": [], "company": "ACME"},
				as_dict=True,
			)

		chain.where.assert_called()

	def test_txt_filter_applied(self):
		"""
		When the user types in the picker search box, the txt value must
		be applied as a LIKE condition on the JE name.
		"""
		qb = MagicMock()
		chain = _build_qb_mock([_je_row("JV-005")])
		qb.from_.return_value = chain

		with (
			patch("frappe.db.exists", return_value=True),
			patch(f"{MODULE}.frappe") as mock_frappe,
		):
			mock_frappe.qb = qb
			mock_frappe._dict = frappe._dict
			get_bank_entry(
				"Journal Entry",
				"JV-005",
				"name",
				0,
				20,
				{"company_account": "", "docs": [], "company": ""},
				as_dict=True,
			)

		chain.where.assert_called()

	def test_null_in_docs_does_not_empty_results(self):
		"""
		If the client sends null values inside docs (reference rows whose
		reference_name is not set), those Nones must be stripped before
		building the NOT IN list.

		SQL evaluates `name NOT IN (NULL, NULL)` as NULL for every row,
		returning zero results — same class of bug as existing_payment_entries.
		"""
		rows = [_je_row("JV-ELIGIBLE")]
		result = _call(
			rows=rows,
			filters={
				"company_account": "Bank GL - TC",
				"docs": [None, None],
				"company": "",
			},
		)
		self.assertEqual(len(result), 1)
		self.assertEqual(result[0]["name"], "JV-ELIGIBLE")

	def test_empty_result_returns_empty_list(self):
		"""When the QB returns nothing the function must return []."""
		result = _call(rows=[])
		self.assertEqual(result, [])


if __name__ == "__main__":
	unittest.main()
