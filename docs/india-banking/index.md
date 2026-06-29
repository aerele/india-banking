# India Banking

India Banking is a Frappe application that integrates ERPNext with major Indian banks, enabling you to initiate payments, track payment status, fetch bank statements, and reconcile transactions — all without leaving ERPNext.

<!-- PLACEHOLDER: hero-banner.png
     Description: A wide banner showing the India Banking module homepage in ERPNext desk,
     highlighting the Payment Order list with status indicators (Pending, Initiated, Processed).
     Suggested size: 1200×500px -->

---

## What Can You Do with India Banking?

| Feature | Description |
|---|---|
| **Payment Requests** | Create outward payment requests against Purchase Orders and Invoices with TDS and GST hold support |
| **Payment Orders** | Batch multiple payment requests into a single bank instruction |
| **Initiate Payments** | Send payments directly to the bank via API — NEFT, RTGS, IMPS, or A2A |
| **Auto Status Tracking** | Automatically fetch UTR and payment status from the bank at configured intervals |
| **Bank Balance** | Check live bank balance from within ERPNext |
| **Bank Statements** | Fetch and import bank statements for reconciliation |
| **Bulk Payment Requests** | Create payment requests for multiple purchase invoices in one click |

---

## Supported Banks

| Bank | Individual Payments | Bulk (File-based) |
|---|---|---|
| ICICI Bank | ✓ | ✓ |
| IDFC First Bank | — | ✓ |
| Axis Bank | — | ✓ |
| Canara Bank | — | ✓ |
| HDFC Bank | ✓ | — |
| Kotak Mahindra Bank | ✓ | — |
| Union Bank of India | ✓ | — |
| Bank of Baroda | ✓ | — |
| CITI Bank | ✓ | ✓ (H2H) |

---

## Getting Started

1. [Installation & Prerequisites](setup/installation.md)
2. [Bank Connector Setup](setup/bank-connector.md)
3. [India Banking Settings](setup/settings.md)
4. [Mode of Transfer](setup/mode-of-transfer.md)
5. [Payment Type](setup/payment-type.md)
6. [Bank Account & Approval Workflow](setup/bank-account.md)

## User Guide

1. [Creating a Payment Request](user-guide/payment-request.md)
2. [Creating a Payment Order](user-guide/payment-order.md)
3. [Initiating a Bank Payment](user-guide/initiate-payment.md)
4. [Tracking Payment Status](user-guide/payment-status.md)
5. [Fetching Bank Balance & Statements](user-guide/bank-balance.md)
6. [Reconciliation & Unreconcile](user-guide/reconciliation.md)
7. [Bulk Payment Requests from Purchase Invoices](user-guide/bulk-payment-request.md)
