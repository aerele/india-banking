# Client / Frontend DocTypes

The main DocTypes for the configuration of India Banking through the frontend are:

## Bank Connector

A Bank Connector is the communication channel between the frontend the backend for a company bank account. This means that a Bank Connector should be created for every company bank account that is used to transact *from*, and there can be **only one** Connector per company bank accont.

> [!IMPORTANT]
> Despite what the name might imply, a Bank Connector **does not** communicate with the bank's servers. It is only to signify that the Connector is for a Bank account.
>
> However, the creation of a Bank Connector is the first step in the bank API integration process, but the prerequisite for this is an account on the backend whose credentials will be used to communicate with it.
>
> A user should be created on the **backend** for a Bank Connector to work. A Bank Connector uses Frappe's Token Based Authentication using API Key and API Secret to communicate. [Frappe's guide](https://docs.frappe.io/framework/user/en/api/rest) can be used to generate the API Key and Secret on the backend instance for a user.
>
> If the backend and frontend are on the same instance, the credentials of a user created on that instance can be used.

### Fields

A Bank Connector uses the following field values to communicate with the backend:

#### Details

- **Company**: The company whose bank account is to be used in the transactions by this connector.
- **Bank Account**: The Bank Account for which this connector is to be created.
- **Bank**: The bank to which the Bank Account belongs. This is automatically poulated when the Bank Account is selected.
- **URL**: The base URL with the backend instance's hostname or IP address. e.g.: https://backend.myerpserver.com or https://192.168.0.1.
- **API Key**: The API Key of the user **created on the backend instance** on whose behalf the requests will be done from the frontend.
- **API Secret**: The API Secret of the user **created on the backend instance** on whose behalf the requests will be done from the frontend.
- **Bulk Transaction**: If this Bank Connector is used for bulk transactions or not.

#### Payment Configuration

- **Enqueue large payments in the background**: Check this option if there are a large number of payments to be made. This option makes the frontend app queue the payments to be done using background workers without blocking the request thread.
- **Enable Payment Delay**: Check this option if you want to add a delay between the API calls sent to the bank's servers. Doing so will space out each call by the number of seconds specified in *Payment Call Interval*. This option should be used to avoid hitting the rate limits set by the bank servers.

## India Banking Settings

The India Banking module can be configured using this DocType. Various settings such as entities to be automatically updated, payment notifications, etc. can be configured in India Banking Settings.

## Mode of Transfer

Mode of Transfer is a new DocType added by the India Banking frontend to capture the type of mode of wire transfer. The Modes of Transfer included in India Banking are: NEFT, IMPS, RTGS, and A2A. Each Mode of Transfer has an upper and lower limit associated with it.

Additionally, a variety of extensions to the existing DocTypes are also made to the existing DocTypes such as:

## Payment Order

- Payment Summary inside a Payment Order to track individual payment line items within a Payment Order. These summary items have statuses on them that are updated based on the responses from the bank.
- Getting payments from Bank Entries in addition to Payment Requests and Payment Entries.

## Payment Request

- Creating Payment Requests in bulk by selecting multiple Purchase Invoices from the list.
- The ability to create an ad hoc Payment Request from the Payment Entry list.
