import unittest
from unittest.mock import MagicMock, patch

from india_banking.india_banking.doc_events.payment_order import make_payment_entries

MODULE = "india_banking.india_banking.doc_events.payment_order"


def _make_reference(
	name, ref_doctype="Purchase Invoice", ref_name="INV-001", amount=200.0, pr="PR-001"
):
	ref = MagicMock()
	ref.name = name
	ref.reference_doctype = ref_doctype
	ref.reference_name = ref_name
	ref.amount = amount
	ref.payment_request = pr
	return ref


def _make_summary_row(sr_names, amount=200.0, row_name="POS-ROW-001"):
	row = MagicMock()
	row.summary_references = str(sr_names)
	row.amount = amount
	row.party_type = "Supplier"
	row.party = "Test Supplier"
	row.bank_account = "BANK-ACC-001"
	row.account = "Creditors - TC"
	row.cost_center = None
	row.project = None
	row.name = row_name
	row.get = lambda k, d=None: getattr(row, k, d)
	return row


def _split_rows(term_name, invoice_portion):
	return [
		{
			"payment_term": term_name,
			"invoice_portion": invoice_portion,
			"due_date": "2026-06-30",
		}
	]


def _build_pe_mock():
	pe = MagicMock()
	pe.naming_series = "ACC-PAY-.YYYY.-"
	pe.references = []
	pe.append = lambda field, row_dict: pe.references.append(row_dict)
	return pe


def _setup_qb_run(mock_frappe, return_value=((0,),)):
	"""Configure the QueryBuilder chain so .run()[0][0] returns a predictable value."""
	mock_frappe.qb.from_.return_value.select.return_value.where.return_value.run.return_value = return_value


class TestMakePaymentEntries(unittest.TestCase):
	"""
	All tests patch the `frappe` name inside `payment_order` with a plain
	MagicMock, avoiding LocalProxy / unbound-context failures.
	"""

	# ------------------------------------------------------------------
	# Bug 1: total_amount must equal to_be_pay, not the full grand_total
	# ------------------------------------------------------------------
	@patch(f"{MODULE}.group_by_invoices")
	@patch(f"{MODULE}.get_bank_payment_naming_series", return_value=None)
	@patch(f"{MODULE}.get_split_invoice_rows")
	@patch(f"{MODULE}.get_accounting_dimensions", return_value=[])
	@patch(f"{MODULE}.nowdate", return_value="2026-06-12")
	@patch(f"{MODULE}.DocType")
	@patch(f"{MODULE}.frappe")
	def test_total_amount_equals_to_be_pay_not_grand_total(
		self, mock_frappe, _doctype, _nowdate, _dims, mock_split, _naming, _group
	):
		grand_total = 400.0
		invoice_portion = 50
		term_name = "50% Advance"
		reference = _make_reference("SR-001", amount=200.0)
		summary_row = _make_summary_row(["SR-001"], amount=200.0)
		pe = _build_pe_mock()

		po_doc = MagicMock(summary=[summary_row])
		po_doc.name = "PO-001"
		po_doc.company = "Test Company"
		po_doc.company_bank_account = "CB-001"
		po_doc.account = "Bank - TC"
		po_doc.payment_order_type = "Purchase Invoice"
		po_doc.posting_date = "2026-06-12"

		mock_frappe.get_single.return_value = MagicMock(
			use_payment_order_date_as_payment_entry_date=False
		)
		mock_frappe.new_doc.return_value = pe

		def get_doc_side_effect(doctype, *args):
			if doctype == "Payment Order":
				return po_doc
			if doctype == "Payment Order Reference":
				return reference
			inv = MagicMock()
			inv.grand_total = grand_total
			return inv

		mock_frappe.get_doc.side_effect = get_doc_side_effect

		def db_get_value(doctype, name, field, *a, **kw):
			mapping = {
				("Payment Request", "payment_term"): None,
				("Payment Request", "net_total"): 200.0,
				(reference.reference_doctype, "payment_terms_template"): "Standard",
				(
					"Payment Terms Template",
					"allocate_payment_based_on_payment_terms",
				): True,
				("Payment Term", "invoice_portion"): invoice_portion,
				(reference.reference_doctype, "grand_total"): grand_total,
				("Letter Head", "name"): "Default",
			}
			return mapping.get((doctype, field))

		mock_frappe.db.get_value.side_effect = db_get_value
		_setup_qb_run(mock_frappe)
		mock_split.return_value = _split_rows(term_name, invoice_portion)

		make_payment_entries("PO-001")

		self.assertEqual(len(pe.references), 1)
		expected_to_be_pay = (invoice_portion / 100) * grand_total  # 200.0
		self.assertEqual(pe.references[0]["total_amount"], expected_to_be_pay)
		self.assertNotEqual(pe.references[0]["total_amount"], grand_total)

	# ------------------------------------------------------------------
	# Bug 3: No double-allocation with two PRs for same invoice+term
	# ------------------------------------------------------------------
	@patch(f"{MODULE}.group_by_invoices")
	@patch(f"{MODULE}.get_bank_payment_naming_series", return_value=None)
	@patch(f"{MODULE}.get_split_invoice_rows")
	@patch(f"{MODULE}.get_accounting_dimensions", return_value=[])
	@patch(f"{MODULE}.nowdate", return_value="2026-06-12")
	@patch(f"{MODULE}.DocType")
	@patch(f"{MODULE}.frappe")
	def test_no_double_allocation_two_prs_same_invoice_and_term(
		self, mock_frappe, _doctype, _nowdate, _dims, mock_split, _naming, _group
	):
		grand_total = 400.0
		invoice_portion = 50
		term_name = "50% Advance"
		ref1 = _make_reference("SR-001", amount=200.0, pr="PR-001")
		ref2 = _make_reference("SR-002", amount=200.0, pr="PR-002")
		summary_row = _make_summary_row(["SR-001", "SR-002"], amount=400.0)
		pe = _build_pe_mock()

		po_doc = MagicMock(summary=[summary_row])
		po_doc.name = "PO-001"
		po_doc.company = "Test Company"
		po_doc.company_bank_account = "CB-001"
		po_doc.account = "Bank - TC"
		po_doc.payment_order_type = "Purchase Invoice"
		po_doc.posting_date = "2026-06-12"

		mock_frappe.get_single.return_value = MagicMock(
			use_payment_order_date_as_payment_entry_date=False
		)
		mock_frappe.new_doc.return_value = pe

		def get_doc_side_effect(doctype, *args):
			if doctype == "Payment Order":
				return po_doc
			if doctype == "Payment Order Reference":
				return ref1 if args[0] == "SR-001" else ref2
			inv = MagicMock()
			inv.grand_total = grand_total
			return inv

		mock_frappe.get_doc.side_effect = get_doc_side_effect

		def db_get_value(doctype, name, field, *a, **kw):
			mapping = {
				("Payment Request", "payment_term"): None,
				("Payment Request", "net_total"): 200.0,
				(ref1.reference_doctype, "payment_terms_template"): "Standard",
				(
					"Payment Terms Template",
					"allocate_payment_based_on_payment_terms",
				): True,
				("Payment Term", "invoice_portion"): invoice_portion,
				(ref1.reference_doctype, "grand_total"): grand_total,
				("Letter Head", "name"): "Default",
			}
			return mapping.get((doctype, field))

		mock_frappe.db.get_value.side_effect = db_get_value
		# DB always returns 0 committed — in_progress must carry the delta
		_setup_qb_run(mock_frappe)
		mock_split.return_value = _split_rows(term_name, invoice_portion)

		make_payment_entries("PO-001")

		to_be_pay = (invoice_portion / 100) * grand_total  # 200
		total_allocated = sum(r["allocated_amount"] for r in pe.references)
		self.assertLessEqual(
			total_allocated,
			to_be_pay,
			f"Total allocated {total_allocated} exceeds term limit {to_be_pay}",
		)

	# ------------------------------------------------------------------
	# Bug 2: term_paid uses QueryBuilder SUM (not frappe.db.sql)
	# ------------------------------------------------------------------
	@patch(f"{MODULE}.group_by_invoices")
	@patch(f"{MODULE}.get_bank_payment_naming_series", return_value=None)
	@patch(f"{MODULE}.get_split_invoice_rows")
	@patch(f"{MODULE}.get_accounting_dimensions", return_value=[])
	@patch(f"{MODULE}.nowdate", return_value="2026-06-12")
	@patch(f"{MODULE}.DocType")
	@patch(f"{MODULE}.frappe")
	def test_term_paid_uses_query_builder_sum(
		self, mock_frappe, _doctype, _nowdate, _dims, mock_split, _naming, _group
	):
		reference = _make_reference("SR-001", amount=200.0)
		summary_row = _make_summary_row(["SR-001"], amount=200.0)
		pe = _build_pe_mock()

		po_doc = MagicMock(summary=[summary_row])
		po_doc.name = "PO-001"
		po_doc.company = "Test Company"
		po_doc.company_bank_account = "CB-001"
		po_doc.account = "Bank - TC"
		po_doc.payment_order_type = "Purchase Invoice"
		po_doc.posting_date = "2026-06-12"

		mock_frappe.get_single.return_value = MagicMock(
			use_payment_order_date_as_payment_entry_date=False
		)
		mock_frappe.new_doc.return_value = pe

		def get_doc_side_effect(doctype, *args):
			if doctype == "Payment Order":
				return po_doc
			if doctype == "Payment Order Reference":
				return reference
			inv = MagicMock()
			inv.grand_total = 400.0
			return inv

		mock_frappe.get_doc.side_effect = get_doc_side_effect

		def db_get_value(doctype, name, field, *a, **kw):
			mapping = {
				("Payment Request", "payment_term"): None,
				("Payment Request", "net_total"): 200.0,
				(reference.reference_doctype, "payment_terms_template"): "Standard",
				(
					"Payment Terms Template",
					"allocate_payment_based_on_payment_terms",
				): True,
				("Payment Term", "invoice_portion"): 50,
				(reference.reference_doctype, "grand_total"): 400.0,
				("Letter Head", "name"): "Default",
			}
			return mapping.get((doctype, field))

		mock_frappe.db.get_value.side_effect = db_get_value
		_setup_qb_run(mock_frappe)
		mock_split.return_value = _split_rows("50% Advance", 50)

		make_payment_entries("PO-001")

		mock_frappe.qb.from_.assert_called()
		mock_frappe.db.sql.assert_not_called()

	# ------------------------------------------------------------------
	# Simple path: no payment_terms_template → one reference, no QBuilder
	# ------------------------------------------------------------------
	@patch(f"{MODULE}.group_by_invoices")
	@patch(f"{MODULE}.get_bank_payment_naming_series", return_value=None)
	@patch(f"{MODULE}.get_split_invoice_rows")
	@patch(f"{MODULE}.get_accounting_dimensions", return_value=[])
	@patch(f"{MODULE}.nowdate", return_value="2026-06-12")
	@patch(f"{MODULE}.frappe")
	def test_no_payment_terms_template_appends_single_reference(
		self, mock_frappe, _nowdate, _dims, mock_split, _naming, _group
	):
		reference = _make_reference("SR-001", amount=300.0)
		summary_row = _make_summary_row(["SR-001"], amount=300.0)
		pe = _build_pe_mock()

		po_doc = MagicMock(summary=[summary_row])
		po_doc.name = "PO-001"
		po_doc.company = "Test Company"
		po_doc.company_bank_account = "CB-001"
		po_doc.account = "Bank - TC"
		po_doc.payment_order_type = "Purchase Invoice"
		po_doc.posting_date = "2026-06-12"

		mock_frappe.get_single.return_value = MagicMock(
			use_payment_order_date_as_payment_entry_date=False
		)
		mock_frappe.new_doc.return_value = pe

		def get_doc_side_effect(doctype, *args):
			if doctype == "Payment Order":
				return po_doc
			if doctype == "Payment Order Reference":
				return reference
			return MagicMock()

		mock_frappe.get_doc.side_effect = get_doc_side_effect

		def db_get_value(doctype, name, field, *a, **kw):
			if doctype == "Payment Request" and field == "payment_term":
				return None
			if doctype == "Payment Request" and field == "net_total":
				return 300.0
			if (
				doctype == reference.reference_doctype
				and field == "payment_terms_template"
			):
				return None
			return None

		mock_frappe.db.get_value.side_effect = db_get_value

		make_payment_entries("PO-001")

		self.assertEqual(len(pe.references), 1)
		self.assertEqual(pe.references[0]["total_amount"], 300.0)
		mock_split.assert_not_called()
		mock_frappe.qb.from_.assert_not_called()

	# ------------------------------------------------------------------
	# PR with payment_term already set skips split logic
	# ------------------------------------------------------------------
	@patch(f"{MODULE}.group_by_invoices")
	@patch(f"{MODULE}.get_bank_payment_naming_series", return_value=None)
	@patch(f"{MODULE}.get_split_invoice_rows")
	@patch(f"{MODULE}.get_accounting_dimensions", return_value=[])
	@patch(f"{MODULE}.nowdate", return_value="2026-06-12")
	@patch(f"{MODULE}.frappe")
	def test_pr_with_payment_term_skips_split(
		self, mock_frappe, _nowdate, _dims, mock_split, _naming, _group
	):
		reference = _make_reference("SR-001", amount=200.0)
		summary_row = _make_summary_row(["SR-001"], amount=200.0)
		pe = _build_pe_mock()

		po_doc = MagicMock(summary=[summary_row])
		po_doc.name = "PO-001"
		po_doc.company = "Test Company"
		po_doc.company_bank_account = "CB-001"
		po_doc.account = "Bank - TC"
		po_doc.payment_order_type = "Purchase Invoice"
		po_doc.posting_date = "2026-06-12"

		mock_frappe.get_single.return_value = MagicMock(
			use_payment_order_date_as_payment_entry_date=False
		)
		mock_frappe.new_doc.return_value = pe

		def get_doc_side_effect(doctype, *args):
			if doctype == "Payment Order":
				return po_doc
			if doctype == "Payment Order Reference":
				return reference
			return MagicMock()

		mock_frappe.get_doc.side_effect = get_doc_side_effect

		def db_get_value(doctype, name, field, *a, **kw):
			if doctype == "Payment Request" and field == "payment_term":
				return "50% Advance"
			if doctype == "Payment Request" and field == "net_total":
				return 200.0
			return None

		mock_frappe.db.get_value.side_effect = db_get_value

		make_payment_entries("PO-001")

		self.assertEqual(len(pe.references), 1)
		self.assertEqual(pe.references[0]["payment_term"], "50% Advance")
		mock_split.assert_not_called()
		mock_frappe.qb.from_.assert_not_called()

	# ------------------------------------------------------------------
	# in_progress_term_alloc resets per summary row
	# ------------------------------------------------------------------
	@patch(f"{MODULE}.group_by_invoices")
	@patch(f"{MODULE}.get_bank_payment_naming_series", return_value=None)
	@patch(f"{MODULE}.get_split_invoice_rows")
	@patch(f"{MODULE}.get_accounting_dimensions", return_value=[])
	@patch(f"{MODULE}.nowdate", return_value="2026-06-12")
	@patch(f"{MODULE}.DocType")
	@patch(f"{MODULE}.frappe")
	def test_in_progress_term_alloc_resets_per_summary_row(
		self, mock_frappe, _doctype, _nowdate, _dims, mock_split, _naming, _group
	):
		grand_total = 400.0
		invoice_portion = 50
		term_name = "50% Advance"

		ref1 = _make_reference("SR-001", amount=200.0, pr="PR-001")
		ref2 = _make_reference("SR-002", amount=200.0, pr="PR-002")
		row1 = _make_summary_row(["SR-001"], amount=200.0, row_name="POS-ROW-001")
		row2 = _make_summary_row(["SR-002"], amount=200.0, row_name="POS-ROW-002")

		pe1, pe2 = _build_pe_mock(), _build_pe_mock()
		pe_instances = iter([pe1, pe2])

		po_doc = MagicMock(summary=[row1, row2])
		po_doc.name = "PO-001"
		po_doc.company = "Test Company"
		po_doc.company_bank_account = "CB-001"
		po_doc.account = "Bank - TC"
		po_doc.payment_order_type = "Purchase Invoice"
		po_doc.posting_date = "2026-06-12"

		mock_frappe.get_single.return_value = MagicMock(
			use_payment_order_date_as_payment_entry_date=False
		)
		mock_frappe.new_doc.side_effect = lambda _: next(pe_instances)

		def get_doc_side_effect(doctype, *args):
			if doctype == "Payment Order":
				return po_doc
			if doctype == "Payment Order Reference":
				return ref1 if args[0] == "SR-001" else ref2
			inv = MagicMock()
			inv.grand_total = grand_total
			return inv

		mock_frappe.get_doc.side_effect = get_doc_side_effect

		def db_get_value(doctype, name, field, *a, **kw):
			mapping = {
				("Payment Request", "payment_term"): None,
				("Payment Request", "net_total"): 200.0,
				(ref1.reference_doctype, "payment_terms_template"): "Standard",
				(
					"Payment Terms Template",
					"allocate_payment_based_on_payment_terms",
				): True,
				("Payment Term", "invoice_portion"): invoice_portion,
				(ref1.reference_doctype, "grand_total"): grand_total,
				("Letter Head", "name"): "Default",
			}
			return mapping.get((doctype, field))

		mock_frappe.db.get_value.side_effect = db_get_value
		mock_split.return_value = _split_rows(term_name, invoice_portion)

		# row1 sees 0 committed; row2 sees 200 committed (row1 already submitted)
		qb_results = iter([((0,),), ((200.0,),)])
		mock_frappe.qb.from_.return_value.select.return_value.where.return_value.run.side_effect = (
			lambda: next(qb_results)
		)

		make_payment_entries("PO-001")

		# row1: paid 200; row2: db_term_paid=200 == to_be_pay → paid_amount=0
		self.assertEqual(len(pe1.references), 1)
		self.assertEqual(len(pe2.references), 0)


if __name__ == "__main__":
	unittest.main()
