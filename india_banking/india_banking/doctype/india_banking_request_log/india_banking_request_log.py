# Copyright (c) 2024, Aerele Technologies Private Limited and contributors
# For license information, please see license.txt

import frappe
import json
from frappe.model.document import Document
from requests.models import Response

class IndiaBankingRequestLog(Document):
	pass


@frappe.whitelist()
def create_api_log(res, action= None, ref_doctype= None, ref_docname= None):
	"""Can create API log From response

	Args:
		res (response object): It is used to obtain an API response.
		request_from (str): It is optional for the purposes of the API...
	"""
	if not isinstance(res, Response): return

	try:
		log_doc = frappe.new_doc("India Banking Request Log")
		log_doc.action = action
		log_doc.url = res.request.url
		log_doc.method = res.request.method
		log_doc.header = json.dumps(dict(res.request.headers), indent=4)
		log_doc.payload =json.dumps(json.loads(res.request.body), indent=4)
		log_doc.response = json.dumps(res.json(), indent=4)
		log_doc.status_code = res.status_code
		log_doc.reference_doctype = ref_doctype
		log_doc.reference_docname = ref_docname
		log_doc.save()
	except:
		frappe.log_error(title='Error in creating API Log', message=frappe.get_traceback())
	else:
		frappe.db.commit()