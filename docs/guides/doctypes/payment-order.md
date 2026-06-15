# Payment Order

## Overview

Payment Order is an ERPNext doctype that groups multiple outgoing payments into a single batch for bank processing. `india_banking` extends it to support Indian bank integrations — pulling payments from Payment Requests, Payment Entries, or Journal Entries, summarising them by party or voucher, validating bank-specific transfer modes, and initiating bulk payments through an India Banking Connector.

---

## Pulling Payments into a Payment Order

The **Get Payments from** menu appears on draft Payment Orders. Which source types appear depends on **India Banking Settings → Allowed Payment Doctypes**. Only doctypes listed there are shown as options.

Once a source type is used on a Payment Order, only that same source type can be added again (the `payment_order_type` field locks after the first pull).

### Payment Request

Filters that a Payment Request must satisfy to appear in the picker:

| Filter | Required Value |
|---|---|
| `docstatus` | `1` (Submitted) |
| `status` | `Initiated` |
| `company` | Matches the Payment Order's company |
| `bank` | Matches the Payment Order's bank |
| `transaction_date` | On or before the date allowed by India Banking Settings |
| `name` | Not already present in the Payment Order's references table |

### Payment Entry

Filters that a Payment Entry must satisfy to appear in the picker:

| Filter | Required Value |
|---|---|
| `docstatus` | `1` (Submitted) |
| `payment_type` | `Pay` |
| `mode_of_payment` | `Wire Transfer` |
| `bank_account` | Matches the Payment Order's company bank account |
| `source_doctype` | Not `Payment Request` (or not set) |
| `name` | Not already referenced in any active Payment Order |
| `name` | Not already present in the Payment Order's references table |

### Journal Entry (Bank Entry)

Filters that a Journal Entry must satisfy to appear in the picker:

| Filter | Required Value |
|---|---|
| `docstatus` | `1` (Submitted) |
| `voucher_type` | `Bank Entry` |
| `jea.payment_status` | Not `Paid`, `Ordered`, or `Payment Ordered` (NULL/empty also eligible) |
| `jea.against_account` | Matches the Payment Order's `account` field (company GL account) — applied only when the field is set |
| `company` | Matches the company selected in the picker dialog (when set) |
| `name` | Not already present in the Payment Order's references table |

**Journal Entry Account line requirements** — for a line to be mapped into the Payment Order reference, it must additionally satisfy:

| Condition | Required Value |
|---|---|
| `debit` | `> 0` (the party/creditor line must be on the debit side) |
| `party_type` | Set (e.g. Supplier, Employee) |
| `party` | Set |
| `bank_account` | Set (party's bank account for payment) |
| `payment_status` | Not `Paid`, `Ordered`, or `Payment Ordered` |

**Correct Bank Entry structure for outgoing payment:**

| Line | Account | Debit | Credit | Party | Bank Account |
|---|---|---|---|---|---|
| 1 | Creditors / Party account | > 0 | 0 | required | required |
| 2 | Company bank GL account | 0 | > 0 | — | — |

If the party line has `debit = 0` (reversed structure — a receipt entry), the JE will appear in the picker but no references will be created when mapped.

---

## Summary

After pulling references, clicking **Validate** generates the **Summary** table. Each row in the summary represents a unique payment grouping.

**Grouped by** is controlled by **India Banking Settings → Summarize Payments By**:

- **Party** — all references for the same party are combined into one summary row
- **Voucher** — each source document gets its own summary row

Each summary row carries: party, party type, bank account, amount, mode of transfer, and any active accounting dimensions.

---

## Mode of Transfer

Each summary row requires a Mode of Transfer. The system assigns one automatically based on amount and bank:

- If the party's bank is the **same** as the company's bank → assigns an A2A/FT/Internal mode
- Otherwise → picks the mode whose `minimum_limit ≤ amount ≤ maximum_limit` with the lowest priority, falling back to the Payment Order's default mode of transfer

Validations on submit:
- Amount must be within the mode's configured limits
- NEFT/RTGS payments above ₹50 Cr require a valid LEI number on the party
- A2A mode is only valid when the party's bank matches the company bank

---

## Submission

On submit, `india_banking` runs the following checks before accepting:

1. **Future date** — blocked unless **India Banking Settings → Allow Future Date Payment Order** is enabled
2. **Bank balance** — if the linked India Banking Connector has `validate_bank_balance` on, the company account balance must cover the total
3. **Amount match** — for Payment Request type orders, each reference amount must match the Payment Request's `grand_total`
4. **Summary integrity** — the sum of all summary rows must equal the sum of all reference rows

On successful submit, referenced documents are updated:

| Source Type | Field Updated | New Value |
|---|---|---|
| Payment Request | `status` | `Payment Ordered` |
| Payment Entry | `payment_order_status` | `Payment Ordered` |
| Journal Entry | `payment_status` | `Payment Ordered` |

---

## Payment Entry Creation

For Payment Request type orders where the connector does **not** have `create_payment_after_success` enabled, Payment Entries are created immediately on submit — one per summary row.

Each Payment Entry:
- Uses the summary row's party, bank account, and amount
- Allocates against the source invoices; respects payment terms if a template is configured on the invoice
- Posting date defaults to today unless **India Banking Settings → Use Payment Order Date for Payment Entry** is enabled

---

## Payment Initiation

After submission, a **Payment Manager** role user can click **Initiate Payment** to send the batch to the bank via the India Banking Connector.

If the bank requires OTP confirmation, a prompt appears to enter the OTP before the payment is processed.

Once initiated, the **Get Status** button appears to poll the bank for individual payment outcomes. Each summary row's `payment_status` updates to `Initiated`, `Processed`, or `Failed`.

---

## Cancellation

A Payment Order cannot be cancelled if any summary row has `payment_status` of `Initiated` or `Processed`. Cancel only when all payments are in `Pending` or `Failed` state.

On cancel, referenced Payment Requests revert to `Initiated` status.

---

## Key Files

| File | Purpose |
|---|---|
| `india_banking/overrides/payment_order.py` | Core overrides: validation, summary generation, mode of transfer logic |
| `india_banking/india_banking/doc_events/payment_order.py` | Payment Entry creation from summary rows |
| `india_banking/public/js/payment_order.js` | Form UI: pull buttons, summary validation, payment initiation |
| `india_banking/overrides/payment_entry.py` | `get_payment_entry` — server-side filter query for the Payment Entry picker |
| `india_banking/overrides/payment_request/payment_request.py` | `make_payment_order` — maps a Payment Request into a Payment Order reference |
