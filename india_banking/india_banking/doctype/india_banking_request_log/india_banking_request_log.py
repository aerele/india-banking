# Copyright (c) 2024, Aerele Technologies Private Limited and contributors
# For license information, please see license.txt

import json

import frappe
import requests
from frappe import _
from frappe.model.document import Document
from requests.models import Response


class IndiaBankingRequestLog(Document):
	@frappe.whitelist()
	def show_failure_message(self):
		try:
			if (
				self.response
				and (response := json.loads(self.response))
				and (server_messages := response.get("_server_messages"))
			):
				if (
					server_messages
					and (server_messages := json.loads(server_messages))
					and (server_message := server_messages[0])
				):
					server_message = json.loads(server_message)
					title = _("Failure Reason")
					message = _(
						f'{frappe.bold(server_message.get("title", ""))}: {server_message.get("message", "")}'
					)
					frappe.msgprint(title=title, msg=message)
		except:
			frappe.msgprint(
				title=_("Error: Could not process the response"),
				msg=frappe.get_traceback(with_context=1),
			)


def format_with_indent(data):
	try:
		if isinstance(data, dict):
			return json.dumps(data, indent=4)
		elif isinstance(data, requests.structures.CaseInsensitiveDict):
			return json.dumps(dict(data), indent=4)
		else:
			return format_with_indent(json.loads(data))
	except:
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
	except:
		frappe.log_error(
			title="Error in creating API Log", message=frappe.get_traceback()
		)
	else:
		frappe.db.commit()
		return log_doc.name
