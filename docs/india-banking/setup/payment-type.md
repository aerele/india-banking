# Payment Type

A **Payment Type** maps a payment category to a specific accounting (debit) account. It allows you to route payments through different accounts depending on the nature of the payment — for example, separating vendor payments from salary payments in your books.

---

## Creating a Payment Type

**Go to:** India Banking > Setup > Payment Type > New

| Field | Description |
|---|---|
| **Payment Type** | A descriptive name (e.g., "Vendor Payments", "Employee Salary") |
| **Company** | The company this Payment Type applies to |
| **Account** | The GL account to be debited when this payment type is used |
| **Is Default** | If checked, this Payment Type is automatically assigned to new Payment Requests for this company |

<!-- PLACEHOLDER: payment-type-form.png
     Description: Screenshot of a Payment Type form with fields filled in:
     Payment Type = "Vendor Payments", Company = "Aerele Technologies", Account = "Accounts Payable - AT", Is Default checked.
     Suggested size: 800×400px -->

---

## How Payment Type is Used

1. **On Payment Request** — The Payment Type determines which GL account is debited when the payment entry is created. If only one Payment Type exists for the company and it is set as default, it is automatically selected.
2. **On Payment Entry creation** — The `paid_to` account on the Payment Entry is set from the Payment Type's Account field.

---

## Example Setup

For a company with two payment streams:

| Payment Type | Account | Is Default |
|---|---|---|
| Vendor Payments | Accounts Payable - AT | ✓ |
| Employee Expense Reimbursements | Employee Payables - AT | |
| TDS Payable | TDS Payable - AT | |

> **Tip:** Set the most commonly used Payment Type as **Is Default** so it is pre-selected on every new Payment Request, reducing manual selection.
