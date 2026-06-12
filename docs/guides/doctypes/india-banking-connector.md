# India Banking Connector

## Overview

India Banking Connector is the bridge between ERPNext and a bank's API. It stores the API credentials, controls which services are enabled (balance, statements, payments), and drives the background scheduler tasks that auto-update payment statuses.

Every company bank account that needs live banking integration must have exactly one connector. Connectors without an active bank account have no effect.

---

## Relationship to Bank Account

The connector has a **strict 1-to-1 relationship** with Bank Account:

| Rule | Detail |
|---|---|
| `autoname: field:bank_account` | Connector is named after the Bank Account — they share the same name |
| `bank_account` field: `unique:1`, `reqd:1` | One connector per bank account, enforced at the DB level |
| `bank` field: fetched from `bank_account.bank` | Auto-populated, no manual entry needed |
| Dashboard link | Bank Account dashboard shows the linked connector under the "Connector" section |

**Flow:** Bank Account → (approve) → India Banking Connector → (configure) → payments and services enabled

---

## Setup Steps

1. Create and save a Bank Account (approve it if the workflow is enabled)
2. Go to **Banking → Setup → India Banking Connector → New**
3. Select the **Bank Account** — name, bank, and company auto-fill
4. Enter the **URL**, **API Key**, and **API Secret** provided by the bank
5. Enable the **Service Subscriptions** you have access to
6. Configure **Payment Configuration** settings based on bank API limits
7. Save

---

## Fields Reference

### Identity

| Field | Type | Purpose |
|---|---|---|
| `company` | Link → Company | Company this connector belongs to |
| `bank_account` | Link → Bank Account | The bank account this connector handles (required, unique) |
| `bank` | Data (fetched) | Auto-filled from the linked Bank Account |
| `url` | Data | Base API URL provided by the bank |
| `api_key` | Data | API key / client ID |
| `api_secret` | Password | API secret / client secret (stored encrypted) |

---

### Service Subscriptions

Controls which features are active for this connector. Enable only services your bank API contract supports.

| Field | Purpose |
|---|---|
| `fetch_bank_balance` | Shows "Fetch Balance" button on Bank Account form; balance stored in `bank_balance` field |
| `fetch_bank_statement` | Shows "Fetch Statements" button on Bank Account form |
| `validate_bank_balance` | Before Payment Order submission, checks live balance ≥ total payment amount |
| `auto_post_payments` | Payments are processed automatically in the background scheduler |
| `create_payment_after_success` | Payment Entry is created only after a successful bank response (not on PO submit) |

---

### Payment Configuration

| Field | Purpose |
|---|---|
| `bulk_transaction` | Enable bulk/batch payment API (bank must support it) |
| `enqueue_large_payments_in_the_background` | If payment count exceeds threshold, queue them instead of processing inline |
| `enqueue_payments_threshold` | Number of payments above which background queuing kicks in |
| `enable_payment_delay` | Add a minimum delay between consecutive payment API calls |
| `payment_call_interval` | Seconds between payment calls (e.g. 10 = one call per 10 seconds) |

---

### Auto Update (Status)

| Field | Purpose |
|---|---|
| `auto_update_payment_status` | If off, user must manually fetch payment status from the bank |
| `status_check_at` | Which scheduler frequency to use for status checks (every 20 min / 1 hr / midnight) |
| `retry_period` | Days after payment initiation to keep checking status (e.g. 1 = check for 1 day) |
| `retry_interval_minutes` | Minutes between background retry attempts |
| `batch_size` | Max payments per batch in background processing |

---

### Reposting

| Field | Purpose |
|---|---|
| `auto_update_posting_date_as_payment_date` | If bank approval happens on a later date, updates the Payment Entry posting date to match the bank's payment date — keeps ledger and bank statement in sync |

---

### Notifications

| Field | Purpose |
|---|---|
| `notify_party` | Send payment notifications to the party (supplier/employee) |
| `payment_notification` | Table of notification rules — configure per payment type/status |

---

### DocType Configuration

| Field | Purpose |
|---|---|
| `doctype_naming_series` | Override naming series for Payment Entry and Payment Order created via this connector |

---

## Scheduler Integration

The connector drives all background tasks in `tasks.py`. Tasks loop over all saved connectors:

| Schedule | Task | Purpose |
|---|---|---|
| Every 1 minute | `process_payment_in_the_background` | Process queued payments for connectors with `auto_post_payments` enabled |
| Every 20 min / 1 hr / midnight | Status check | Fetch payment status updates from bank API based on `status_check_at` setting |
| Daily | `daily` | Fetch bank statements, update balances |

If no connector exists or `auto_post_payments` is off, the background tasks skip that connector silently.

---

## Key Files

| File | Purpose |
|---|---|
| `india_banking/india_banking/doctype/india_banking_connector/india_banking_connector.py` | Core connector class — API calls, payment initiation, status checks |
| `india_banking/tasks.py` | Scheduler tasks that loop over connectors |
| `india_banking/api.py` | Whitelisted API methods using connector (get_connected_bank_accounts, etc.) |
| `india_banking/india_banking/doc_events/bank_account/bank_account.py` | `get_data()` adds connector to Bank Account dashboard |
