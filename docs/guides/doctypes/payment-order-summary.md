# Payment Order Summary

## Overview

Payment Order Summary is a child table of Payment Order. Each row represents one grouped payment — one outgoing bank transfer — after the references table has been summarised by party or voucher. It tracks the payment's status from pending through initiation, processing, and completion, and holds the bank account details snapshotted at the time of payment.

---

## Fields

| Field | Fieldname | Purpose |
|---|---|---|
| Party Type | `party_type` | Party type for this payment (Supplier, Employee, etc.) |
| Party | `party` | Party being paid |
| Party Name | `party_name` | Display name of the party |
| Bank Account | `bank_account` | Party's bank account receiving the payment |
| Account Name | `account_name` | Bank account holder name (snapshotted) |
| Bank Account No | `bank_account_no` | Account number (snapshotted) |
| Branch Code | `branch_code` | IFSC code (snapshotted) |
| Bank | `bank` | Bank name (snapshotted) |
| Amount | `amount` | Total amount for this grouped payment |
| Mode of Transfer | `mode_of_transfer` | Transfer rail assigned (NEFT, RTGS, IMPS, A2A) |
| Account | `account` | GL account for the payment |
| Cost Center | `cost_center` | Cost center dimension |
| Project | `project` | Project dimension |
| Tax Withholding Category | `tax_withholding_category` | TDS category if applicable |
| Reference Doctype | `reference_doctype` | Source doctype (Payment Request, Payment Entry, etc.) |
| Reference Name | `reference_name` | Source document name |
| Payment Status | `payment_status` | Current status: `Pending`, `Initiated`, `Processed`, `Failed` |
| Payment Entry | `payment_entry` | Linked Payment Entry created for this row |
| Payment Initiated | `payment_initiated` | Check — set when payment has been sent to the bank |
| Payment Date | `payment_date` | Date the payment was processed by the bank |
| Reference Number | `reference_number` | Bank's UTR / transaction reference number |
| Message | `message` | Bank API response message (success or failure detail) |
| Email | `email` | Override email for payment notification |
| Journal Entry Account | `journal_entry_account` | Journal Entry account reference (for JE type orders) |
| Summary References | `summary_references` | JSON list of Payment Order Reference row names grouped into this summary row |
| Create Payment Entry | `create_payment_entry` | Button — manually creates a Payment Entry for this row |

---

## Payment Status Flow

| Status | When Set |
|---|---|
| `Pending` | On Payment Order submit |
| `Initiated` | After payment is sent to the bank via the connector |
| `Processed` | After bank confirms successful credit |
| `Failed` | After bank returns a failure response, or manually via Cancel Pending Payments |

---

## Summary References

`summary_references` stores a JSON-serialised list of `Payment Order Reference` row names that were collapsed into this summary row. This is used during Payment Entry creation to find and allocate against each individual source invoice.

---

## Bank Detail Snapshot

When a Payment Order is submitted, the party's bank account details (`account_name`, `bank_account_no`, `branch_code`, `bank`) are snapshotted onto the summary row. This ensures the payment record reflects the details at the time of initiation, even if the Bank Account is later edited.

---

## Key Files

| File | Purpose |
|---|---|
| `india_banking/india_banking/doctype/payment_order_summary/payment_order_summary.json` | Field definitions |
| `india_banking/overrides/payment_order.py` (`validate_summary`, `get_party_summary`) | Summary generation and validation |
| `india_banking/india_banking/doc_events/payment_order.py` (`make_payment_entries`) | Creates Payment Entries from summary rows |
| `india_banking/india_banking/doctype/india_banking_connector/india_banking_connector.py` | Updates `payment_status`, `reference_number`, `message`, `payment_date` after bank response |
| `india_banking/india_banking/doc_events/payment_order.py` (`cancel_pending_payments`) | Marks failed rows and cancels their Payment Entries |
