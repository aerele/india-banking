def on_cancel(doc, method=None):
	if not doc.flags.from_bank_failure:
		return

	ignored_doctypes = list(doc.get("ignore_linked_doctypes") or [])
	if "Payment Order" not in ignored_doctypes:
		ignored_doctypes.append("Payment Order")
	doc.ignore_linked_doctypes = ignored_doctypes
