# Bank Account & Approval Workflow

## Setting Up Supplier Bank Accounts

Before you can pay a supplier through India Banking, they must have a **default Bank Account** in ERPNext.

**Go to:** Accounting > Masters > Bank Account > New

Fill in:
- **Account Name** — Supplier's account holder name
- **Bank** — Select the bank
- **Bank Account No** — Account number
- **IFSC Code** — India Banking validates this automatically on save
- **Party Type** — Supplier
- **Party** — Select the supplier
- **Is Default** — Check this so it is auto-selected on Payment Requests

<!-- PLACEHOLDER: supplier-bank-account-form.png
     Description: Screenshot of a Bank Account form for a Supplier, with IFSC Code filled in
     and the "Is Default" checkbox checked. The Party Type is set to "Supplier".
     Suggested size: 900×550px -->

---

## IFSC Validation

When you save a Bank Account, India Banking automatically validates the IFSC code format. An invalid code will block saving.

> **Format:** 11 characters — first 4 letters (bank code) + 0 + 6 alphanumeric characters. Example: `ICIC0001234`

---

## Bank Account Approval Workflow

If **Activate Workflow on Bank Account** is enabled in India Banking Settings, every new bank account goes through an approval process before it can be used in payments.

### Workflow States

```
New/Pending → Approved
           → Rejected
```

### How It Works

1. When a new Bank Account is saved, it enters **Pending** state.
2. A user with the **Payment Manager** role reviews and either **Approves** or **Rejects** it.
3. Only **Approved** bank accounts appear in the bank account selector on Payment Requests.

<!-- PLACEHOLDER: bank-account-workflow.gif
     Description: Screen recording showing a Bank Account in "Pending" state,
     a manager clicking "Approve", the state changing to "Approved" with a green indicator,
     and then the account appearing in a Payment Request bank account dropdown.
     Suggested size: 900×500px, GIF duration ~6 seconds -->

### Why Use the Approval Workflow?

The approval workflow prevents payments to unverified or fraudulently added bank accounts — a common compliance requirement in Indian corporate finance (Maker–Checker control).

---

## Company Bank Account

Your **company's own bank account** must also be set up in ERPNext with:
- **Is Company Account** = checked
- A corresponding **Bank Connector** pointing to this account

The company bank account is selected on the Payment Order and determines which bank connector (and therefore which bank's API) is used for initiating payments.
