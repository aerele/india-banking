import frappe, json
from datetime import datetime
from frappe import _
import requests
from frappe.utils import get_link_to_form




def create_response_log(log_details):
	log = frappe.get_doc({
							"doctype": "India Banking Request Log",
							"status": log_details.status,
							"payload": log_details.get("payload") or "",
							"voucher_type": log_details.get("voucher_type"),
							"voucher_name": log_details.get("voucher_name"),
							"response": json.dumps(log_details.get("response"), indent=4),

	}).insert(ignore_permissions=True)
	frappe.db.commit()
	return log.name


def send_request(args):
	response = requests.request(args.method, args.url, headers=args.headers, data=args.payload)
	data = frappe._dict(json.loads(response.text))
	log_name = create_response_log(frappe._dict({
							"status": "Success" if response.ok else "Failure",
							"payload": args.payload,
							"voucher_type": args.get("voucher_type") or "",
							"voucher_name": args.get("voucher_name") or "",
							"response": json.loads(response.text),

	}))

	if response.ok:
		return response.text

	else:
		return response.text
