# Mode of Transfer

## Overview

Mode of Transfer defines the payment rail (NEFT, RTGS, IMPS, A2A/Internal) that a payment will travel over. Each record sets the amount range it covers, the time window it is valid, and whether it applies only to a specific bank (bank-specific) or to all banks (generic). Payment Order uses these records to auto-assign the right transfer mode to each summary row and to validate that the assigned mode is appropriate before submission.

---

## Fields

| Field | Fieldname | Purpose |
|---|---|---|
| Mode | `mode` | Name of the transfer rail — e.g. `NEFT`, `RTGS`, `IMPS`, `A2A/FT/Internal` |
| Minimum Limit | `minimum_limit` | Minimum payment amount this mode supports (inclusive) |
| Maximum Limit | `maximum_limit` | Maximum payment amount this mode supports (inclusive) |
| Is Bank Specific | `is_bank_specific` | When on, this mode applies only to the bank/bank account set below |
| Bank | `bank` | Bank this mode applies to (only when `is_bank_specific` is on) |
| Bank Account | `bank_account` | Bank account this mode applies to (only when `is_bank_specific` is on) |
| Start Time | `start_time` | Earliest time of day this mode is valid |
| End Time | `end_time` | Latest time of day this mode is valid |
| Priority | `priority` | Determines which mode is selected first when multiple modes match an amount. Lower number = higher priority. |
| Disabled | `disabled` | Excludes this mode from auto-assignment and validation |

---

## Default Records Created on Install

Four records are created automatically when the app is installed:

| Mode | Min | Max | Priority | Bank Specific |
|---|---|---|---|---|
| A2A/FT/Internal | ₹1 | ₹50 Cr | 1 | Yes |
| IMPS | ₹1 | ₹2 L | 2 | No |
| RTGS | ₹2 L | ₹50 Cr | 3 | No |
| NEFT | ₹1 | ₹50 Cr | 4 | No |

All default records are active 24×7 (`00:00:00` – `23:59:59`).

---

## Auto-Assignment in Payment Order

When `get_party_summary()` builds the Payment Order summary, it calls `get_mode_of_transfer()` for each summary row using this logic:

1. **Same bank (A2A):** If the party's bank matches the company's bank, look for a bank-specific mode (`is_bank_specific=1, bank=party_bank`). Assign it if found.
2. **Different bank (generic):** Find the enabled (`disabled=0`) non-bank-specific mode whose `minimum_limit ≤ amount ≤ maximum_limit`, ordered by `priority asc`. Fall back to the Payment Order's `default_mode_of_transfer` if no match is found.

---

## Validation on Payment Order Submit

`validate_summary()` runs on every Payment Order save and checks each summary row:

| Rule | Condition |
|---|---|
| Mode must be set | Throws if `mode_of_transfer` is blank and no default is configured |
| Amount within limits | `minimum_limit ≤ amount ≤ maximum_limit` — throws if outside range |
| A2A only for same bank | A mode whose `mode` contains `A2A` is rejected if the party's bank differs from the company bank |
| Auto-upgrade to A2A | If the party's bank matches the company bank but a non-A2A mode is assigned, the system automatically replaces it with the first available A2A mode |
| LEI required for large NEFT/RTGS | Payments via NEFT or RTGS above ₹50 Cr require a valid `lei_number` on the party record |

---

## Usage in Payment Entry Flow

When initiating payment directly from a Payment Entry (without going through a Payment Order), the form shows a **Select Mode of Transfer** dialog. The selected mode is passed to `create_payment_order()` as the `default_mode_of_transfer`.

---

## Key Files

| File | Purpose |
|---|---|
| `india_banking/india_banking/doctype/mode_of_transfer/mode_of_transfer.json` | Field definitions |
| `india_banking/default.py` | `DEFAULT_MODE_OF_TRANSFERS` — records created on install |
| `india_banking/install.py` (`create_default_mode_of_transfers`) | Install-time creation of default records |
| `india_banking/overrides/payment_order.py` (`get_mode_of_transfer`, `validate_summary`) | Auto-assignment and validation logic |
| `india_banking/public/js/payment_entry.js` | Mode of Transfer dialog on Payment Entry form |
