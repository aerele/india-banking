import json

import frappe
import requests
from frappe import _

from india_banking.india_banking.default import ALLOWED_DOCTYPES


def create_response_log(log_details):
	log = frappe.get_doc(
		{
			"doctype": "India Banking Request Log",
			"status": log_details.status,
			"payload": log_details.get("payload") or "",
			"voucher_type": log_details.get("voucher_type"),
			"voucher_name": log_details.get("voucher_name"),
			"response": json.dumps(log_details.get("response"), indent=4),
		}
	).insert(ignore_permissions=True)
	frappe.db.commit()
	return log.name


def send_request(args):
	response = requests.request(
		args.method, args.url, headers=args.headers, data=args.payload
	)
	data = frappe._dict(json.loads(response.text))
	log_name = create_response_log(
		frappe._dict(
			{
				"status": "Success" if response.ok else "Failure",
				"payload": args.payload,
				"voucher_type": args.get("voucher_type") or "",
				"voucher_name": args.get("voucher_name") or "",
				"response": json.loads(response.text),
			}
		)
	)

	if response.ok:
		return response.text

	else:
		return response.text


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


@frappe.whitelist()
def get_allowed_doctypes(*args):
	return [[doctype] for doctype in ALLOWED_DOCTYPES]


@frappe.whitelist()
def is_bank_payment_request_enabled(doctype, workflow=None):
	allowed_details = frappe.get_value(
		"Payment Allowed Doctype",
		{
			"doctype_name": doctype,
			"allow": 1,
		},
		["doctype_name", "workflow"],
		as_dict=1,
	)

	enabled = 0
	if allowed_details:
		enabled = 1
		if allowed_details.get("workflow", "") and workflow != allowed_details.get(
			"workflow", ""
		):
			enabled = 0

	return {"enabled": enabled}
