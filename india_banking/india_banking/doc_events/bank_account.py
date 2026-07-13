import frappe, re
from frappe import _ , cstr

def validate_ifsc_code(self, method):
	pattern = re.compile("^[A-Z]{4}0[A-Z0-9]{6}$")
	if not pattern.match(cstr(self.branch_code)):
		frappe.throw(_("IFSC/Branch Code is not valid"))


def validate_duplicate_receivers(self, method):
	first_row_idx = {}
	for row in (self.get("beneficiaries") or []):
		if not row.company or not row.receiver_id:
			continue
		key = (row.company, row.receiver_id)
		if key in first_row_idx:
			receiver = row.beneficiary_name or row.beneficiary or row.receiver_id
			frappe.throw(
				_("Row #{0}: Receiver {1} is already added for Company {2} (row #{3}).").format(
					row.idx, frappe.bold(receiver), frappe.bold(row.company), first_row_idx[key]
				),
				title=_("Duplicate Receiver"),
			)
		first_row_idx[key] = row.idx