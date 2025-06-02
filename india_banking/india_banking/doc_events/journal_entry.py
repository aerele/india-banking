import frappe
from frappe import _, bold


def on_cancel(doc, method=None):
	for acc in doc.accounts:
		if acc.reference_details and acc.payment_status in [
			"Ordered",
			"Payment Ordered",
		]:
			if acc.reference_details:
				payment_order = frappe.get_value(
					"Payment Order Reference", acc.reference_details, "parent"
				)
				frappe.throw(
					_(
						(
							f"We can see <b>#row {acc.idx}</b> linked with Payment Order "
							f"{bold(payment_order)}."
							"<br>Please unlink the Payment Order before cancelling the Journal Entry."
						)
					)
				)
		elif acc.payment_status == "Paid":
			frappe.throw(
				f"Cannot cancel Journal Entry already paid <b>#Row {acc.idx}</b>"
			)
