import frappe
from india_banking.india_banking.install import create_default_bank

def execute():
    create_default_bank()