# App Architecture

## Overview

`india_banking` extends ERPNext's payment flow with Indian bank-specific logic: bulk payment orders, bank connector integrations (ICICI, HDFC, Axis, etc.), GST-aware payment processing, and a Payment Order → Payment Entry lifecycle.

## Layer Map

```
Frontend (JS)                  Backend (Python)
─────────────────              ────────────────────────────────────────
bank_account.js           →    doc_events/bank_account/bank_account.py
payment_request.js        →    overrides/payment_request/payment_request.py
                               doc_events/payment_request/payment_request.py
payment_order.js          →    overrides/payment_order.py
                               doc_events/payment_order.py
payment_entry.js          →    overrides/payment_entry.py
                               doc_events/payment_entry.py
                          →    overrides/journal_entry.py
```

## Key Design Patterns

### 1. Override Class vs Doc Event

| Pattern | File Location | Use When |
|---|---|---|
| `override_doctype_class` | `overrides/` | Need to override `on_submit`, `on_cancel`, add methods to the class |
| `doc_events` | `india_banking/doc_events/` | Simple hooks (validate, before_save) that don't need parent class access |

**Registered in:** `india_banking/hooks.py`

### 2. Payment Flow

```
Purchase Invoice
      ↓ (bulk or single)
Payment Request  ──→  make_payment_order()
      ↓
Payment Order  ──→  (bank connector initiates payment)
      ↓
Payment Order Summary  ──→  (per-party grouping)
      ↓
Payment Entry  ──→  (created after success or immediately)
```

### 3. Bank Connector

Each bank has an `India Banking Connector` document. The connector:
- Stores credentials and API config
- Exposes `get_bank_balance()`, `initiate_payment()`, `get_payment_status()`
- Called from `tasks.py` on a schedule (every 1 min for background, every 20 min for status)

### 4. Settings Gate

Almost all conditional behavior is gated by `India Banking Settings` (singleton):
- `allow_future_date_payment_order`
- `enable_bank_account_workflow`
- `enable_unique_account_no`
- `create_payment_after_success`
- `hold_gst_payables`
- `restrict_journal_entry_without_bank_account`

Always read via `frappe.get_single("India Banking Settings")`.

## Custom Doctypes

| Doctype | Purpose |
|---|---|
| India Banking Connector | Bank API credentials and config |
| India Banking Settings | Global feature toggles |
| India Banking Request Log | API call audit trail |
| Payment Order Summary | Per-party grouping within a Payment Order |
| Mode of Transfer | IMPS/NEFT/RTGS limits and timings |
| Bank Payment Allocation | Payment-to-invoice matching |
| Unreconcile Bank Payment | Reverse a reconciled payment |
| Payment Notification | Notification rules per party |
| Field Map / Naming Series Map / Party Bank Account Field Map | Configuration tables |
