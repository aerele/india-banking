import frappe, re
from frappe import _ , cstr

def validate_ifsc_code(self, method):
	pattern = re.compile("^[A-Z]{4}0[A-Z0-9]{6}$")
	if not pattern.match(cstr(self.branch_code)):
		frappe.throw(_("IFSC/Branch Code is not valid"))


def validate_duplicate_receivers(self, method):
	for row in (self.get("beneficiaries") or []):
		if not row.company or not row.receiver_id:
			continue

		if frappe.db.exists(
			"Beneficiaries",
			{
				"company": row.company,
				"receiver_id": row.receiver_id,
				"parent": self.name,
				"name": ["!=", row.name],
			},
		):
			frappe.throw(
				_("Row #{0}: Receiver {1} is already added for Company {2}.").format(
					row.idx, frappe.bold(row.receiver_id), frappe.bold(row.company)
				),
				title=_("Duplicate Receiver"),
			)
