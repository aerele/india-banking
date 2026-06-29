# India Banking Settings

**Go to:** India Banking > Settings > India Banking Settings

India Banking Settings is a single-record configuration form that controls global behaviour across the application.

<!-- PLACEHOLDER: india-banking-settings.png
     Description: Full screenshot of the India Banking Settings form showing all tabs:
     Basic Configuration, Auto Update Configurations, Payment Notifications, and DocType Configuration.
     Suggested size: 900×700px -->

---

## Basic Configuration

| Setting | Description |
|---|---|
| **Summarise Payment Based On** | Controls how Payment Order summary rows are grouped — by **Party** (one row per supplier) or by **Voucher** (one row per invoice) |
| **Activate Workflow on Bank Account** | When enabled, a bank account must be **Approved** through the approval workflow before it can be used in a Payment Request |
| **Allowed Payment Doctypes** | The document types from which Payment Orders can be created (e.g., Payment Request, Payment Entry, Journal Entry) |
| **Show Bank Balance in Payment Order** | Displays the live company bank balance on the Payment Order form |
| **Enable Bank Balance Validation** | Prevents submitting a Payment Order if the bank balance is insufficient |
| **Allow Future-Dated Payment Orders** | When enabled, allows payment orders with a posting date in the future |
| **Use Payment Order Date as Payment Entry Date** | When enabled, the Payment Entry posting date is set to the Payment Order date rather than today |

---

## Auto Update Configurations

| Setting | Description |
|---|---|
| **Auto Update Payment Status** | When enabled, a scheduled job automatically polls the bank for payment status |
| **Status Check Frequency** | How often to poll — **Every 20 Minutes**, **Every Hour**, or **Every Day at Midnight** |
| **Retry Period (in Days)** | Number of days to continue retrying status checks for Initiated payments before giving up |

> **Tip:** For high-volume operations, set frequency to **Every 20 Minutes**. For low-volume, **Every Hour** is sufficient and reduces API call costs.

---

## Payment Notifications

| Setting | Description |
|---|---|
| **Notify Party** | When enabled, sends an email/SMS notification to the supplier/employee when their payment is processed |

---

## DocType Configuration

| Setting | Description |
|---|---|
| **Doctype Naming Series** | Configure custom naming series for Payment Request and Payment Order documents |
| **Process Payments in Background** | Run payment initiation as a background job (recommended for bulk payments to avoid browser timeouts) |

---

## Recommended Settings for Production

```
Summarise Payment Based On   : Party
Auto Update Payment Status   : Enabled
Status Check Frequency       : Every Hour
Activate Workflow on Bank    : Enabled (for payment controls)
Enable Bank Balance Validation: Enabled
Process Payments in Background: Enabled
```
