# Payment Request

A **Payment Request** represents a request to pay a specific amount to a supplier or employee. In India Banking, the standard ERPNext Payment Request is enhanced with:

- TDS (Tax Deducted at Source) calculation
- GST payable hold for suppliers with pending GST liabilities
- Bank account approval gate
- Ad-hoc payment support (without a reference document)

---

## Creating a Payment Request from a Purchase Order or Invoice

### Step 1 — Open the Source Document

Navigate to your **Purchase Order** or **Purchase Invoice** and ensure it is submitted.

### Step 2 — Click "Make Payment Request"

In the document form, click:

**Create > Payment Request**

<!-- PLACEHOLDER: create-payment-request.gif
     Description: Screen recording of a user opening a submitted Purchase Invoice,
     clicking "Create > Payment Request", and the Payment Request form opening pre-filled
     with the supplier, amount, and reference details.
     Suggested size: 900×500px, GIF duration ~5 seconds -->

### Step 3 — Fill in Payment Details

| Field | Description |
|---|---|
| **Payment Request Type** | Set to **Outward** for supplier payments |
| **Party Type / Party** | Auto-filled from the source document |
| **Payment Type** | Select the payment category (auto-assigned if a default is configured) |
| **Bank Account** | Supplier's bank account (auto-assigned if a default is set on the supplier) |
| **Net Total** | Amount to pay — can be less than the invoice total for partial payments |
| **Apply Tax Withholding Amount** | Check this to deduct TDS; set the **Tax Withholding Category** |
| **Taxes Deducted** | Auto-calculated TDS amount |
| **Grand Total** | Net Total minus Taxes Deducted — this is the actual amount that will be transferred |
| **Remarks** | Payment narration sent to the bank (max 48 characters) |
| **Payment Term** | Optional — link to a specific payment term for tracking |

<!-- PLACEHOLDER: payment-request-form.png
     Description: Screenshot of a Payment Request form showing the Net Total, TDS fields,
     Grand Total, Payment Type, and Bank Account fields filled in.
     Suggested size: 900×650px -->

---

## TDS Deduction

When **Apply Tax Withholding Amount** is checked:

1. Select the **Tax Withholding Category** (e.g., 194C for contractors, 194J for professionals)
2. India Banking automatically calculates the TDS amount based on ERPNext's tax withholding rules
3. **Grand Total = Net Total − TDS**

Only the Grand Total is transferred to the supplier. The TDS amount remains in the TDS Payable account for remittance to the government.

---

## GST Payable Hold

If a supplier has **Hold GST Payables** enabled on their record, India Banking will:

1. Calculate the outstanding GST amount on the linked invoice
2. Deduct it from the eligible payment amount
3. Block payment if the full amount equals only GST (i.e., nothing payable after GST hold)

> **To pay GST separately**, use the **Bank GST Payables** report.

---

## Ad-hoc Payments

An **ad-hoc payment** is a payment not linked to any Purchase Order or Invoice — for example, an advance or a one-off expense.

To create one:
1. Go to **India Banking > Payment Request > New**
2. Check **Is Ad-hoc**
3. Fill in Party Type, Party, Bank Account, and Amount
4. **Do not** fill Reference Doctype or Reference Name

> Ad-hoc payments skip the reference amount validation and go directly to Initiated status on submit.

---

## Submitting the Payment Request

After review, click **Submit**. India Banking validates:

- Bank account is present and (if workflow is on) **Approved**
- Bank account currency matches the payment currency
- Bank account belongs to the selected party
- Amount is not zero

On successful submit, the Payment Request status becomes **Initiated** (for ad-hoc) or remains ready to be added to a Payment Order.

---

## Payment Request Statuses

| Status | Meaning |
|---|---|
| Draft | Created but not yet submitted |
| Initiated | Submitted and awaiting a Payment Order |
| Payment Ordered | Added to a submitted Payment Order |
| Partially Paid | Part of the amount has been processed |
| Paid | Fully processed and payment entry created |
| Cancelled | Cancelled before processing |
