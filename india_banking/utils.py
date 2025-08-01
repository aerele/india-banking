import json

import frappe
import requests
from frappe import _

from india_banking.india_banking.default import ALLOWED_DOCTYPES
import re

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


@frappe.whitelist()
def find_payments(transaction_id):
	matched_payments = []
	bank_transaction = frappe.get_doc("Bank Transaction", transaction_id)
	payments = get_api_payments(bank_transaction)
	if payments:
		for payment_entry in payments:
			if payment_entry:
				party_type = frappe.get_value("Payment Entry", payment_entry, "party_type")
				party = frappe.get_value("Payment Entry", payment_entry, "party")
				paid_amount = frappe.get_value("Payment Entry", payment_entry, "paid_amount")
				matched_payments.append({
					"doctype": "Payment Entry",
					"docname": payment_entry,
					"party_type": party_type,
					"party": party,
					"amount": paid_amount,
				})

	return matched_payments


def get_api_payments(bank_transaction):
	description = bank_transaction.description
	if not description:
		return []

	filters = {}

	if description.startswith("PAYMENT FROM"):
		match = re.search(r'(?<=PAYMENT FROM\s)[^\s]+', description)
		if bank_transaction.party_type and bank_transaction.party:
			filters.update({
				"party_type": bank_transaction.party_type,
				"party": bank_transaction.party,
			})
		if bank_transaction.withdrawal:
			filters["amount"] = bank_transaction.withdrawal
		if match:
			filters["parent"] = match.group()

	elif description.startswith("PT-") and description.endswith("-TID"):
		match = re.search(r"PR-(\S+)\s+(.+?)-TID", description)
		if match:
			payment_id, transaction_id = match.group(1), match.group(2)
			if payment_id:
				filters["parent"] = payment_id
			if transaction_id:
				filters["name"] = transaction_id

	elif description.startswith("PT-"):
		match = re.match(r'PR-(PMO-\d+)\s+(.+)', description)
		if match:
			payment_id = match.group(1)
			party_name = match.group(2)
			if payment_id:
				filters["parent"] = payment_id
			if party_name:
				filters["party"] = party_name

	if filters:
		return frappe.get_all("Payment Order Summary", filters, pluck="payment_entry") or []

	return []
