import frappe
from frappe.query_builder import DocType

def daily():
	"""Daily task to update payment dates and repost ledger entries."""
	update_payment_date_as_posting_date()

def update_payment_date_as_posting_date():
	"""Update Payment Entry posting dates based on Payment Order Summary and repost accounting ledgers."""

	#check settings enabled
	if not frappe.get_single("India Banking Settings").update_posting_date_as_payment_date:
		return
	
	# Define DocTypes for query builder
	PaymentEntry = DocType("Payment Entry")
	PaymentOrderSummary = DocType("Payment Order Summary")

	# Fetch payment entries with mismatched posting dates
	reposting_entries = (
		frappe.qb.from_(PaymentOrderSummary)
		.join(PaymentEntry)
		.on(PaymentOrderSummary.payment_entry == PaymentEntry.name)
		.select(PaymentOrderSummary.payment_entry)
		.where(
			(PaymentEntry.docstatus == 1)
			& (PaymentOrderSummary.payment_date.isnotnull())
			& (PaymentOrderSummary.payment_date != PaymentEntry.posting_date)
		)
		.groupby(PaymentEntry.name)
	).run(as_dict=True)

	if reposting_entries:
		# Update mismatched posting dates
		(
			frappe.qb.update(PaymentEntry)
			.join(PaymentOrderSummary)
			.on(PaymentOrderSummary.payment_entry == PaymentEntry.name)
			.set(PaymentEntry.posting_date, PaymentOrderSummary.payment_date)
			.where(
				(PaymentEntry.docstatus == 1)
				& (PaymentOrderSummary.payment_date.isnotnull())
				& (PaymentOrderSummary.payment_date != PaymentEntry.posting_date)
			)
		).run()

		frappe.db.commit()

		# Repost accounting ledger entries for updated Payment Entries
		reposting_doc = frappe.new_doc("Repost Accounting Ledger")
		for entry in reposting_entries:
			reposting_doc.append("vouchers", {
				"voucher_type": "Payment Entry",
				"voucher_no": entry['payment_entry']
			})

		# Save and submit the Repost Accounting Ledger document
		reposting_doc.save()
		reposting_doc.submit()