# Copyright (c) 2024, Aerele Technologies Private Limited and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import get_datetime

class OTPLog(Document):
	def autoname(self):
		self.name = get_datetime().strftime("%Y%m%d%H%M%S")
