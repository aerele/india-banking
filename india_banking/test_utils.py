import sys
import unittest
from unittest.mock import MagicMock

# If running outside Frappe environment, mock frappe module for isolated testing
if "frappe" not in sys.modules:
	sys.modules["frappe"] = MagicMock()
	sys.modules["frappe.utils"] = MagicMock()
	sys.modules["frappe.utils.background_jobs"] = MagicMock()

from india_banking.utils import minutes_to_cron, parse_summary_references


class TestBankingUtils(unittest.TestCase):
	def test_minutes_to_cron_valid(self):
		self.assertEqual(minutes_to_cron(1), "*/1 * * * *")
		self.assertEqual(minutes_to_cron(15), "*/15 * * * *")
		self.assertEqual(minutes_to_cron(59), "*/59 * * * *")
		self.assertEqual(minutes_to_cron(60), "0 * * * *")
		self.assertEqual(minutes_to_cron(120), "0 */2 * * *")
		self.assertEqual(minutes_to_cron(1440), "0 0 * * *")
		self.assertEqual(minutes_to_cron(2880), "0 0 */2 * *")

	def test_minutes_to_cron_invalid(self):
		with self.assertRaises(ValueError):
			minutes_to_cron(0)
		with self.assertRaises(ValueError):
			minutes_to_cron(-5)
		with self.assertRaises(ValueError):
			minutes_to_cron(90)  # Non-divisor across hours cannot be a valid standard cron
		with self.assertRaises(ValueError):
			minutes_to_cron(75)

	def test_parse_summary_references_safety(self):
		self.assertEqual(parse_summary_references(None), [])
		self.assertEqual(parse_summary_references(""), [])
		self.assertEqual(parse_summary_references("[]"), [])
		self.assertEqual(parse_summary_references("['ref1', 'ref2']"), ['ref1', 'ref2'])
		self.assertEqual(parse_summary_references(['ref1', 'ref2']), ['ref1', 'ref2'])
		self.assertEqual(parse_summary_references(('ref1', 'ref2')), ['ref1', 'ref2'])

	def test_parse_summary_references_malformed(self):
		with self.assertRaises((ValueError, SyntaxError)):
			parse_summary_references("invalid syntax {")
		with self.assertRaises(TypeError):
			parse_summary_references(12345)
