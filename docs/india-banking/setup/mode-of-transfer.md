# Mode of Transfer

A **Mode of Transfer** defines a payment method (NEFT, RTGS, IMPS, A2A) along with its allowed amount range, operating hours, and priority. India Banking uses this to automatically assign the correct payment mode when building a Payment Order summary.

<!-- PLACEHOLDER: mode-of-transfer-list.png
     Description: Screenshot of the Mode of Transfer list view showing default entries:
     IMPS (₹1–₹2,00,000), RTGS (₹2,00,000–₹50,00,00,000), NEFT, and A2A/FT/Internal,
     each with their priority and status.
     Suggested size: 900×400px -->

---

## Default Modes of Transfer

India Banking installs the following defaults on first install:

| Mode | Min Amount | Max Amount | Priority | Notes |
|---|---|---|---|---|
| A2A / FT / Internal | ₹1 | ₹50 Cr | 1 | Same-bank transfers only |
| IMPS | ₹1 | ₹2,00,000 | 2 | 24×7, fastest |
| RTGS | ₹2,00,000 | ₹50 Cr | 3 | High-value, requires LEI for >₹50 Cr |
| NEFT | ₹1 | ₹50 Cr | 4 | Batch settlement |

---

## Creating a Mode of Transfer

**Go to:** India Banking > Setup > Mode of Transfer > New

| Field | Description |
|---|---|
| **Mode** | Name of the transfer mode (e.g., NEFT, RTGS, IMPS) |
| **Minimum Limit** | Minimum payment amount allowed for this mode |
| **Maximum Limit** | Maximum payment amount allowed for this mode |
| **Start Time** | Operating window start time |
| **End Time** | Operating window end time |
| **Priority** | Lower number = higher priority when auto-assigning |
| **Is Bank Specific** | Enable if this mode applies only to same-bank (A2A) transfers |
| **Bank** | The specific bank this mode applies to (only if Is Bank Specific is checked) |
| **Bank Account** | Optional — restrict to a specific bank account |
| **Disabled** | Disables the mode from being auto-assigned |

---

## How Auto-Assignment Works

When you click **Get Summary** on a Payment Order, India Banking automatically assigns a Mode of Transfer to each summary row:

1. **Same-bank transfers** — Looks for a Mode of Transfer with **Is Bank Specific** enabled and matching bank. Assigns it if found.
2. **Cross-bank transfers** — Picks the highest-priority mode whose **Min–Max range** covers the payment amount.

<!-- PLACEHOLDER: mode-assignment.gif
     Description: Short screen recording showing a user clicking "Get Summary" on a Payment Order
     and watching the Mode of Transfer column auto-populate for each row based on amount.
     Suggested size: 900×450px, GIF duration ~4 seconds -->

---

## RTGS and LEI Number

For RTGS payments exceeding ₹50 Crore, RBI mandates a **Legal Entity Identifier (LEI)** for the payee. India Banking enforces this automatically — if the Supplier's LEI Number field is empty and the payment exceeds the threshold, submission is blocked.

**To add LEI:** Open the Supplier record > LEI Number field.
