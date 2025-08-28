import ast
import json

import frappe
from frappe import _, bold
from frappe.utils import get_link_to_form

from india_banking.default import ALLOWED_PAYMENT_DOCTYPE
from india_banking.india_banking.doctype.party_bank_account_field_map.party_bank_account_field_map import (
	get_party_bank_fields,
)


@frappe.whitelist()
def get_allowed_payment_doctypes():
	return ALLOWED_PAYMENT_DOCTYPE


def get_bank_address_details(bank_account, validate=False):
	address = frappe.db.get_value(
		"Dynamic Link",
		{"link_doctype": "Bank Account", "link_name": bank_account},
		"parent",
	)

	bank_account_currency = frappe.get_value("Bank Account", bank_account, "currency")

	if not bank_account_currency:
		bank_account_currency = "INR"

	if not address:
		link = get_link_to_form("Bank Account", bank_account)
		if validate:
			frappe.throw(
				"Address mandatory for Bank Account {0}".format(frappe.bold(link))
			)
		return {}

	bank_address = frappe.get_doc("Address", address)
	address_line = bank_address.get("address_line1", "").split(",")
	street_name = bank_address.get("city", "")
	building_number = address_line[0] if address_line else ""

	if len(building_number) > 10:
		building_number = building_number[:10]

	post_code = bank_address.get("pincode", "")

	town_name = (
		bank_address.get("state", "")[:3].upper()
		if bank_address.get("state", "")
		else ""
	)

	country_sub_division = (
		bank_address.get("country", "")[:2] if bank_address.get("country", "") else ""
	)
	country = bank_address.get("country", "")

	country_code = bank_address.county

	missing_details = []
	invalid_details = []
	address_details = frappe._dict(
		{
			"name": address,
			"AddressLine": address_line,
			"StreetName": street_name,
			"BuildingNumber": building_number,
			"PostCode": post_code,
			"State": bank_address.get("state", ""),
			"TownName": town_name,
			"CountySubDivision": country_sub_division,
			"Country": country,
			"CountryCode": country_code,
		}
	)

	if validate:
		for key in address_details:
			if not address_details.get(key):
				missing_details.append(key)
				continue

			if key == "CountryCode" and (
				bank_account_currency != "INR"
				and address_details.get("CountryCode", "").lower() == "in"
			):
				msg = "The <b>Country Code</b> for currency {} should not be set to <b>IN</b>".format(
					bold(bank_account_currency)
				)
				invalid_details.append(msg)
			if key == "Country" and (
				bank_account_currency != "INR"
				and "india" in address_details.get("Country", "").lower()
			):
				msg = "The <b>Country</b> for currency {} should not be set to <b>India</b>".format(
					bold(bank_account_currency)
				)
				invalid_details.append(msg)

	if missing_details:
		link = get_link_to_form("Address", address)
		frappe.throw(
			title="Following Bank Details Are Missing in Bank Address</br>{0}".format(
				bold(link)
			),
			msg=bold(", ".join(missing_details)),
		)
	if invalid_details:
		link = get_link_to_form("Address", address)
		frappe.throw(
			title="Following Bank Details Are Invalid for Bank Address</br>{0}".format(
				bold(link)
			),
			msg="</br>".join(invalid_details),
		)

	return address_details


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

		server_message = response_json.get("_server_messages", "[]")
		if server_message and (server_message := json.loads(server_message)):
			server_message = json.loads(server_message[0])
			failure_message = _(
				f'{frappe.bold(server_message.get("title", ""))}: {server_message.get("message", "")}'
			)

		failure_message = failure_message or response_json.get("message", "")
		if isinstance(failure_message, dict):
			failure_message = failure_message.get("message", "")
		if isinstance(failure_message, dict):
			failure_message = failure_message.get("errormessage", "")

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


def validate_party_bank_account_details(target, update=False):
	if (party_type := target.get("party_type")) and (party_name := target.get("party")):
		party_bank_fields = get_party_bank_fields(party_type)
		if not party_bank_fields:
			return False

		party = frappe.get_doc(party_type, party_name)
		for target_field, source_field in party_bank_fields.items():
			if not hasattr(party, source_field):
				frappe.throw(
					_("Please set <b>{}</b> for {} - {}").format(
						source_field.replace("custom_", "").replace("_", " ").title(),
						party_type,
						frappe.bold(party_name),
					)
				)
			elif not party.get(source_field):
				frappe.throw(
					_("Mandatory Field Required <b>{}</b> for {} - {}").format(
						source_field.replace("custom_", "").replace("_", " ").title(),
						party_type,
						frappe.bold(party_name),
					)
				)
			else:
				if update:
					target.update({target_field: party.get(source_field)})
		return True
