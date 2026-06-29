# India Banking — Flow Documentation

## Overview

India Banking integrates ERPNext with Indian banks (ICICI, HDFC, Yes Bank, Axis, Kotak, Bank of Baroda) by overriding standard ERPNext doctypes and adding a Bank Connector layer that proxies API calls to `india_banking_connector`.

---

## 1. Setup & Configuration

```mermaid
flowchart TD
    S1([Bank\nERPNext]) -->|"on_trash hook:\nblock deletion of standard banks"| S2[Bank Protected]
    S3([Bank Account]) -->|"validate hook:\ncheck IFSC code format"| S4{IFSC Valid?}
    S4 -->|No| S5([❌ Throw Error])
    S4 -->|Yes| S6[Bank Account Saved]
    S6 -->|"activate_workflow_on_bank_account\nenabled in settings"| S7[Bank Account Approval\nWorkflow triggered]
    S7 -->|Approve| S8[workflow_state = Approved]
    S7 -->|Reject| S9[workflow_state = Rejected]

    S10([Bank Connector\nDocType]) -->|"stores: URL, api_key,\napi_secret, bank, company"| S11[Connector Ready]
    S12([India Banking Settings]) -->|"status_check interval\nlog retention days\nworkflow toggle"| S13[Settings Configured]
    S14([Mode of Transfer]) -->|"NEFT / RTGS / IMPS / A2A\nmin–max limits, priority"| S15[Transfer Modes Ready]
    S16([Payment Type]) -->|"maps to a debit account\nper company"| S17[Payment Type Ready]
```

---

## 2. Payment Request Flow

> ERPNext's standard **Payment Request** doctype is overridden by `india_banking.overrides.payment_request.BankPaymentRequest`.

```mermaid
flowchart TD
    A1([Purchase Order /\nPurchase Invoice]) -->|"Make Payment Request\n(bulk: from PI list view)"| A2[Payment Request — Draft]

    A2 --> A3[set_default_value:\nauto-assign Payment Type,\nBank Account, transaction_date]
    A3 --> A4[before_insert:\nvalidate_and_update_gst_payables]

    A4 --> A5{Hold GST\nPayable?}
    A5 -->|Yes| A6[Deduct GST amount\nfrom net_total]
    A5 -->|No| A7[Amount unchanged]
    A6 --> A8[validate]
    A7 --> A8

    A8 --> A9{Ad-hoc\npayment?}
    A9 -->|Yes| A10[No reference required\nStatus = Draft]
    A9 -->|No| A11[Validate reference amount\nCheck TDS / tax withholding]
    A10 --> A12[before_submit:\nre-validate GST payables]
    A11 --> A12

    A12 --> A13[on_submit:\nvalidate_bank_account]
    A13 --> A14{Bank Account\nApproval enabled?}
    A14 -->|workflow_state ≠ Approved| A15([❌ Throw Error])
    A14 -->|Approved| A16{Ad-hoc\nOutward?}
    A16 -->|Yes| A17[db_set status = Initiated]
    A16 -->|No| A18[super.on_submit:\ncreate Payment Entry]
    A17 --> A19[Payment Request\nStatus: Initiated]
    A18 --> A19
```

---

## 3. Payment Order Flow

> ERPNext's **Payment Order** is overridden by `india_banking.overrides.payment_order.CustomPaymentOrder`.

```mermaid
flowchart TD
    B1([Payment Request\nSubmitted]) -->|"Make Payment Order"| B2[Payment Order — Draft]
    B3([Payment Entry\nSubmitted]) -->|"Make Payment Order"| B2
    B4([Journal Entry\nBank Entry]) -->|"Make Payment Order"| B2

    B2 --> B5[Add References]
    B5 -->|"get_party_summary:\ngroup by Party or Voucher"| B6[Summary Generated]
    B6 -->|"get_mode_of_transfer:\nauto-assign by amount + bank match"| B7[Mode of Transfer Assigned]

    B7 --> B8[validate]
    B8 --> B9{A2A — same bank\ncheck}
    B9 -->|Mismatch| B10([❌ Throw Error])
    B9 -->|OK| B11{RTGS > ₹50Cr\nLEI required?}
    B11 -->|Missing| B10
    B11 -->|OK| B12[validate_summary:\ntotals match references?]
    B12 -->|Mismatch| B10
    B12 -->|OK| B13{Payment Request\namount match?}
    B13 -->|Mismatch| B10
    B13 -->|OK| B14{Bank balance\nsufficient?}
    B14 -->|Insufficient| B10
    B14 -->|OK| B15[before_submit:\ngenerate unique_id &\nfile_reference_id]

    B15 --> B16[on_submit]
    B16 --> B17{Payment Order\nType?}
    B17 -->|Payment Request| B18[make_payment_entries\nper summary row]
    B17 -->|Journal Entry| B19[update_payment_status\n= Ordered]
    B17 -->|Payment Entry /\nPayroll Entry| B20[No new entries\nstatus = Pending]
    B18 --> B21[Payment Order\nStatus: Pending]
    B19 --> B21
    B20 --> B21
```

---

## 4. Initiate Bank Payment

```mermaid
flowchart TD
    C1([User clicks\n'Make Bank Payment']) --> C2[Lookup Bank Connector\nfor company + bank_account]
    C2 --> C3{ICICI Bulk\nTransaction?}

    C3 -->|Yes| C4[generate_payment_otp:\nAPI call to ICICI]
    C4 --> C5[User enters OTP]
    C5 --> C6[process_bulk_payment:\nPOST file to ICICI API]
    C6 --> C7{Response?}
    C7 -->|ACCEPTED| C8[Store file_sequence_number\nAll rows: Initiated]
    C7 -->|Failed| C9([Return failure message])

    C3 -->|No — individual| C10[get_payment_status:\ncheck existing Initiated rows first]
    C10 --> C11[process_payment\nper Pending row]
    C11 --> C12{API response\nper row}
    C12 -->|Initiated| C13[Mark row Initiated\npayment_initiated = 1]
    C12 -->|Failed| C14[Cancel Payment Entry\nMark row Failed]

    C8 --> C15[Payment Order\nStatus: Initiated]
    C13 --> C15
    C14 --> C16[update_payment_status:\nre-evaluate order status]
```

---

## 5. Bank Connector API Layer

```mermaid
flowchart TD
    D1[Build Auth Header\napi_key:api_secret token] --> D2[POST to connector URL\n/api/method/app.doctype...]
    D2 --> D3[Log to India Banking\nRequest Log]
    D3 --> D4{HTTP status?}
    D4 -->|200 + Success| D5[Parse UTR / TxnID\nfrom response]
    D4 -->|200 + Failure| D6[Log error message\nreturn failure]
    D4 -->|Non-200| D6
    D5 --> D7[Update Payment Entry\nreference_no = UTR]
    D7 --> D8[notify_party:\nEmail / SMS]
```

---

## 6. Scheduled Payment Status Checks

```mermaid
flowchart TD
    E1([Scheduler]) --> E2{Status check\ninterval setting}
    E2 -->|Every 20 min| E3[job_twenty_minutes]
    E2 -->|Every Hour| E4[job_one_hour]
    E2 -->|Every Day at Midnight| E5[job_at_midnight]

    E3 & E4 & E5 --> E6[Find Payment Orders\nwhere status = Initiated\nin Payment Order Summary]
    E6 --> E7[frappe.enqueue\nget_payment_status per order]

    E7 --> E8{ICICI Bulk?}
    E8 -->|Yes| E9[get_bulk_payment_status:\ncheck file_sequence_number]
    E8 -->|No| E10[get_response\nper summary row]

    E9 & E10 --> E11{Status from bank}
    E11 -->|Processed| E12[Update Payment Entry\nwith UTR / reference]
    E12 --> E13[Payment Order\nStatus: Processed]
    E13 --> E14[notify_party\nEmail / SMS]
    E11 -->|Failed| E15[Mark row Failed\nCancel Payment Entry]
    E11 -->|Pending / In-Progress| E16[Leave as Initiated\nretry next cycle]
```

---

## 7. Reconciliation & Unreconcile

```mermaid
flowchart TD
    F1([Bank Statement\nImport / Bank Transaction]) --> F2[Match with\nPayment Entries]
    F2 --> F3[Bank Transaction Reconciled]

    F3 --> F4{User submits\nUnreconcile Payment?}
    F4 -->|on_submit hook| F5{source_doctype\n= Payment Request?}
    F5 -->|Yes| F6[get_payment_order_summary\nfor that Payment Entry]
    F6 --> F7[unlink_bank_payment:\nreset Payment Order Summary\npayment_status & reference]
    F5 -->|No| F8[Standard ERPNext\nunreconcile flow]
```

---

## 8. Daily Log Cleanup

```mermaid
flowchart TD
    G1([Daily Scheduler]) --> G2{clear_india_banking\n_request_log enabled?}
    G2 -->|No| G3([Skip])
    G2 -->|Yes| G4[Count logs older\nthan stale_days setting]
    G4 --> G5{count > 50,000?}
    G5 -->|Yes| G6[Delete one 7-day\nbatch window]
    G6 --> G7[Re-count remaining]
    G7 -->|Still > 50k| G8[Enqueue next batch]
    G5 -->|No| G9[Delete all stale logs\nin one pass]
```

---

## Key DocTypes

| DocType | Module | Role |
|---|---|---|
| **Payment Request** | ERPNext (overridden) | Per-invoice payment request; overridden by `BankPaymentRequest` to add TDS, GST hold, bank account approval, ad-hoc support |
| **Payment Order** | ERPNext (overridden) | Batches multiple payment requests into one bank instruction; overridden by `CustomPaymentOrder` |
| **Payment Entry** | ERPNext (overridden) | Accounting entry created on Payment Order submit; extended to carry `source_doctype` |
| **Bank Account** | ERPNext | Company and party bank accounts; IFSC validation + optional approval workflow |
| **Bank Connector** | India Banking | Stores API credentials (URL, key, secret) per company–bank pair |
| **India Banking Settings** | India Banking | Global config: status-check interval, log retention, workflow toggle |
| **Mode of Transfer** | India Banking | NEFT / RTGS / IMPS / A2A with amount limits, priority, and bank-specific rules |
| **Payment Type** | India Banking | Maps a payment category to a debit account per company |
| **Payment Order Summary** | India Banking | One row per party in a Payment Order; tracks `payment_status`, UTR, payment date |
| **India Banking Request Log** | India Banking | Full API request/response audit trail; auto-purged after `stale_days` |
| **Payment Notification** | India Banking | Stores inbound bank webhook/notification events |
| **Unreconcile Bank Payment** | India Banking | Reverse reconciliation and unlink Payment Order Summary on submit |

---

## Payment Request Status Lifecycle

```
Draft → Submitted → Initiated → (via Payment Order) → Processed
                                                    ↘ Failed
```

## Payment Order Status Lifecycle

```
Pending → Initiated → Processed
                   ↘ Failed (partial or full)
```

---

## Supported Banks

| Bank | Mode |
|---|---|
| ICICI Bank | Bulk (file + OTP) and Individual |
| HDFC Bank | Individual |
| Yes Bank | Individual |
| Axis Bank | Individual |
| Kotak Bank | Individual |
| Bank of Baroda | Individual |
