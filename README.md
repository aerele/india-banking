# India Banking

**Indian Banking Integration for ERPNext** — by [Aerele Technologies](https://aerele.in)

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![ERPNext](https://img.shields.io/badge/ERPNext-v16-blue)](https://erpnext.com)
[![Frappe](https://img.shields.io/badge/Frappe-v16-blue)](https://frappeframework.com)

---

## Overview

India Banking is a Frappe app that integrates ERPNext with Indian banks for seamless payment processing. It supports **vendor payouts**, **payroll disbursements**, **statement reconciliation**, and **virtual account receipts** — all from within ERPNext.

### Supported Banks

| Bank | Vendor Payout | Payroll | Statement | Virtual Account |
|---|---|---|---|---|
| HDFC Bank | ✅ | ✅ | ✅ | ✅ |
| ICICI Bank | ✅ | ✅ | ✅ | ✅ |
| Axis Bank | ✅ | ✅ | ✅ | — |
| Kotak Mahindra | ✅ | ✅ | ✅ | — |
| YES Bank | ✅ | ✅ | — | — |
| Union Bank | ✅ | ✅ | — | — |
| Bank of Baroda | ✅ | ✅ | — | — |
| HSBC | ✅ | — | — | — |
| Canara Bank | ✅ | — | — | — |
| IDFC First | ✅ | — | — | — |

---

## Features

### 💸 Payment Processing
- Initiate **vendor payouts** directly from Payment Orders in ERPNext
- Supports **NEFT, RTGS, IMPS, FT** transfer modes
- Bulk payment initiation with real-time status tracking
- OTP-based authorization for ICICI Bank bulk transactions
- Cancel pending/failed payments from ERPNext

### 📊 Statement Reconciliation
- Auto-fetch bank statements via API
- Match and reconcile transactions against ERPNext entries
- Unreconcile payments when needed

### 🔔 Payment Notifications
- Real-time payment status updates via webhooks
- Notify parties on payment success/failure
- Configurable notification templates

### 🏦 Bank Account Management
- Approval workflow for new bank accounts
- Validate beneficiary bank accounts before payment
- Dashboard showing connected accounts with balance

### 📋 Reporting
- Bank GST Payables report
- Bulk Payment Request creation
- Bulk Payment Request status updates

---

## Architecture

```
india_banking/
├── api.py                          # Public whitelisted API endpoints
├── hooks.py                        # Frappe hooks — doc events, overrides
├── default.py                      # Bank color constants
├── install.py                      # Post-install setup
├── utils.py                        # Shared utilities
│
├── india_banking/
│   ├── doc_events/                 # Event handlers for standard doctypes
│   │   ├── bank/                   # Prevent deletion of standard banks
│   │   ├── bank_account/           # Validate & dashboard for Bank Account
│   │   ├── payment_entry.py        # On cancel handler
│   │   ├── payment_order.py        # Cancel pending payments, bulk processing
│   │   ├── payment_request/        # Autoname override
│   │   └── unreconcile_payment.py  # Unreconcile on submit
│   │
│   ├── doctype/
│   │   ├── india_banking_connector/    # Core connector — initiates bank API calls
│   │   ├── india_banking_settings/     # Global app settings
│   │   ├── india_banking_request_log/  # API request/response audit log
│   │   ├── payment_order_summary/      # Per-payment status tracking
│   │   ├── payment_notification/       # Webhook notification handler
│   │   ├── bank_payment_allocation/    # Allocate payments to invoices
│   │   ├── mode_of_transfer/           # NEFT/RTGS/IMPS/FT configuration
│   │   ├── naming_series_map/          # Custom naming series per bank
│   │   └── unreconcile_bank_payment/   # Unreconciliation records
│   │
│   └── report/
│       ├── bank_gst_payables/          # GST payable report
│       ├── bulk_create_payment_request/
│       └── bulk_update_payment_request/
│
├── overrides/
│   ├── payment_request.py          # Extended Payment Request doctype
│   └── payment_order.py            # Extended Payment Order doctype
│
└── public/
    ├── js/                         # Client-side scripts
    └── assets/bank-logos/          # Bank logo images
```

---

## Key Doctypes

### India Banking Connector
The core doctype that manages the connection between ERPNext and a bank's API.

**Fields:**
- `bank_account` — the ERPNext Bank Account linked to this connector
- `url` — the bank connector service URL
- `api_key` / `api_secret` — authentication credentials (stored encrypted)
- `bank` — the bank name (HDFC, ICICI, etc.)

**Key Methods:**
- `initiate_payment(payment_order)` — sends payment request to bank API
- `get_bank_balance()` — fetches current balance
- `get_bank_statement(from_date, to_date)` — fetches statement
- `check_user_permission()` — enforces Payment Order write permission

### India Banking Settings
Global configuration for the app.

**Key Settings:**
- `enable_bank_account_workflow` — toggle approval workflow for bank accounts
- `custom_app_priority` — specify a custom connector app (overrides default)
- `notify_party` — enable payment notifications to vendors/employees
- `payment_notification` — notification template configuration

### India Banking Request Log
Audit trail for every API call made to bank APIs.

**Fields:**
- `request_data` — JSON payload sent to bank
- `response_data` — JSON response received
- `status` — Success / Failed
- `reference_doctype` / `reference_name` — linked ERPNext document

### Payment Order Summary
Tracks the status of each individual payment within a Payment Order.

**Payment Statuses:**
- `Initiated` — payment sent to bank
- `Success` — bank confirmed payment
- `Failed` — bank rejected payment
- `Pending` — awaiting bank response

---

## Payment Flow

```
Purchase Invoice
    ↓
Payment Request (auto-named per bank series)
    ↓
Payment Order (grouped by bank account)
    ↓
India Banking Connector → Bank API
    ↓
Payment Order Summary (per-row status)
    ↓
Payment Entry (on success)
    ↓
Bank Statement Reconciliation
```

---

## Installation

### Prerequisites
- ERPNext v16
- Frappe v16
- A bank connector app (e.g. `india_banking_connector` for your bank)

### Install

```bash
# Get the app
bench get-app https://github.com/aerele/india-banking --branch version-16-dev

# Install on your site
bench --site your-site.com install-app india_banking

# Run migrations
bench --site your-site.com migrate
```

---

## Configuration

### 1. India Banking Settings
Go to **India Banking Settings** and configure:
- Enable/disable bank account approval workflow
- Set notification preferences
- Configure custom app priority (if using a custom connector)

### 2. Add Bank Account
- Create or open a **Bank Account** in ERPNext
- The account will go through approval workflow (if enabled)

### 3. Create India Banking Connector
- Go to **India Banking Connector** → New
- Select the Bank Account
- Enter the connector URL and API credentials
- Test the connection

### 4. Mode of Transfer
- Configure transfer modes (NEFT, RTGS, IMPS, FT) per bank
- Set minimum/maximum limits per mode

---

## Usage

### Initiating Payments

1. Create **Payment Requests** for vendor invoices
2. Group them into a **Payment Order**
3. Submit the Payment Order
4. Click **Initiate Payment** — the connector calls the bank API
5. Monitor status in **Payment Order Summary**
6. On success, **Payment Entries** are created automatically

### Bulk Operations

Use the reports for bulk workflows:
- **Bulk Create Payment Request** — create PRs for multiple invoices at once
- **Bulk Update Payment Request** — update status for multiple PRs

### Reconciliation

1. Fetch bank statement via the Bank Account dashboard
2. Use ERPNext's standard reconciliation tool
3. Unreconcile via **Unreconcile Bank Payment** if needed

---

## API Reference

### `india_banking.api.get_standard_bank`
Returns list of supported standard banks with logos.

```python
# Response
[{"name": "HDFC Bank", "logo": "/assets/india_banking/assets/bank-logos/HDFC_Bank.png"}]
```

### `india_banking.api.get_connected_bank_accounts`
Returns all bank accounts linked to active connectors.

```python
# Response
[{
    "name": "HDFC - Company",
    "account_name": "Current Account",
    "account_number": "XXXX1234",
    "bank_name": "HDFC Bank",
    "primary_color": "#004C8F",
    "secondary_color": "#0070CC"
}]
```

---

## Hooks Reference

| Hook | Handler |
|---|---|
| `after_install` | `india_banking.install.after_install` |
| `before_uninstall` | `india_banking.uninstall.before_uninstall` |
| Bank → `on_trash` | Prevent standard bank deletion |
| Bank Account → `validate` | Validate account details |
| Payment Request → `autoname` | Custom naming per bank |
| Payment Order → `autoname` | Custom naming series |
| Payment Entry → `on_cancel` | Handle payment cancellation |
| Unreconcile Payment → `on_submit` | Process unreconciliation |

---

## Development

### Running Tests

```bash
bench --site your-site.com run-tests --app india_banking
```

### Adding a New Bank

1. Create a new connector app or extend via `custom_app_priority`
2. Implement the standard connector interface
3. Add bank logo to `public/assets/bank-logos/`
4. Add bank colors to `india_banking/default.py`

---

## License

GNU General Public License v3.0 — see [LICENSE](LICENSE)

## Support

- 📧 support@aerele.in
- 🌐 [aerele.in](https://aerele.in)
- 🐛 [GitHub Issues](https://github.com/aerele/india-banking/issues)
