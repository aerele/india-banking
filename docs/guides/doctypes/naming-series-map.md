# Naming Series Map

## Overview

Naming Series Map is a child doctype that maps a company to a custom naming series for a specific payment doctype (Payment Request, Payment Order, or Payment Entry). It is stored as a child table on the **India Banking Connector** and allows different companies on the same ERPNext instance to use distinct naming prefixes for bank payment documents.

---

## Fields

| Field | Fieldname | Purpose |
|---|---|---|
| DocType | `doctype_name` | The doctype this series applies to — `Payment Request`, `Payment Order`, or `Payment Entry` |
| Series | `series` | The naming series string (e.g. `BANK-PAY-.YYYY.-.####`) |
| Company | `company` | The company this series applies to |

The `doctype_name` field is filtered to only allow `Payment Request`, `Payment Order`, and `Payment Entry`.

---

## How It Works

`update_series()` in `india_banking/utils.py` is hooked into the `autoname` event of Payment Order. It:

1. Looks up `Naming Series Map` for a row matching `company` and `doctype_name`
2. If a matching series is found and it differs from the document's current `naming_series`, it updates the series and shows an alert
3. Payment Requests and Payment Entries are also covered — Payment Entry naming is applied during `make_payment_entries()` in the payment order flow

**Scope filters in `update_series()`:**
- For **Payment Request** — only applies if `payment_request_type == "Outward"`
- For **Payment Entry** — only applies if `payment_type == "Pay"`

---

## Configuration

Naming Series Map rows are added on the **India Banking Connector** form under the **Naming Series** section (field: `doctype_naming_series`). Add one row per company–doctype combination that needs a custom series.

---

## Key Files

| File | Purpose |
|---|---|
| `india_banking/india_banking/doctype/naming_series_map/naming_series_map.json` | Field definitions |
| `india_banking/utils.py` (`get_bank_payment_naming_series`, `update_series`) | Lookup and apply logic |
| `india_banking/hooks.py` | `autoname` hook wiring `update_series` to Payment Order |
| `india_banking/india_banking/doc_events/payment_order.py` | Applies series to Payment Entries created from a Payment Order |
| `india_banking/india_banking/doctype/india_banking_settings/india_banking_settings.js` | Filters `doctype_name` field to the three supported doctypes |
