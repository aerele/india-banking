# Testing Guide

## Running Tests

Always run on a `*.test` site — never on `.local`, `.dev`, or production.

```bash
# Full app test suite
bench --site india_banking.test run-tests --app india_banking

# Single module
bench --site india_banking.test run-tests --module india_banking.india_banking.doctype.bank_account.test_bank_account

# Single test class
bench --site india_banking.test run-tests --module india_banking.india_banking.doctype.bank_account.test_bank_account --test TestBankAccount
```

## Existing Test Coverage

| Test File | Covers |
|---|---|
| `test_bank_account.py` | IFSC validation, unique account no, party currency |
| `test_payment_request.py` | Payment Request creation, autoname, GST payables |
| `test_mode_of_transfer.py` | Transfer mode limits |
| `test_india_banking_connector.py` | Connector setup and API calls |
| `test_india_banking_settings.py` | Settings flags |
| `test_india_banking_request_log.py` | Log creation and retention |
| `test_unreconcile_bank_payment.py` | Unreconcile flow |
| `test_bank.py` | Bank deletion prevention |

## Writing New Tests

Follow ERPNext test conventions:

```python
import frappe
import unittest
from frappe.tests.utils import FrappeTestCase

class TestPaymentOrder(FrappeTestCase):
    def setUp(self):
        # Create minimal fixtures
        pass

    def test_validate_summary(self):
        # ...
        pass
```

- Use `FrappeTestCase` not plain `unittest.TestCase` — it handles DB setup/teardown.
- Mock external API calls (bank connector calls) using `unittest.mock.patch`.
- Never hit real bank APIs in tests — patch `requests.get` / `requests.post`.

## Manual Test Flows (v16 Migration Verification)

1. **Payment Request → Payment Order → Payment Entry**
   - Create supplier + purchase invoice
   - Create Payment Request
   - Submit Payment Request → run `make_payment_order()`
   - Submit Payment Order → verify Payment Entries created

2. **Payment Entry → Payment Order**
   - Create submitted Pay-type Payment Entry
   - Click "Initiate Payment" → select mode → verify Payment Order created

3. **Journal Entry (Bank Entry) → Payment Order**
   - Create Bank Entry with party + bank account
   - Run `make_payment_order()` → verify grouping by party

4. **Bank Account Workflow**
   - Enable `enable_bank_account_workflow` in settings
   - Create Bank Account → verify it requires approval before use in Payment Request
