import unittest
import ast

def parse_summary_references(raw_references):
	if not raw_references:
		return []
	if isinstance(raw_references, str):
		try:
			return ast.literal_eval(raw_references)
		except (ValueError, SyntaxError):
			return []
	elif isinstance(raw_references, (list, tuple)):
		return list(raw_references)
	return []


def minutes_to_cron(minutes: int) -> str:
	if not minutes or minutes <= 0:
		return "* * * * *"
	if minutes < 60:
		return f"*/{minutes} * * * *"
	elif minutes % 60 == 0 and minutes < 1440:
		hours = minutes // 60
		if hours == 1:
			return "0 * * * *"
		else:
			return f"0 */{hours} * * *"
	elif minutes == 1440:
		return "0 0 * * *"
	else:
		days = minutes / 1440
		if days.is_integer():
			return f"0 0 */{int(days)} * *"
		return f"*/{minutes} * * * *"


class TestBankingUtils(unittest.TestCase):
	def test_minutes_to_cron_edge_cases(self):
		self.assertEqual(minutes_to_cron(0), "* * * * *")
		self.assertEqual(minutes_to_cron(-5), "* * * * *")
		self.assertEqual(minutes_to_cron(15), "*/15 * * * *")
		self.assertEqual(minutes_to_cron(60), "0 * * * *")
		self.assertEqual(minutes_to_cron(120), "0 */2 * * *")
		self.assertEqual(minutes_to_cron(1440), "0 0 * * *")
		self.assertEqual(minutes_to_cron(2880), "0 0 */2 * *")
		self.assertEqual(minutes_to_cron(90), "*/90 * * * *")

	def test_parse_summary_references_safety(self):
		self.assertEqual(parse_summary_references(None), [])
		self.assertEqual(parse_summary_references(""), [])
		self.assertEqual(parse_summary_references("['ref1', 'ref2']"), ['ref1', 'ref2'])
		self.assertEqual(parse_summary_references(['ref1', 'ref2']), ['ref1', 'ref2'])
		self.assertEqual(parse_summary_references("invalid syntax {"), [])
