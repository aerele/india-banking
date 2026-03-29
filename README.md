# India Banking

> Indian Banking Integration for ERPNext — by [Aerele Technologies](https://aerele.in)

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![ERPNext v16](https://img.shields.io/badge/ERPNext-v16-0089FF)](https://erpnext.com)
[![Frappe v16](https://img.shields.io/badge/Frappe-v16-0089FF)](https://frappeframework.com)

India Banking integrates ERPNext with Indian bank APIs, enabling payment initiation, status tracking, and bank statement import — directly from within ERPNext workflows.

---

## Supported Banks

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

---

## Integration Types

### API Integration
Direct REST API connection to the bank's payment gateway via a bank-specific connector app. Supports real-time payment initiation and status tracking.

### Host-to-Host (H2H)
File-based integration for bulk payment processing. *(Available in v15; backport to v16 in progress.)*

---

## Transfer Modes

All supported banks use the same set of transfer modes. The mode is **auto-selected** based on the payment amount and the priority configured in **Mode of Transfer**:

| Mode | Default Amount Range | Default Priority |
|---|---|---|
| A2A / FT / Internal | ₹1 – ₹50,00,00,000 | 1 (highest) |
| IMPS | ₹1 – ₹2,00,000 | 2 |
| RTGS | ₹2,00,000 – ₹50,00,00,000 | 3 |
| NEFT | ₹1 – ₹50,00,00,000 | 4 (fallback) |

A2A/FT is bank-specific and applied only when the source and destination accounts belong to the same bank.

---

## Payment Flows

All flows converge at the **Payment Order**, from which the connector initiates payment with the bank. The following source doctypes are supported (configurable in India Banking Settings):

### 1. Purchase Invoice → Payment Entry
```
Purchase Invoice
  └─► Payment Request (auto-named per bank series)
        └─► Payment Order
              ├─► Payment Entry (auto-created on initiation)
              └─► Payment initiated via India Banking Connector
```

### 2. Purchase Order → Payment Entry
```
Purchase Order
  └─► Payment Request
        └─► Payment Order
              ├─► Payment Entry
              └─► Payment initiated via India Banking Connector
```

### 3. Journal Entry → Payment
```
Journal Entry
  └─► Pulled directly into Payment Order (as Bank Entry/JV)
        ├─► Payment Entry
        └─► Payment initiated via India Banking Connector
```

### 4. Payment Entry → Payment
```
Payment Entry
  └─► Pulled directly into Payment Order
        └─► Payment initiated via India Banking Connector
```

---

## Bank Statement Import

Bank statements are fetched from the bank server via API and imported as **Bank Transactions** in **Draft** state. Users then manually review and reconcile these against ERPNext ledger entries.

> **Note:** Auto-reconciliation is not supported. Statement import and reconciliation are separate manual steps.

---

## Payment Status Lifecycle

Each row in the **Payment Order Summary** tracks an individual payment through the following states:

| Status | Meaning |
|---|---|
| `Pending` | Payment not yet initiated |
| `Initiated` | Payment request sent to bank, awaiting confirmation |
| `Processed` | Bank confirmed the payment |
| `Failed` | Bank rejected the payment |

On failure, the corresponding Payment Entry is cancelled and the Payment Request is reset.

---

## OTP Authorization

For **ICICI Bank** and **IDFC First Bank** with bulk transaction mode enabled, the connector requires OTP authorization before initiating payments. The system detects this automatically and prompts for OTP before calling the bank API.

---

## Installation

### Prerequisites
- ERPNext v16 + Frappe v16
- A bank-specific connector app providing the payment gateway interface

### Steps

```bash
# Fetch the app
bench get-app https://github.com/aerele/india-banking --branch dev16-refactor

# Install on your site
bench --site <your-site> install-app india_banking

# Run migrations
bench --site <your-site> migrate
```

---

## Configuration

### 1. India Banking Settings

Navigate to **India Banking Settings** to configure global behaviour:

| Setting | Description |
|---|---|
| **Enable Bank Account Approval Workflow** | Requires Accounts Manager approval before a Bank Account can be used for payments |
| **Enforce Unique Bank Account Numbers** | Prevents duplicate bank account numbers across the system |
| **Summarize Payments By** | `Party` — one payment per vendor/employee per order; `Voucher` — one payment per source document |
| **Use Payment Order Date for Payment Entry** | Sets the Payment Entry posting date to the Payment Order date rather than today |
| **Allow Future Date Payment Order** | Allows creating Payment Orders with a future `posting_date` |
| **Allowed Payment Doctypes** | Doctypes that can be pulled into a Payment Order. Defaults: `Payment Request`, `Payment Entry`, `Bank Entry(JV)` |
| **Custom Application Priority** *(Beta)* | Override the default connector with a custom app (cannot be `frappe`, `erpnext`, `payments`, or `hrms`) |

---

### 2. Bank Account

Create or open a **Bank Account** in ERPNext. If the approval workflow is enabled, the account must reach **Approved** state before payments can be initiated from it.

---

### 3. India Banking Connector

Create one **India Banking Connector** per bank account. This is the central configuration record linking an ERPNext Bank Account to the external connector service.

**Connection**

| Field | Description |
|---|---|
| `company` | The ERPNext company |
| `bank_account` | The Bank Account to connect |
| `url` | URL of the bank connector service |
| `api_key` | Connector API key (stored encrypted) |
| `api_secret` | Connector API secret (stored encrypted) |

**Transaction Processing**

| Field | Description |
|---|---|
| `bulk_transaction` | Enable bulk payment mode. When enabled, all payments in an order are sent in a single API call. Supported for ICICI Bank and IDFC First Bank only |
| `enqueue_large_payments_in_the_background` | Process large payment batches as background jobs |
| `enqueue_payments_threshold` | Minimum number of payments to trigger background processing |
| `enable_payment_delay` | Add a minimum interval between consecutive payment API calls |
| `payment_call_interval` | Minimum seconds between payment calls (e.g. `10`) |
| `auto_post_payments` | Automatically process queued payments via a cron job |
| `retry_interval_minutes` | Minutes between background retry attempts |
| `batch_size` | Maximum payments per background batch |

**Status Tracking**

| Field | Description |
|---|---|
| `auto_update_payment_status` | Automatically fetch payment status from the bank. When disabled, status must be fetched manually |
| `status_check_at` | Timing for automatic status checks |
| `retry_period` | Number of days after initiation to continue checking `Processed` payment status |
| `auto_update_posting_date_as_payment_date` | If a payment is approved on a date later than the Payment Entry posting date, update the ledger accordingly to match the bank statement date |

**Naming**

| Field | Description |
|---|---|
| `doctype_naming_series` | Override the default naming series for Payment Requests and Payment Orders per bank |

**Notifications**

| Field | Description |
|---|---|
| `notify_party` | Send payment notifications to vendors/employees |
| `payment_notification` | Notification template configuration |

---

### 4. Mode of Transfer

Configure transfer mode rules under **Mode of Transfer**. The system auto-selects the mode with the highest priority that satisfies the payment amount.

| Field | Description |
|---|---|
| `mode` | Transfer type: `NEFT`, `RTGS`, `IMPS`, `A2A/FT/Internal` |
| `minimum_limit` | Minimum payment amount (₹) |
| `maximum_limit` | Maximum payment amount (₹) |
| `start_time` / `end_time` | Operating window for this mode |
| `priority` | Selection order (lower number = higher priority) |
| `is_bank_specific` | Restrict this mode to a specific bank/account |
| `disabled` | Disable this mode |

---

## Usage

### Initiating a Payment

1. Create the source document (Purchase Invoice, Purchase Order, Journal Entry, or Payment Entry)
2. For invoice/PO flows: create a **Payment Request**
3. Open or create a **Payment Order** and pull in the references
4. **Validate Summary** to generate the Payment Order Summary rows
5. Submit the Payment Order
6. Click **Initiate Payment**
   - For ICICI/IDFC First (bulk mode): enter OTP when prompted
7. Monitor per-payment status in the **Payment Order Summary** child table
8. Payment Entries are created automatically on success

### Checking Payment Status

- **Auto mode**: status updates based on the cron configured in the connector
- **Manual mode**: click **Get Payment Status** on the Payment Order

### Cancelling Failed Payments

Use **Cancel Pending Payments** on the Payment Order to cancel failed rows. The corresponding Payment Entry is cancelled and the Payment Request is reset to open.

### Importing Bank Statement

1. Open the **Bank Account** record
2. Click **Get Bank Statement** from the dashboard
3. Specify date range
4. Transactions are imported as **Bank Transactions** in Draft state
5. Manually reconcile using ERPNext's standard bank reconciliation tool

---

## Architecture

```
india_banking/
├── api.py                          # Whitelisted endpoints: get_standard_bank,
│                                   # get_connected_bank_accounts
├── hooks.py                        # Doc events, doctype JS/list JS overrides,
│                                   # override_doctype_class
├── default.py                      # STD_BANK_LIST, BANK_CARD_COLORS,
│                                   # DEFAULT_MODE_OF_TRANSFERS, ALLOWED_PAYMENT_DOCTYPE
├── install.py                      # Post-install: create standard banks, modes,
│                                   # roles, and workflows
├── utils.py                        # get_bank_address_details, get_party_field_name,
│                                   # get_bank_payment_naming_series, extract_error_message
│
├── india_banking/
│   ├── doc_events/
│   │   ├── bank/bank.py            # Prevents deletion of standard banks
│   │   ├── bank_account/           # Validate bank account, dashboard data provider
│   │   ├── payment_entry.py        # On-cancel: unlinks from Payment Order Summary
│   │   ├── payment_order.py        # cancel_pending_payments, make_payment_entries,
│   │   │                           # process_payment_requests
│   │   ├── payment_request/        # autoname override (uses naming series map)
│   │   └── unreconcile_payment.py  # On-submit: reverse reconciliation
│   │
│   ├── doctype/
│   │   ├── india_banking_connector/    # Core payment engine:
│   │   │                               # make_post_request, make_single_request,
│   │   │                               # get_bank_balance, get_bank_statements,
│   │   │                               # verify_response, update_payment_status,
│   │   │                               # check_otp_enabled, generate_otp, verify_otp
│   │   ├── india_banking_settings/     # Global settings + workflow toggle
│   │   ├── india_banking_request_log/  # Audit trail: request payload, response, status
│   │   ├── payment_order_summary/      # Per-payment row: status, payment entry link,
│   │   │                               # payment date, failure reason
│   │   ├── payment_notification/       # Vendor/employee notification on payment events
│   │   ├── bank_payment_allocation/    # Allocate bank payments to open invoices
│   │   ├── mode_of_transfer/           # NEFT/RTGS/IMPS/A2A rules with limits/timing
│   │   ├── naming_series_map/          # Per-bank naming series overrides
│   │   └── unreconcile_bank_payment/   # Stores unreconciliation records
│   │
│   └── report/
│       ├── bank_gst_payables/              # GST payable amounts by bank
│       ├── bulk_create_payment_request/    # Bulk PR creation from invoices
│       └── bulk_update_payment_request/    # Bulk PR status update
│
├── overrides/
│   ├── payment_request.py      # BankPaymentRequest: extended Payment Request
│   │                           # with bank-specific validation
│   └── payment_order.py        # CustomPaymentOrder: before_submit validation
│                               # (future date check, amount mismatch check),
│                               # validate_summary (mode of transfer assignment)
│
└── public/js/
    ├── bank_account.js         # Balance fetch button on Bank Account form
    ├── payment_request.js      # Bank-specific fields and actions
    ├── payment_order.js        # Initiate payment, get status, cancel buttons
    ├── payment_entry.js        # Pull into Payment Order action
    └── purchase_invoice.js     # Bulk PR creation shortcut
```

---

## Key Design Decisions

**Connector-per-account model**: Each `India Banking Connector` is scoped to a single Bank Account. This allows different banks and accounts to have independent configuration (retry logic, batch size, OTP requirements) without cross-contamination.

**Payment Order Summary as the source of truth**: Individual payment status is tracked at the `Payment Order Summary` child row level, not the Payment Order header. This allows partial success — some payments in a batch can succeed while others fail and are retried independently.

**Naming series isolation**: The `Naming Series Map` doctype allows each bank to use a separate document series for Payment Requests and Payment Orders, making it easy to trace which bank a document belongs to.

**Request logging**: Every bank API call is logged in `India Banking Request Log` with full request/response payloads. This is essential for debugging payment failures and providing evidence in bank disputes.

---

## Roles

| Role | Purpose |
|---|---|
| **Payment Manager** | Initiate and manage bank payments |
| **Accounts Manager** | Approve Bank Accounts in the approval workflow |

---

## License

GNU General Public License v3.0 — see [LICENSE](LICENSE)

## Support

- 📧 support@aerele.in
- 🌐 [aerele.in](https://aerele.in)
- 🐛 [GitHub Issues](https://github.com/aerele/india-banking/issues)
