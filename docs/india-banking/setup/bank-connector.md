# Bank Connector

The **Bank Connector** is the bridge between ERPNext and your bank's API. You need one connector per **Company–Bank Account** combination.

<!-- PLACEHOLDER: bank-connector-form.png
     Description: Screenshot of a filled Bank Connector form in ERPNext, showing
     the Company, Bank Account, URL, API Key fields filled in for ICICI Bank,
     with the Bulk Transaction checkbox checked.
     Suggested size: 900×600px -->

---

## Creating a Bank Connector

**Go to:** India Banking > Setup > Bank Connector > New

Fill in the following fields:

| Field | Description |
|---|---|
| **Company** | The ERPNext Company that owns this bank account |
| **Bank Account** | The company's bank account (must be a company account) |
| **Bank** | Auto-fetched from the Bank Account |
| **URL** | The base URL where `india_banking_connector` is installed (e.g., `https://connector.yourcompany.com`) |
| **API Key** | API key of the connector site user |
| **API Secret** | API secret of the connector site user |
| **Bulk Transaction** | Enable for banks that use file-based (bulk) payment mode — ICICI, IDFC First, Axis, Canara |
| **Integration Mode** | Select the bank's API integration mode |
| **Same Site** | *(Beta)* Enable if the connector is installed on the same Frappe site |

> **Important:** The API Key and Secret are credentials for the `india_banking_connector` Frappe site, not your bank credentials. The connector app manages the actual bank API authentication.

---

## Testing the Connection

After saving the connector, go to a **Company Bank Account** form and click:

**Fetch > Bank Balance**

If the balance is returned successfully, the connector is working correctly.

<!-- PLACEHOLDER: bank-connector-test.gif
     Description: Screen recording showing a user clicking "Fetch > Bank Balance" on a
     Bank Account form and seeing the live balance displayed in a popup dialog.
     Suggested size: 900×500px, GIF duration ~5 seconds -->

---

## One Connector per Bank Account

If your company has multiple bank accounts at the same bank, create a separate Bank Connector for each account. The connector is always looked up by **company + bank account**, not just by company or bank.
