import json

import frappe
from frappe import _


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
		response_json = json.loads(response_json) if isinstance(response_json, str) else response_json
		failure_message = ""

		server_message = response_json.get("_server_messages", "[]")
		if server_message and (server_message := json.loads(server_message)):
			server_message = json.loads(server_message[0])
			failure_message = _(
				f'{frappe.bold(server_message.get("title", ""))}: {server_message.get("message", "")}'
			)

		failure_message = failure_message or json.loads(
			response_json.get("message", "{}").get("message", "{}")
		).get("errormessage", "")

		if show_message and failure_message:
			frappe.msgprint(title=_("Failure Reason"), msg=failure_message)

		elif failure_message:
			return failure_message

	except:
		frappe.throw(
			title=_("Error: Could not process the response"),
			msg=frappe.get_traceback(with_context=1),
		)
