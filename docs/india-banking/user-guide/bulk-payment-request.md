# Bulk Payment Requests from Purchase Invoices

India Banking adds a **Payment Request** action to the Purchase Invoice list view, allowing you to create Payment Requests for multiple invoices in a single click.

---

## Creating Bulk Payment Requests

### Step 1 — Go to the Purchase Invoice List

**Go to:** Accounts > Payables > Purchase Invoice

### Step 2 — Select Submitted Invoices

Check the boxes next to the invoices you want to pay. Only **submitted** invoices with an outstanding balance will be processed.

<!-- PLACEHOLDER: purchase-invoice-list-select.png
     Description: Screenshot of the Purchase Invoice list view with three invoices checked,
     showing the "Actions" dropdown menu open and the "Payment Request" option highlighted.
     Suggested size: 1000×450px -->

### Step 3 — Click Actions > Payment Request

A confirmation dialog appears:

> *"Create 3 Payment Request(s)?"*

Click **Yes** to proceed.

<!-- PLACEHOLDER: bulk-payment-request-confirm.png
     Description: Screenshot of the confirmation dialog showing the count of invoices selected
     and a Yes/No button pair.
     Suggested size: 500×250px -->

### Step 4 — Result

India Banking creates one **Payment Request** per invoice. Invoices that are already fully covered by existing Payment Requests are skipped automatically.

A success message shows how many Payment Requests were created.

---

## How It Works

For each selected invoice:
1. India Banking calculates the outstanding amount minus any existing unpaid Payment Requests
2. If the remaining payable amount > 0, a new Payment Request is created
3. If nothing is payable, the invoice is skipped silently

---

## After Bulk Creation

All created Payment Requests appear in the **Payment Request** list. From there you can:
- Review and submit them individually
- Add them to a Payment Order for bulk bank payment

**Go to:** India Banking > Payment Request

<!-- PLACEHOLDER: payment-request-list-after-bulk.png
     Description: Screenshot of the Payment Request list view showing multiple newly created
     draft payment requests with status "Draft" and the supplier names from the invoices.
     Suggested size: 1000×350px -->

---

## Notes

- Only invoices in **Submitted** state are valid for selection. Draft invoices in the selection are ignored.
- The Payment Request amount is the invoice's outstanding amount minus any existing submitted Payment Requests for the same invoice.
- Each Payment Request inherits the supplier, party bank account, and payment type defaults from Settings.
