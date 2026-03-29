# India Banking

**Indian Banking Integration for ERPNext** — by [Aerele Technologies](https://aerele.in)

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![ERPNext](https://img.shields.io/badge/ERPNext-v16-blue)](https://erpnext.com)
[![Frappe](https://img.shields.io/badge/Frappe-v16-blue)](https://frappeframework.com)

---

## Overview

India Banking is a Frappe app that integrates ERPNext with Indian banks for seamless payment processing directly from within ERPNext. It supports **vendor payouts**, **employee payroll disbursements**, **bank statement import**, and **payment notifications**.

### Supported Banks

| Bank |
|---|
| Axis Bank |
| HDFC Bank |
| ICICI Bank |
| Kotak Mahindra Bank |
| Union Bank of India |
| Bank of Baroda |
| IDFC First Bank |
| HSBC Bank |
| Citi Bank |
| Yes Bank |

### Supported Transfer Modes

All banks support all the following transfer modes. The mode is auto-selected based on the payment amount and configured limits:

| Mode | Default Limit | Priority |
|---|---|---|
| A2A / FT / Internal | ₹1 – ₹50,00,00,000 | 1 (highest) |
| IMPS | ₹1 – ₹2,00,000 | 2 |
| RTGS | ₹2,00,000 – ₹50,00,00,000 | 3 |
| NEFT | ₹1 – ₹50,00,00,000 | 4 (fallback) |

### Integration Types

India Banking supports two types of bank integration:

1. **API Integration** — Direct REST API connection to the bank's payment gateway. Real-time payment initiation and status tracking.
2. **Host-to-Host (H2H)** — File-based integration for bulk payment processing. *(Available in v15, backport to v16 in progress.)*

---

## Payment Flows

India Banking supports **4 payment flows**. All flows converge at the **Payment Order**, from where payments are initiated to the bank.

### Flow 1: Purchase Invoice → Payment
```
Purchase Invoice
    → Payment Request
    → Payment Order
    → Payment Entry (created on success)
    → Payment Initiated via India Banking Connector
```

### Flow 2: Purchase Order → Payment
```
Purchase Order
    → Payment Request
    → Payment Order
    → Payment Entry (created on success)
    → Payment Initiated via India Banking Connector
```

### Flow 3: Journal Entry → Payment
```
Journal Entry
    → Pull into Payment Order
    → Payment Entry (created on success)
    → Payment Initiated via India Banking Connector
```

### Flow 4: Payment Entry → Payment
```
Payment Entry
    → Pull into Payment Order
    → Payment Initiated via India Banking Connector
```

> **Note:** Configurable via **India Banking Settings → Allowed Payment Doctypes**. Supported types: `Payment Request`, `Payment Entry`, `Bank Entry (JV)`.

---

## Bank Statement Import

Bank statements are fetched directly from the bank server via API and imported into ERPNext as **Bank Transactions** in **Draft** state. Users can then manually review and reconcile these against ledger entries using ERPNext's standard bank reconciliation tool.

> ⚠️ **Auto bank reconciliation is not supported.** Statements are imported only — reconciliation must be done manually.

---

## Installation

### Prerequisites
- ERPNext v16
- Frappe v16
- A bank-specific connector app (e.g. `india_banking_connector`)

### Install

```bash
bench get-app https://github.com/aerele/india-banking --branch dev16-refactor
bench --site your-site.com install-app india_banking
bench --site your-site.com migrate
```

---

## Configuration

### Step 1: India Banking Settings

Go to **India Banking Settings** to configure global behaviour:

| Field | Description |
|---|---|
| **Enable Bank Account Approval Workflow** | When enabled, new Bank Accounts require approval by an Accounts Manager before use |
| **Enforce Unique Bank Account Numbers** | Prevents duplicate account numbers in the system |
| **Summarize Payments By** | `Party` — group payments by vendor/employee; `Voucher` — group by source document |
| **Use Payment Order Date for Payment Entry** | Uses the Payment Order date as the Payment Entry date instead of today |
| **Allow Future Date Payment Order** | Allows creating Payment Orders with a future transaction date |
| **Allowed Payment Doctypes** | Which doctypes can be pulled into a Payment Order (`Payment Request`, `Payment Entry`, `Bank Entry(JV)`) |
| **Custom Application Priority** *(Beta)* | Set a custom connector app to override the default India Banking connector |

---

### Step 2: Set Up Bank Account

1. Go to **Bank Account** → Create or open an existing account
2. If the Bank Account Approval Workflow is enabled, the account must be **Approved** by an Accounts Manager before it can be used

---

### Step 3: Create India Banking Connector

Go to **India Banking Connector** → New. This is the core link between your Bank Account and the bank's API.

| Field | Description |
|---|---|
| **Company** | The ERPNext company |
| **Bank Account** | The Bank Account to connect |
| **Bank** | Auto-filled from the Bank Account |
| **URL** | The bank connector service URL |
| **API Key** | Authentication key for the connector |
| **API Secret** | Authentication secret (stored encrypted) |
| **Enable Bulk Transaction** | Enable bulk payment mode (supported: ICICI Bank, IDFC First Bank) |
| **Enqueue Large Payments in Background** | Queue payments exceeding the threshold for background processing |
| **Enqueue Payments Threshold** | Number of payments above which background processing is triggered |
| **Enable Payment Delay** | Add a minimum delay between consecutive payment API calls |
| **Payment Call Interval (Seconds)** | Minimum seconds between payment calls (e.g. `10`) |
| **Auto Post Payments** | Automatically process queued payments in the background |
| **Retry Interval (minutes)** | Time between retry attempts for queued payments |
| **Batch Size** | Maximum payments per batch in background processing |
| **Auto Update Payment Status** | If unchecked, payment status must be fetched manually |
| **Status Check At** | When to automatically check payment status |
| **Retry Period (Days)** | How many days after initiation to keep checking payment status |
| **Auto Update Posting Date as Payment Date** | If bank approval happens on a later date, update the ledger's posting date to match the actual payment date |
| **Notify Party** | Send payment notifications to vendors/employees |
| **Payment Notification** | Notification template configuration |

---

### Step 4: Configure Mode of Transfer

Go to **Mode of Transfer** to set transfer rules per mode. Each mode can be configured with:

| Field | Description |
|---|---|
| **Mode** | Transfer type: NEFT, RTGS, IMPS, A2A/FT/Internal |
| **Minimum Limit** | Minimum payment amount for this mode |
| **Maximum Limit** | Maximum payment amount for this mode |
| **Start Time / End Time** | Operating hours for this mode |
| **Priority** | Selection priority (lower = preferred) |
| **Is Bank Specific** | Restrict this mode to a specific bank/account |
| **Disabled** | Disable this mode |

The system auto-selects the transfer mode based on amount and priority.

---

## Usage

### Initiating Payments

1. Create source documents (Purchase Invoice, Purchase Order, Journal Entry, or Payment Entry)
2. Create **Payment Requests** (for invoice-based flows)
3. Open or create a **Payment Order** and pull in the references
4. Submit the Payment Order
5. Click **Initiate Payment** — the India Banking Connector calls the bank API
6. Monitor individual payment status in **Payment Order Summary**
7. On success, **Payment Entries** are created automatically

### Checking Payment Status

- If **Auto Update Payment Status** is enabled in the connector, status updates automatically
- Otherwise, manually click **Fetch Payment Status** on the Payment Order

### Importing Bank Statement

1. Open the **Bank Account** dashboard
2. Click **Get Bank Statement**
3. Transactions are imported as **Bank Transactions** in Draft state
4. Manually review and reconcile against ledger entries using ERPNext's bank reconciliation tool

### Payment Notifications

Enable **Notify Party** in the India Banking Connector to send automatic notifications to vendors/employees when payments are processed.

---

## Key Doctypes

| Doctype | Purpose |
|---|---|
| **India Banking Connector** | Core config — links a Bank Account to the bank's API |
| **India Banking Settings** | Global app settings |
| **India Banking Request Log** | Audit trail of every API call (request + response) |
| **Payment Order Summary** | Per-payment status row within a Payment Order |
| **Mode of Transfer** | NEFT/RTGS/IMPS/FT configuration rules |
| **Payment Notification** | Notification templates for payment events |
| **Bank Payment Allocation** | Allocate bank payments to invoices |
| **Naming Series Map** | Custom naming series per bank/doctype |
| **Unreconcile Bank Payment** | Records for unreconciling bank payments |

---

## Roles

| Role | Purpose |
|---|---|
| **Payment Manager** | Can initiate and manage payments via India Banking |
| **Accounts Manager** | Can approve Bank Accounts in the approval workflow |

---

## Architecture

```
india_banking/
├── api.py                          # Whitelisted API endpoints
├── hooks.py                        # Doc events, overrides, JS injections
├── default.py                      # Bank list, colors, default modes
├── install.py / uninstall.py       # Setup and teardown
├── utils.py                        # Shared helpers
│
├── india_banking/
│   ├── doc_events/                 # Handlers for standard ERPNext doctypes
│   │   ├── bank/                   # Prevent deletion of standard banks
│   │   ├── bank_account/           # Validate + dashboard data
│   │   ├── payment_entry.py        # Cancel handler
│   │   ├── payment_order.py        # Cancel pending payments, bulk ops
│   │   ├── payment_request/        # Autoname override
│   │   └── unreconcile_payment.py  # Unreconcile on submit
│   │
│   ├── doctype/                    # Custom Frappe doctypes
│   │   ├── india_banking_connector/
│   │   ├── india_banking_settings/
│   │   ├── india_banking_request_log/
│   │   ├── payment_order_summary/
│   │   ├── payment_notification/
│   │   ├── bank_payment_allocation/
│   │   ├── mode_of_transfer/
│   │   ├── naming_series_map/
│   │   └── unreconcile_bank_payment/
│   │
│   └── report/
│       ├── bank_gst_payables/
│       ├── bulk_create_payment_request/
│       └── bulk_update_payment_request/
│
├── overrides/
│   ├── payment_request.py          # Extended Payment Request
│   └── payment_order.py            # Extended Payment Order
│
└── public/js/                      # Client-side scripts for standard doctypes
```

---

## License

GNU General Public License v3.0 — see [LICENSE](LICENSE)

## Support

- 📧 support@aerele.in
- 🌐 [aerele.in](https://aerele.in)
- 🐛 [GitHub Issues](https://github.com/aerele/india-banking/issues)
