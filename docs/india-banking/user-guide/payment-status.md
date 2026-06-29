# Tracking Payment Status

India Banking automatically polls the bank at configured intervals to update payment status — you don't need to manually check.

---

## How Auto Status Check Works

Based on the **Status Check Frequency** in India Banking Settings, a scheduled job runs and:

1. Finds all Payment Orders with at least one summary row in **Initiated** status
2. Calls the bank API for each order to check transaction status
3. Updates each row based on the bank's response

| Bank Response | India Banking Action |
|---|---|
| Processed / Success | UTR number recorded, Payment Entry updated, row marked **Processed** |
| Failed | Row marked **Failed**, Payment Entry cancelled |
| Pending / In-Progress | No change — will retry on next cycle |

---

## Checking Status Manually

You can trigger an immediate status check without waiting for the scheduler:

1. Open the submitted **Payment Order**
2. Click **Check Payment Status**

<!-- PLACEHOLDER: check-payment-status.gif
     Description: Screen recording showing a user clicking "Check Payment Status" on a Payment Order,
     a loading indicator appearing, and then the payment status column updating from "Initiated"
     to "Processed" with a UTR number appearing in the reference column.
     Suggested size: 900×450px, GIF duration ~5 seconds -->

---

## UTR Number

Once a payment is **Processed**, the bank's UTR (Unique Transaction Reference) number is stored on:
- The **Payment Order Summary** row (Reference No column)
- The linked **Payment Entry** (Reference No field)

The UTR is the primary proof of payment for audit and reconciliation purposes.

---

## Payment Summary Statuses

| Status | Description |
|---|---|
| **Pending** | Payment Entry created, payment not yet sent to bank |
| **Initiated** | Payment sent to bank, awaiting confirmation |
| **Processed** | Bank confirmed payment, UTR received |
| **Failed** | Bank rejected the payment |

---

## Retry Period

If a payment stays in **Initiated** status beyond the **Retry Period (in Days)** configured in Settings, the status check scheduler will stop polling for it. This prevents indefinite retries for stuck transactions.

---

## Payment Notification to Supplier

If **Notify Party** is enabled in Settings, India Banking sends an email (and/or SMS) to the supplier when their payment is processed, including the UTR number.

<!-- PLACEHOLDER: payment-notification-email.png
     Description: Sample email notification sent to a supplier showing the payment details:
     amount paid, UTR number, payment date, and company name.
     Suggested size: 600×400px -->

---

## Viewing All Payment Logs

Every API call made to the bank connector is recorded in **India Banking Request Log**.

**Go to:** India Banking > Logs > India Banking Request Log

Each log entry contains the full request and response payload, timestamp, and linked document. Logs are automatically deleted after the configured retention period.
