from erpnext.accounts.doctype.payment_entry.payment_entry import PaymentEntry


class CustomPaymentEntry(PaymentEntry):
	def validate_duplicate_entry(self):
		reference_names = []
		for d in self.get("references"):
			reference_names.append((d.reference_doctype, d.reference_name, d.payment_term))