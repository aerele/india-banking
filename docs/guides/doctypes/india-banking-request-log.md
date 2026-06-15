# India Banking Request Log

## Overview

India Banking Request Log records every HTTP call made by an India Banking Connector to a bank API. Each log entry captures the full request and response — URL, method, headers, payload, response body, and HTTP status code — along with a reference to the document that triggered the call. It is the primary audit trail for diagnosing payment failures and API issues.

---

## Fields

| Field | Fieldname | Purpose |
|---|---|---|
| Action | `action` | Label describing what the API call was doing (e.g. `initiate_payment`, `get_status`) |
| URL | `url` | Full URL of the API request |
| Method | `method` | HTTP method — `GET`, `POST`, etc. |
| Header | `header` | Request headers, JSON-formatted with indent |
| Payload | `payload` | Request body sent to the bank API, JSON-formatted |
| Response | `response` | Raw response from the bank API, JSON-formatted |
| Status Code | `status_code` | HTTP status code returned by the bank |
| Reference Doctype | `reference_doctype` | Doctype of the document that triggered the call |
| Reference Docname | `reference_docname` | Name of the document that triggered the call |
| Show Failure Message | `show_failure_message` | Button — parses the response and displays a human-readable error message |

---

## Log Creation

Logs are created by `create_api_log()` in `india_banking_request_log.py`, called from the India Banking Connector after every bank API response:

```
create_api_log(response, action="initiate_payment", ref_doctype="Payment Order", ref_docname="PO-0001")
```

Only `requests.Response` objects are accepted — non-response inputs are ignored. Errors during log creation are written to Frappe's Error Log and do not propagate.

---

## Log Retention

Logs are automatically cleared after **60 days** via Frappe's `default_log_clearing_doctypes` hook (`hooks.py`). The `clear_old_logs()` method on the doctype handles the deletion using a QueryBuilder date comparison.

---

## Failure Message

The **Show Failure Message** button on each log record calls `extract_error_message()` from `india_banking.utils`, which parses the bank API's error response and displays a user-readable message. This avoids having to manually read raw JSON in the response field.

---

## Key Files

| File | Purpose |
|---|---|
| `india_banking/india_banking/doctype/india_banking_request_log/india_banking_request_log.py` | `create_api_log()`, `clear_old_logs()`, failure message handler |
| `india_banking/india_banking/doctype/india_banking_connector/india_banking_connector.py` | Calls `create_api_log` after every bank API request |
| `india_banking/hooks.py` | `default_log_clearing_doctypes` — sets 60-day retention |
| `india_banking/utils.py` | `extract_error_message()` — parses bank error responses |
