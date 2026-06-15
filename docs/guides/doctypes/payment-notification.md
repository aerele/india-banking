# Payment Notification

## Overview

Payment Notification is a child doctype that holds the email configuration used to notify a party after their payment is processed. It is stored as a child table on the **India Banking Connector** and is only active when the connector has `notify_party` enabled.

When a payment status is updated to `Processed`, the connector sends an email to the party with a PDF of the Payment Entry attached.

---

## Fields

| Field | Fieldname | Purpose |
|---|---|---|
| Company | `company` | The company this notification config applies to |
| Email Format | `email_format` | Print format used to generate the PDF attachment — must be a Payment Entry print format |
| Letter Head | `letter_head` | Letter head applied to the PDF |
| CC | `cc` | Comma-separated email addresses to CC on every notification |

---

## How It Works

Notifications are triggered inside `_notify_party()` on the India Banking Connector after a payment summary row's status updates to `Processed`.

The send logic:

1. Looks up the Payment Entry linked to the summary row
2. Fetches the `Payment Notification` record matching `company = payment_entry.company`
3. Sends an email to the party's email address — taken from the summary row's `email` field, falling back to the `email` field on the party's Bank Account
4. Attaches a PDF of the Payment Entry, rendered using the configured `email_format` (or the default Payment Entry print format if none is set), with the configured `letter_head`
5. CCs any addresses in the `cc` field

If no matching `Payment Notification` record is found for the company, no email is sent. Errors during send are swallowed silently to avoid blocking the payment status update flow.

---

## Configuration

Payment Notification records are configured on the **India Banking Connector** form, under the **Payment Notifications** section:

1. Enable **Notify Party** on the connector
2. Add one or more rows to the **Payment Notification** child table — one per company
3. For each row, set the Email Format (must be a `Payment Entry` print format — enforced by the field query in India Banking Settings JS), Letter Head, and CC addresses

The `email_format` field query is filtered to only show print formats where `doc_type = Payment Entry`.

---

## Key Files

| File | Purpose |
|---|---|
| `india_banking/india_banking/doctype/payment_notification/payment_notification.json` | Field definitions |
| `india_banking/india_banking/doctype/india_banking_connector/india_banking_connector.py` (`_notify_party`) | Send logic triggered after payment status update |
| `india_banking/india_banking/doctype/india_banking_settings/india_banking_settings.js` | Filters `email_format` field to Payment Entry print formats |
