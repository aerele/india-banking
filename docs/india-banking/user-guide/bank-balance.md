# Fetching Bank Balance & Statements

India Banking lets you fetch your company's live bank balance and import bank statements directly from within ERPNext.

---

## Checking Bank Balance

### From Bank Account Form

1. Open the **Bank Account** for your company account
2. Click **Fetch > Bank Balance**

A popup displays the current available balance.

<!-- PLACEHOLDER: bank-balance-popup.png
     Description: Screenshot of the bank balance popup dialog showing:
     "Current Available Balance: ₹12,45,670.00" with a green indicator.
     Suggested size: 500×250px -->

### From Payment Order Form

If **Show Bank Balance in Payment Order** is enabled in Settings, the live balance is displayed directly on the Payment Order form next to the Company Bank Account field.

<!-- PLACEHOLDER: bank-balance-on-payment-order.png
     Description: Screenshot of the Payment Order form showing the Company Bank Account field
     with the balance displayed below it as "Balance: ₹12,45,670" in a green indicator,
     with a refresh icon next to it.
     Suggested size: 700×200px -->

Click the **refresh icon** to fetch the latest balance at any time.

---

## Fetching Bank Statements

Bank statements can be fetched and imported to create **Bank Transactions** in ERPNext for reconciliation.

### Step 1 — Open the Fetch Statements Dialog

1. Open the **Bank Account** form
2. Click **Fetch > Bank Statements**

### Step 2 — Set Date Range

| Field | Description |
|---|---|
| **From Date** | Start date for the statement period |
| **To Date** | End date for the statement period |

<!-- PLACEHOLDER: fetch-statements-dialog.png
     Description: Screenshot of the "Fetch Statements" dialog showing the Company, Bank Account
     (both read-only), From Date, and To Date fields.
     Suggested size: 600×400px -->

### Step 3 — Import

Click **Fetch**. India Banking calls the bank API and creates **Bank Transaction** records in ERPNext for each transaction in the date range.

> **Note:** Duplicate transactions (same reference number, date, and amount already in ERPNext) are automatically skipped.

---

## Using Bank Balance Validation

When **Enable Bank Balance Validation** is turned on in Settings, India Banking checks the live bank balance before allowing a Payment Order to be submitted. If the balance is insufficient, submission is blocked with an error message.

This acts as a real-time check — it does not account for pending/uncleared outgoing payments, so your actual available limit may be lower than the displayed balance in some cases.
