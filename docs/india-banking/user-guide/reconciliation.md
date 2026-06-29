# Reconciliation & Unreconcile

India Banking integrates with ERPNext's standard Bank Reconciliation workflow. Once bank statements are imported, you can match them against Payment Entries created by Payment Orders.

---

## Reconciliation Flow

```
Bank Statement Imported (Bank Transactions)
        ↓
Match with Payment Entries (ERPNext Reconciliation Tool)
        ↓
Bank Transaction Reconciled
```

**Go to:** Accounting > Banking > Bank Reconciliation Tool

<!-- PLACEHOLDER: bank-reconciliation-tool.png
     Description: Screenshot of the Bank Reconciliation Tool showing matched and unmatched
     bank transactions on the left, and suggested Payment Entry matches on the right.
     Suggested size: 1100×500px -->

---

## Auto-Matching

ERPNext's reconciliation tool can automatically match bank transactions to Payment Entries using:
- **Amount** match
- **Reference Number** (UTR) match

Since India Banking stores the UTR on Payment Entries, auto-matching by reference number is highly accurate for bank-initiated transactions.

---

## Unreconciling a Payment

If a reconciled transaction needs to be reversed (e.g., an incorrectly matched entry), use the **Unreconcile Payment** document.

**Go to:** Accounting > Banking > Unreconcile Payment > New

When you submit an Unreconcile Payment document:

1. India Banking detects if the reversed Payment Entry was created through a Payment Order
2. If yes, it finds the corresponding **Payment Order Summary** row
3. It resets the summary row's payment status and clears the reference number

This allows the payment to be re-initiated if needed.

<!-- PLACEHOLDER: unreconcile-payment.png
     Description: Screenshot of the Unreconcile Payment form showing the voucher type (Payment Entry),
     the voucher number, and the allocation entries to be reversed.
     Suggested size: 900×500px -->

---

## What Gets Reset on Unreconcile

| Document | What Changes |
|---|---|
| Bank Transaction | Unlinked from Payment Entry |
| Payment Entry | Unreconciled |
| Payment Order Summary | Payment status and reference number cleared |

> **Note:** Unreconciling does not cancel the Payment Entry or reverse the accounting entry. It only removes the reconciliation link and resets the tracking status in India Banking.

---

## Tips

- Always reconcile using the **UTR number** when available — it gives a 1:1 match with zero ambiguity
- If a bank transaction has no matching Payment Entry (e.g., bank charges, interest), create a Journal Entry and reconcile manually
- Run the **Bank Reconciliation Statement** report monthly to confirm all transactions are matched
