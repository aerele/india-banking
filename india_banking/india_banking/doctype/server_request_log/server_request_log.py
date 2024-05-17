# Copyright (c) 2024, Aerele Technologies Private Limited and contributors
# For license information, please see license.txt

import frappe
import json
from frappe.model.document import Document


class ServerRequestLog(Document):
	pass



@frappe.whitelist()
def create_api_log(res, action= None):	
	"""Can create API log From response

	Args:
		res (response object): It is used to obtain an API response.
		request_from (str): It is optional for the purposes of the API...
	"""
	if not res: return
	
	log_doc = frappe.new_doc("Server Request Log")
	log_doc.action = action
	log_doc.url = res.request.url
	log_doc.method = res.request.method
	log_doc.header = json.dumps(dict(res.request.headers))
	log_doc.payload =res.request.body
	log_doc.response = json.dumps(res.json())
	log_doc.status_code = res.status_code
	log_doc.save()
	
	frappe.db.commit()