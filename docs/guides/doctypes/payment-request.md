# Payment Request

## Overview

Payment Request is an ERPNext doctype that records an outgoing payment request against a source document (Purchase Invoice, Purchase Order, etc.). `india_banking` extends it with Indian banking requirements: default bank account resolution, `net_total` separation from `grand_total` for GST handling, bank account validation against the approval workflow, currency enforcement, party account checks, and bulk payment support via Payment Order.

> **Deprecation notice:** The Adhoc Payment Request feature is deprecated. The recommended flow is to create a Payment Entry directly and pull it into a Payment Order. Payment Request is retained for Payment Order-based bulk payment flows only.

---

## Default Values on Validate

`set_default_value()` runs on every validate and fills in missing fields:

| Field | Auto-set to |
|---|---|
| `net_total` | `grand_total` if `net_total` is not set |
| `transaction_date` | Today's date if not set |
| `bank_account` | Party's default active bank account (`is_default=1, disabled=0`) if not set |
| `mode_of_payment` | `Wire Transfer` whenever `bank_account` is present |

`grand_total` is also overridden with `net_total` during validate — ensuring the amount used downstream in Payment Entry creation reflects the net payable after any GST exclusion.

---

## GST Payables Handling

Applies only when `india_compliance` is installed and the supplier has `hold_gst_payables` enabled.

### On Insert (`before_insert`)

Deducts GST components (IGST + CGST + SGST) from the payment amount and sets `net_total` to the GST-exclusive amount. Throws if the resulting payable amount is zero or negative, directing the user to the **Bank GST Payables** report to process GST separately.

### On Submit (`before_submit`)

Re-validates the GST payable position at submit time. Throws if the requested amount exceeds the eligible (GST-exclusive) outstanding.

### Amount Calculation

```
GST payable = sum of IGST + CGST + SGST from the source document's item rows
Net payable  = outstanding amount − existing payment requests − GST payable
```

For Purchase Invoice the outstanding amount is `outstanding_amount`; for Purchase Order it is `base_grand_total − advance_paid`.

---

## Validations on Submit

### `validate_bank_account()`

Runs on `on_submit`. Checks in order:

1. `bank_account` must be set — falls back to the party's default bank account; throws if none exists
2. If **India Banking Settings → Enable Bank Account Approval Workflow** is on, the bank account's `workflow_state` must be `Approved`
3. The bank account's `currency` must match the Payment Request's `currency`
4. If the bank account has a `party_type` and `party` set, they must match the Payment Request's `party_type` and `party`

### `validate_party_account()`

Runs on `on_submit`. Confirms that an accounting GL account exists for the party in the company. Throws if none is found.

### Amount check

`grand_total` and `net_total` must both be non-zero on submit.

---

## Remarks Truncation

`remarks` is trimmed to 48 characters on validate. Most Indian bank APIs have a strict character limit on the payment narration field — exceeding it causes API rejection.

---

## Bank Account Field Query (Form UI)

The `bank_account` field on the form is filtered to show only relevant accounts:

| Condition | Value |
|---|---|
| `disabled` | `0` |
| `party_type` | Matches the Payment Request's `party_type` (when set) |
| `party` | Matches the Payment Request's `party` (when set) |
| `workflow_state` | `Approved` — only when **India Banking Settings → Enable Bank Account Approval Workflow** is on |

---

## Status Flow

| Status | Meaning |
|---|---|
| `Initiated` | Submitted, ready to be pulled into a Payment Order |
| `Payment Ordered` | Pulled into a submitted Payment Order |
| `Partially Paid` | One or more payments processed but not fully settled |
| `Paid` | Fully settled |

When a Payment Order is cancelled, referenced Payment Requests revert to `Initiated`.

The List View adds a `Payment Ordered` indicator in blue to make this status visible in the list.

---

## Pulling into a Payment Order

A submitted Payment Request with `status = Initiated` can be pulled into a Payment Order via **Get Payments from → Payment Request**. See the [Payment Order guide](payment-order.md#payment-request) for the full filter set that must match.

`make_payment_order()` maps the Payment Request into a Payment Order reference row, carrying: reference doctype/name, amount (`grand_total`), party type/party, bank account, mode of payment, GL account, cost center, project, and all active accounting dimensions.

---

## Key Files

| File | Purpose |
|---|---|
| `india_banking/overrides/payment_request/payment_request.py` | `BankPaymentRequest` class — all validations, GST handling, default values |
| `india_banking/public/js/payment_request.js` | Form UI: bank account field query, Payment Order list button |
| `india_banking/public/js/payment_request_list.js` | List view: `Payment Ordered` status indicator, deprecation banner |
