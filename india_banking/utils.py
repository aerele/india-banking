import ast
import json
import re

import frappe
from frappe import _
from frappe.utils.background_jobs import is_job_enqueued

from india_banking.default import ALLOWED_PAYMENT_DOCTYPE


@frappe.whitelist()
def get_allowed_payment_doctypes():
	return ALLOWED_PAYMENT_DOCTYPE


def get_bank_address_details(bank_account):
	address = frappe.db.get_value(
		"Dynamic Link",
		{"link_doctype": "Bank Account", "link_name": bank_account},
		"parent",
	)
	if not address:
		return {}

	party_address_ = frappe.get_doc("Address", address)
	address_line = party_address_.get("address_line1", "").split(",")
	street_name = party_address_.get("city", "")
	building_number = address_line[0] if address_line else ""

	if len(building_number) > 10:
		building_number = building_number[:10]

	post_code = party_address_.get("pincode", "")

	town_name = (
		party_address_.get("state", "")[:3].upper()
		if party_address_.get("state", "")
		else ""
	)

	country_sub_division = (
		[party_address_.get("country", "")[:2]]
		if party_address_.get("country", "")
		else []
	)
	country = party_address_.get("country", "")[:2]

	return {
		"AddressLine": address_line,
		"StreetName": street_name,
		"BuildingNumber": building_number,
		"PostCode": post_code,
		"TownName": town_name,
		"CountySubDivision": country_sub_division,
		"Country": country,
	}


def get_party_field_name(party_type):
	return {
		"Supplier": "supplier_name",
		"Customer": "customer_name",
		"Employee": "employee_name",
	}.get(party_type, "name")


def extract_error_message(response_json, show_message=False) -> str:
	try:
		response_json = (
			json.loads(response_json)
			if isinstance(response_json, str)
			else response_json
		)
		failure_message = ""

		# Check if the response contains a server error message
		server_message = response_json.get("_server_messages", "[]")
		if server_message and (server_message := json.loads(server_message)):
			server_message = json.loads(server_message[0]) or {}
			failure_message = server_message.get("message", "")

		if isinstance(response_json.get("message", {}), dict):
			failure_message = failure_message or response_json.get("message", {}).get(
				"errormessage", ""
			)
			failure_message = failure_message or response_json.get("message", {}).get(
				"error", ""
			)
			failure_message = failure_message or response_json.get("message", {}).get(
				"message", ""
			)

		if show_message and failure_message:
			frappe.msgprint(title=_("Failure Reason"), msg=failure_message)

		elif failure_message:
			return failure_message

	except Exception:
		frappe.throw(
			title=_("Error: Could not process the response"),
			msg=frappe.get_traceback(with_context=1),
		)


def unlink_bank_payment(payment_order_summary=None):
	"""
	Unlinks bank payment references from the given payment order summary.

	This function takes a payment order summary and removes the references to
	payment requests and payment order references associated with it. It updates
	the database to clear the reference doctype and reference name fields.
	"""
	if not payment_order_summary:
		return

	summary_references = ast.literal_eval(
		payment_order_summary.get("summary_references")
	)
	for reference in summary_references:
		payment_request = frappe.get_doc(
			"Payment Order Reference", reference, "payment_request"
		)
		if payment_request:
			frappe.db.set_value(
				"Payment Request",
				payment_request,
				{"reference_doctype": "", "reference_name": ""},
			)
		frappe.db.set_value(
			"Payment Order Reference",
			reference,
			{"reference_doctype": "", "reference_name": ""},
		)

		frappe.db.set_value(
			"Payment Order Summary",
			payment_order_summary.name,
			{"reference_doctype": "", "reference_name": ""},
		)


def get_payment_order_summary(payment_entry):
	is_ammended = frappe.db.get_value("Payment Entry", payment_entry, "amended_from")
	payment_entry = (
		"-".join(payment_entry.split("-")[:-1]) if is_ammended else payment_entry
	)
	summary = frappe.db.get_value(
		"Payment Order Summary", {"payment_entry": payment_entry}, "name"
	)
	if summary:
		return frappe.get_doc("Payment Order Summary", summary)


@frappe.whitelist()
def get_party_bank_account(party_type, party):
	workflow = ""
	if frappe.db.get_single_value(
		"India Banking Settings", "activate_workflow_on_bank_account"
	):
		workflow = "Approved"

	filters = {"party_type": party_type, "party": party, "is_default": 1}

	if workflow:
		filters.update({"workflow_state": workflow})

	return frappe.db.get_value("Bank Account", filters)


def add_background_job(job_id, job_name, method, **kwargs):
	def _add_queue(job_id, job_name, method, **kwargs):
		frappe.enqueue(
			method,
			**kwargs,
			job_id=job_id,
			job_name=job_name,
			enqueue_after_commit=True,
		)

	job_id = "".join(re.findall(r"[0-9a-zA-Z]", job_id))[-10:] + "-" + job_name

	if not frappe.db.exists("RQ Job", job_id):
		_add_queue(job_id, job_name, method, **kwargs)

	elif (rq_job := frappe.db.exists("RQ Job", job_id)) and not is_job_enqueued(job_id):
		frappe.get_doc("RQ Job", rq_job).delete()
		frappe.clear_cache(doctype="RQ Job")
		_add_queue(job_id, job_name, method, **kwargs)

	return True
