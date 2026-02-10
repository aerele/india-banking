# Copyright (c) 2024, Aerele Technologies Private Limited and contributors
# For license information, please see license.txt

import json

import frappe
import requests
from frappe.model.document import Document
from requests.models import Response

from india_banking.utils import extract_error_message


class IndiaBankingRequestLog(Document):
	@frappe.whitelist()
	def show_failure_message(self):
		extract_error_message(json.loads(self.response), show_message=True)

	@staticmethod
	def clear_old_logs(days=30):
		from frappe.query_builder import Interval
		from frappe.query_builder.functions import Now

		table = frappe.qb.DocType("India Banking Request Log")
		frappe.db.delete(
			table, filters=(table.creation < (Now() - Interval(days=days)))
		)


def format_with_indent(data):
	try:
		if isinstance(data, dict):
			return json.dumps(data, indent=4)
		elif isinstance(data, requests.structures.CaseInsensitiveDict):
			return json.dumps(dict(data), indent=4)
		else:
			return format_with_indent(json.loads(data))

	except Exception:
		frappe.log_error(
			title="Error in formatting data", message=frappe.get_traceback()
		)
		return data


@frappe.whitelist()
def create_api_log(res, action=None, ref_doctype=None, ref_docname=None):
	"""Can create API log From response

	Args:
	                res (response object): It is used to obtain an API response.
	                request_from (str): It is optional for the purposes of the API...
	"""
	if not isinstance(res, Response):
		return

	try:
		log_doc = frappe.new_doc("India Banking Request Log")
		log_doc.action = action
		log_doc.url = res.request.url
		log_doc.method = res.request.method
		log_doc.header = format_with_indent(res.request.headers)
		log_doc.payload = format_with_indent(res.request.body)
		log_doc.response = format_with_indent(res.text)
		log_doc.status_code = res.status_code
		log_doc.reference_doctype = ref_doctype
		log_doc.reference_docname = ref_docname
		log_doc.save()

	except Exception:
		frappe.log_error(
			title="Error in creating API Log", message=frappe.get_traceback()
		)
	else:
		frappe.db.commit()
		return log_doc.name
