# India Banking Settings

## Overview

India Banking Settings is a Single doctype that acts as the central configuration switch for the entire `india_banking` app. Every other doctype — Bank Account, Payment Request, Payment Order, India Banking Connector — reads from it to decide what validations to enforce and how to behave. Changes here take effect immediately across the system without a restart.

Navigate to: **Banking → Setup → India Banking Settings**

---

## Fields

### Bank Account

| Field | Fieldname | Default | Effect |
|---|---|---|---|
| Enable Bank Account Approval Workflow | `enable_bank_account_workflow` | On | When enabled, bank accounts must pass through an approval workflow before they can be used in payments. The `bank_account` field on Payment Request and Payment Entry only shows `Approved` accounts. |
| Enforce Unique Bank Account Numbers | `enable_unique_account_no` | On | Prevents saving a Bank Account whose `bank_account_no` already exists on another active record. |

### Basic Configuration

| Field | Fieldname | Default | Effect |
|---|---|---|---|
| Summarize Payments By | `summarise_payment_based_on` | — | Controls how Payment Order summary rows are grouped. **Party** → one row per party. **Voucher** → one row per source document. Auto-applied to new Payment Orders on load. |
| Use Payment Order Date for Payment Entry | `use_payment_order_date_as_payment_entry_date` | Off | When on, Payment Entries created from a Payment Order use the Payment Order's `posting_date` instead of today's date. |
| Allow Future Date Payment Order | `allow_future_date_payment_order` | Off | When off, submitting a Payment Order with a `posting_date` in the future is blocked. |
| Allowed Payment Doctypes | `allowed_payment_doctypes` | — | Newline-separated list of source doctypes that can be pulled into a Payment Order. Options: `Payment Request`, `Payment Entry`, `Bank Entry(JV)`. Only doctypes listed here appear in the **Get Payments from** menu. |

### Custom App Priority (Beta)

| Field | Fieldname | Default |
|---|---|---|
| Custom Application Priority | `custom_app_priority` | `India Banking` |

Controls which app's overrides take precedence when multiple custom apps override the same ERPNext method. Leave as default unless another custom app conflicts.

---

## Allowed Payment Doctypes

This field is a plain text list — one doctype name per line. It is managed through a dialog (not direct text editing) by clicking the field on the form. The dialog shows all supported doctypes as checkboxes.

Supported values:
- `Payment Request`
- `Payment Entry`
- `Bank Entry(JV)`

Removing a doctype from this list hides its pull button from all draft Payment Orders immediately.

---

## Where Each Setting Is Read

| Setting | Read By |
|---|---|
| `enable_bank_account_workflow` | Bank Account (unique account validation), Payment Request (submit), Payment Entry (`make_payment_order`), Journal Entry (`make_payment_order`), Bank Account form (field query filter) |
| `enable_unique_account_no` | Bank Account (`validate_unique_acc_no`) |
| `summarise_payment_based_on` | Payment Order form (onload default), `get_party_summary` |
| `use_payment_order_date_as_payment_entry_date` | `make_payment_entries` (posting date of created Payment Entry) |
| `allow_future_date_payment_order` | Payment Order (`before_submit` date check) |
| `allowed_payment_doctypes` | Payment Order form (`set_get_payments_from_buttons`) |

---

## Key Files

| File | Purpose |
|---|---|
| `india_banking/india_banking/doctype/india_banking_settings/india_banking_settings.json` | Field definitions |
| `india_banking/india_banking/doctype/india_banking_settings/india_banking_settings.js` | Allowed Doctypes dialog, naming series query |
