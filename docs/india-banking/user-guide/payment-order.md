# Payment Order

A **Payment Order** batches one or more Payment Requests (or Payment Entries / Journal Entries) into a single bank instruction. It is the document you submit to send payments to the bank.

---

## Creating a Payment Order

### Method 1 — From a Payment Request

1. Open a submitted **Payment Request**
2. Click **Create > Payment Order**

The Payment Order is created with the Payment Request pre-loaded in the references table.

### Method 2 — From the Payment Order List

1. Go to **India Banking > Payment Order > New**
2. Fill in **Company** and **Company Bank Account**
3. Click **Get Payments from** to pull in Payment Requests, Payment Entries, or Journal Entries

<!-- PLACEHOLDER: payment-order-get-payments.gif
     Description: Screen recording showing a user on a new Payment Order form, selecting the
     Company Bank Account, then clicking "Get Payments from > Payment Request", and a dialog
     appearing to filter and select payment requests to add.
     Suggested size: 900×500px, GIF duration ~6 seconds -->

---

## Understanding the Payment Order Form

### Header Fields

| Field | Description |
|---|---|
| **Company** | The company initiating the payment |
| **Company Bank Account** | The bank account from which payment is made |
| **Company Account No / IFSC** | Auto-filled from the bank account |
| **Payment Order Type** | Payment Request / Payment Entry / Journal Entry / Payroll Entry |
| **Default Mode of Transfer** | Applied to all rows that don't have an individual mode set |
| **Summarise Payment Based On** | Party (one row per supplier) or Voucher (one row per invoice) |
| **Bank Balance** | Live balance shown if enabled in Settings |

### References Table

Lists each individual payment — one row per Payment Request / Entry / Journal Entry Account. These rows drive the accounting entries.

### Summary Table

Grouped rows after clicking **Get Summary**. One row per payment batch (per party or per voucher depending on settings). This is what goes to the bank.

| Column | Description |
|---|---|
| **Party / Party Name** | Supplier or Employee being paid |
| **Bank Account No / IFSC** | Payee's bank details |
| **Amount** | Total amount for this batch |
| **Mode of Transfer** | NEFT / RTGS / IMPS / A2A — auto-assigned or manually set |
| **Payment Status** | Pending → Initiated → Processed / Failed |

---

## Generating the Summary

Click **Get Summary** to group the references and auto-assign Modes of Transfer.

<!-- PLACEHOLDER: payment-order-summary.png
     Description: Screenshot of the Payment Order summary table after clicking "Get Summary",
     showing multiple supplier rows with auto-assigned Mode of Transfer (NEFT/RTGS/IMPS)
     based on the payment amounts.
     Suggested size: 900×450px -->

India Banking assigns modes automatically:
- Same-bank transfers → A2A/FT/Internal (priority 1)
- ₹1–₹2,00,000 → IMPS
- ₹2,00,000+ → RTGS

You can manually override any row's Mode of Transfer.

---

## Validations on Submit

India Banking runs these checks before allowing submission:

| Validation | Condition |
|---|---|
| Summary must exist | At least one row in the summary table |
| Amounts must match | Summary total = References total |
| Mode of Transfer amounts | Each payment amount within the mode's min–max limits |
| A2A transfers | Party bank must be same as company bank |
| RTGS > ₹50 Cr | LEI Number must be set on the Supplier |
| Bank balance | Sufficient balance (if validation is enabled in Settings) |
| Payment Request amounts | Grand Total on the linked Payment Request must match the reference amount |

---

## What Happens on Submit

1. A **Payment Entry** is created for each summary row (accounting entry in ERPNext)
2. Payment Order status is set to **Pending**
3. Linked Payment Requests are marked as **Payment Ordered**

The payments are **not yet sent to the bank**. The next step is to initiate the payment.

---

## Payment Order Statuses

| Status | Meaning |
|---|---|
| Pending | Submitted but bank payment not yet initiated |
| Initiated | Payment sent to bank, awaiting confirmation |
| Processed | All payments confirmed by bank with UTR numbers |
| Failed | One or more payments failed at the bank |
