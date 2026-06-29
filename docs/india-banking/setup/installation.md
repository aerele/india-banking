# Installation & Prerequisites

## Prerequisites

Before installing India Banking, ensure the following are in place:

- ERPNext v15 installed and configured
- `india_banking_connector` app installed (provides the bank API middleware)
- A **static IP address** approved by your bank for outbound API calls
- SSL certificate configured on your server
- Bank API credentials obtained from your bank (API key, secret, and endpoint URL)

> **Note:** Each bank has its own onboarding process for API access. Contact your relationship manager to obtain sandbox and production credentials before setting up the connector.

---

## Installing the App

Run the following commands from your bench directory:

```bash
bench get-app india_banking
bench --site your-site.com install-app india_banking
bench migrate
```

After install, India Banking automatically:
- Creates custom fields on Payment Request, Payment Order, Bank Account, Supplier, and Journal Entry
- Sets up default Modes of Transfer (IMPS, RTGS, NEFT, A2A)
- Creates a default Payment Type
- Adds a **Bank Account Approval** workflow (optional, can be enabled in Settings)
- Creates a **Payment Manager** role

---

## Post-Install Checklist

- [ ] Open **India Banking Settings** and configure the status check frequency
- [ ] Create a **Bank Connector** for each company–bank combination
- [ ] Create **Mode of Transfer** entries or verify the defaults suit your bank limits
- [ ] Create a **Payment Type** for each payment category (e.g., Vendor Payments, Salary)
- [ ] Set a default bank account on each Supplier you will pay via India Banking

<!-- PLACEHOLDER: post-install-checklist.png
     Description: Screenshot of the ERPNext desk after India Banking installation,
     showing the India Banking module card and the Settings shortcut highlighted.
     Suggested size: 900×500px -->
