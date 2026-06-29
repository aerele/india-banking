# Initiating a Bank Payment

After a Payment Order is submitted, you initiate the actual bank transfer using the **Make Bank Payment** button. This sends payment instructions to your bank via the API.

---

## Individual Payments (HDFC, Kotak, Union Bank, Bank of Baroda)

For banks that process individual transactions:

1. Open the submitted **Payment Order**
2. Click **Make Bank Payment**

India Banking sends a separate API request for each row in the summary that is in **Pending** status.

<!-- PLACEHOLDER: make-bank-payment-button.png
     Description: Screenshot of a submitted Payment Order form showing the "Make Bank Payment"
     button in the top action bar, with the payment status column showing "Pending" for all rows.
     Suggested size: 900×400px -->

Each row is processed independently:
- **Success** → Row status changes to **Initiated**, UTR/reference number recorded once bank confirms
- **Failure** → Row status changes to **Failed**, the Payment Entry is cancelled automatically

---

## Bulk Payments (ICICI, IDFC First, Axis, Canara)

Banks with bulk transaction mode use a **file-based OTP flow**:

### Step 1 — Generate OTP

Click **Get OTP**. India Banking sends an OTP request to the bank. The OTP is delivered to the registered mobile number of the bank account's authorised signatory.

<!-- PLACEHOLDER: get-otp-dialog.png
     Description: Screenshot of the OTP input dialog that appears after clicking "Get OTP",
     showing a text field for entering the 6-digit OTP received from the bank.
     Suggested size: 500×300px -->

### Step 2 — Enter OTP and Initiate

Enter the OTP in the dialog and click **Make Bank Payment**.

India Banking packages all pending payment rows into a file and sends it to the bank API in one call.

- **ACCEPTED** → All rows move to **Initiated** status. The bank's file sequence number is stored on the Payment Order.
- **Failed** → An error message is returned. No status changes occur.

<!-- PLACEHOLDER: bulk-payment-otp-flow.gif
     Description: Screen recording of the entire OTP flow: user clicking "Get OTP",
     entering the OTP in the dialog, clicking "Make Bank Payment", and watching the
     payment status column update from "Pending" to "Initiated" for all rows.
     Suggested size: 900×500px, GIF duration ~8 seconds -->

---

## Background Processing

If **Process Payments in Background** is enabled in India Banking Settings, clicking **Make Bank Payment** queues the job instead of running it synchronously. This prevents browser timeouts for large payment batches.

A notification appears when the job completes.

---

## After Initiation

Once payments are initiated, the Payment Order status becomes **Initiated**. The final UTR numbers and **Processed** status are updated automatically by the scheduled status check job — no manual action required.

See [Tracking Payment Status](payment-status.md) for details.

---

## Cancellation Rules

| Condition | Result |
|---|---|
| All rows Pending | Payment Order can be cancelled |
| Any row Initiated or Processed | Cancellation is **blocked** |

> You cannot cancel a Payment Order that has been sent to the bank. Contact your bank to reverse an erroneous payment.
