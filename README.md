# India Banking Integration for ERPNext

## Introduction

Integrating banking payments into ERPNext streamlines financial management, making it easier to pay vendors, employees, handle payroll, and reconcile bank statements (if supported by the bank). This automation reduces manual processing errors and simplifies payment entries.

Currently, this integration is available with select Indian banks, and it is accessible to account holders upon request. After a year of efforts to gain API access, we've identified current account holders with good transactional histories. As banks offer more robust APIs and simplify the API access process, we are developing a custom Frappe app called **India Banking** to facilitate this integration.

The ERPNext banking payment flow and necessary customizations are handled within the India Banking app, which connects to the available server-side apps. 

Due to strict bank security requirements (static IPs, certificates, and specific environments), the server-side app structure is essential. 

### Deployment Options

- **Private Benches or Dedicated Servers**: Install both the India Banking client and server app on the same site if a static IP is available.
- **Shared Benches**: Install the India Banking client app on a Frappe Cloud site and manage certificates and keys on a hosted server with a static IP.
- **On-Premise Setup**: Install both the client and server-side apps on the same site.

### Supported Banks and Status
- **ICICI Bank Server App**: API integration live.
- **HDFC Bank Server App**: API integration live.
- **Yes Bank Server App**: API integration live.
- **Axis Bank Server App**: API integration live.
- **Kotak Mahindra Bank Server App**: Latest API access available, awaiting go-live.
- **SBI Server App**: Awaiting API access.
- **Standard Chartered Bank Server App**: Awaiting API access.

## Bank-Specific Features

### ICICI Bank
- **Transfers**: IMPS, NEFT, RTGS, Internal Transfer (Single API with portal authorization).
- **Bulk Transfers**: NEFT (Bulk API with single OTP and portal authorization).
- **Encryption**: AES, RSA.

### HDFC Bank
- **Transfers**: IMPS, NEFT, RTGS, A2A (Single API with and without portal authorization).
- **Encryption**: (AES, RSA, Signature Validation) or JSON Object Signing and Encryption - application/jose 

### Yes Bank
- **Transfers**: IMPS, NEFT, RTGS, A2A (Single API without portal authorization).
- **Encryption**: Signature Validation.

### Axis Bank
- **Transfers**: IMPS, NEFT, RTGS, A2A (Single API with and without portal authorization).
- **Encryption**: Checksum Validation, AES (Key provided by the bank).

### Kotak Mahindra Bank
- **Transfers**: IMPS, NEFT, RTGS, A2A (Single API with and without portal authorization).
- **Encryption**: AES, RSA.

## Future Plans

We plan to develop a self-help support portal to assist account holders in providing technical information required by the banks. This portal will include support-related details and a user guide wiki.

## Contact

For more details or assistance, feel free to reach out:

**Vignesh Sekar**  
Phone: +91-7790844832  
Email: [vignesh@aerele.in](mailto:vignesh@aerele.in)
