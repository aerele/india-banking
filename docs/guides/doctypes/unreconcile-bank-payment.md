# Unreconcile Bank Payment

## Overview

Unreconcile Bank Payment is a submittable doctype that selectively removes reference rows from a submitted Payment Order without cancelling the entire order. It also reverses the downstream effects — unreconciling the linked Payment Entry allocations and cancelling any linked Payment Requests — leaving the Payment Order intact with the remaining references.

It is triggered from the **Unlink Allocation** button on a submitted Payment Order.

---

## Fields

| Field | Purpose |
|---|---|
| Company | Company of the Payment Order being unlinked |
| Voucher Type | Always `Payment Order` (the only supported type) |
| Voucher No | The specific Payment Order to unlink from |
| Allocations | Child table — rows selected for removal (see below) |

### Allocations child table (`Bank Payment Allocation`)

| Field | Purpose |
|---|---|
| Party Type | Party type of the reference row |
| Party | Party name |
| Reference Type | Source doctype of the reference (e.g. Purchase Invoice) |
| Reference Name | Source document name |
| Amount | Amount of the reference row |
| Account | GL account |
| Payment Request | Linked Payment Request, if any |

---

## How to Use

1. Open the submitted Payment Order
2. Click **Unlink Allocation**
3. A dialog shows all current reference rows — select the ones to remove
4. Click **Submit** — an Unreconcile Bank Payment document is created and submitted automatically

Alternatively, create the document manually: set Company, Voucher Type = `Payment Order`, Voucher No, then click **Get Allocations** to populate the child table, select rows, save and submit.

---

## What Happens on Submit

For each selected allocation row, in order:

1. **Deletes the Payment Order Reference row** — removes the entry from `tabPayment Order Reference` matching the Payment Order, reference doctype, and reference name

2. **Unreconciles the Payment Entry** — finds the submitted Payment Entry linked to this Payment Order for the same party, then calls ERPNext's `create_unreconcile_doc_for_selection` to reverse its allocations against the source invoice/order

3. **Cancels the Payment Request** (if present) — cancels the linked Payment Request and adds a comment recording which voucher was unlinked and from which Payment Order

4. **Adds a comment to the Payment Order** — logs all unlinked vouchers with amounts for audit trail

---

## Validations

| Rule | Detail |
|---|---|
| Voucher Type must be Payment Order | Only Payment Orders are supported |
| Allocations must not be empty | At least one row required before submission |
| Cancel permission required | If a Payment Request is linked, the user must have cancel permission on it — throws otherwise |

---

## Key Files

| File | Purpose |
|---|---|
| `india_banking/india_banking/doctype/unreconcile_bank_payment/unreconcile_bank_payment.py` | All submit logic — deletion, unreconciliation, PR cancellation, comments |
| `india_banking/india_banking/doctype/unreconcile_bank_payment/unreconcile_bank_payment.js` | Form UI: voucher filters, Get Allocations button |
| `india_banking/public/js/payment_order.js` (`set_unlink_vouchers_button`) | Unlink Allocation button and dialog on the Payment Order form |
