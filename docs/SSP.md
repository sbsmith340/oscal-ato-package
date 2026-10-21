# Field Inspection Portal (FIP) - System Security Plan summary

Generated from `source/*.yaml` by `tools/build.py`. The authoritative machine-readable SSP is [`oscal/ssp.json`](../oscal/ssp.json). Fictional system for demonstration.

## System characteristics

**Description.** The Field Inspection Portal (FIP) lets inspectors of the (fictional) Office of Facility Standards schedule site inspections, record findings on mobile devices, and publish compliance letters to facility operators. It is a multi-tier web application hosted in a commercial Azure region and operated by Fabrikam Digital Services under contract.

**Authorization boundary.** The authorization boundary contains the FIP web front end (Azure App Service), the API tier (Azure App Service), the Azure SQL Database holding inspection records, the Azure Key Vault holding application secrets and keys, the Azure Front Door instance with Web Application Firewall, and the administrative workstations used to operate the system. Microsoft Entra ID, Azure platform services, Microsoft Sentinel and Defender for Cloud are external, FedRAMP authorized services leveraged by the system and are outside the boundary.

**Network architecture.** All inbound traffic terminates at Azure Front Door (WAF in prevention mode). The web and API tiers are reachable only from Front Door via service tags and access restrictions. The database and Key Vault expose private endpoints only; public network access is disabled. Administrative access uses Entra ID Privileged Identity Management and Intune-compliant workstations; there is no inbound RDP or SSH.

## Security categorization (FIPS 199)

| Information type | C | I | A |
|---|---|---|---|
| Inspection Records | Moderate | Moderate | Low |
| Facility Operator Contact Information (PII) | Moderate | Moderate | Low |
| Compliance Determinations | Low | Moderate | Moderate |
| Security and Audit Data | Moderate | Moderate | Low |
| **System (high-water mark)** | **Moderate** | **Moderate** | **Moderate** |

## Control implementation

24 controls from the NIST SP 800-53 Rev 5 MODERATE baseline.

| Control | Title | Status | Components |
|---|---|---|---|
| AC-2 | Account Management | Implemented | Microsoft Entra ID (leveraged), Field Inspection Portal |
| AC-2(3) | Disable Accounts | Implemented | Microsoft Entra ID (leveraged) |
| AC-6 | Least Privilege | Implemented | Microsoft Entra ID (leveraged) |
| AC-17 | Remote Access | Implemented | Microsoft Entra ID (leveraged) |
| AU-2 | Event Logging | Implemented | Log Analytics and Microsoft Sentinel (leveraged) |
| AU-6 | Audit Record Review, Analysis, and Reporting | Implemented | Log Analytics and Microsoft Sentinel (leveraged) |
| AU-11 | Audit Record Retention | Partial | Log Analytics and Microsoft Sentinel (leveraged) |
| CA-7 | Continuous Monitoring | Implemented | Microsoft Defender for Cloud (leveraged) |
| CM-6 | Configuration Settings | Partial | CI/CD pipeline (GitHub Actions) |
| CM-7 | Least Functionality | Implemented | Azure App Service (web and API tiers) |
| CM-8 | System Component Inventory | Implemented | Field Inspection Portal |
| CP-9 | System Backup | Partial | Azure SQL Database |
| IA-2(1) | Multi-factor Authentication to Privileged Accounts | Implemented | Microsoft Entra ID (leveraged) |
| IA-2(2) | Multi-factor Authentication to Non-privileged Accounts | Implemented | Microsoft Entra ID (leveraged) |
| IA-5 | Authenticator Management | Implemented | Azure Key Vault |
| IR-4 | Incident Handling | Implemented | Log Analytics and Microsoft Sentinel (leveraged) |
| IR-6 | Incident Reporting | Partial | Field Inspection Portal |
| RA-5 | Vulnerability Monitoring and Scanning | Partial | Microsoft Defender for Cloud (leveraged), CI/CD pipeline (GitHub Actions) |
| SC-7 | Boundary Protection | Implemented | Azure Front Door with WAF, Azure SQL Database |
| SC-8 | Transmission Confidentiality and Integrity | Implemented | Azure App Service (web and API tiers) |
| SC-13 | Cryptographic Protection | Implemented | Azure Key Vault |
| SC-28 | Protection of Information at Rest | Implemented | Azure SQL Database |
| SI-2 | Flaw Remediation | Implemented | Azure App Service (web and API tiers) |
| SI-4 | System Monitoring | Partial | Log Analytics and Microsoft Sentinel (leveraged) |

## Implementation statements

### AC-2 Account Management
- **Microsoft Entra ID (leveraged)** (implemented): Accounts are created only from approved access requests in the agency ticketing system and provisioned to role-based Entra ID groups. Group membership is reviewed quarterly through Entra ID Access Reviews by the System Owner; denied or unreviewed access is removed automatically.
- **Field Inspection Portal** (implemented): Application roles (Inspector, Facility Operator, Administrator) are mapped from Entra ID group claims; the application holds no local accounts.

### AC-2(3) Disable Accounts
- **Microsoft Entra ID (leveraged)** (implemented): Accounts are disabled within 24 hours of a termination notice through HR-driven lifecycle workflows, and accounts inactive for 90 days are disabled automatically. Deprovisioning time is measured monthly against the 24-hour target.

### AC-6 Least Privilege
- **Microsoft Entra ID (leveraged)** (implemented): Administrative roles are eligible-only in Privileged Identity Management with approval, justification and a 4-hour maximum activation. No user holds standing production database access.

### AC-17 Remote Access
- **Microsoft Entra ID (leveraged)** (implemented): Remote administrative access requires Conditional Access with phishing-resistant MFA and an Intune-compliant device. No VPN or inbound RDP/SSH paths exist into the boundary.

### AU-2 Event Logging
- **Log Analytics and Microsoft Sentinel (leveraged)** (implemented): Diagnostic settings enforced by Azure Policy send App Service HTTP and audit logs, SQL auditing, Key Vault audit events, Front Door WAF logs, Entra ID sign-in and audit logs, and Azure Activity logs to the Log Analytics workspace.

### AU-6 Audit Record Review, Analysis, and Reporting
- **Log Analytics and Microsoft Sentinel (leveraged)** (implemented): Microsoft Sentinel analytics rules generate incidents for defined events (privileged role activation outside PIM, mass deletion, WAF blocks above threshold, failed sign-in bursts). The ISSO reviews open incidents daily and produces a weekly audit review summary for the System Owner.

### AU-11 Audit Record Retention
- **Log Analytics and Microsoft Sentinel (leveraged)** (partial): Interactive retention is 90 days in Log Analytics. Long-term archive to meet the agency's one-year retention requirement is not yet configured (see POA&M).

### CA-7 Continuous Monitoring
- **Microsoft Defender for Cloud (leveraged)** (implemented): Defender for Cloud continuously assesses the subscription against the NIST SP 800-53 Rev 5 regulatory compliance standard. The ISSO reports compliance score, open recommendations and POA&M status to the System Owner monthly.

### CM-6 Configuration Settings
- **CI/CD pipeline (GitHub Actions)** (partial): Configuration baselines are defined as infrastructure as code and deployed only through the pipeline. Automated drift detection between deployed resources and code is not yet in place (see POA&M).

### CM-7 Least Functionality
- **Azure App Service (web and API tiers)** (implemented): FTP/FTPS and remote debugging are disabled, HTTPS only is enforced, and only the ports required by the application are exposed through Front Door.

### CM-8 System Component Inventory
- **Field Inspection Portal** (implemented): The system inventory is generated from Azure Resource Graph on each deployment and reconciled monthly against the authorization boundary; untagged or unexpected resources raise a Defender for Cloud recommendation.

### CP-9 System Backup
- **Azure SQL Database** (partial): Automated backups with point-in-time restore (35 days) and geo-redundant backup storage are enabled. A documented restore test has not yet been performed (see POA&M).

### IA-2(1) Multi-factor Authentication to Privileged Accounts
- **Microsoft Entra ID (leveraged)** (implemented): Conditional Access requires phishing-resistant MFA (FIDO2 security keys or Windows Hello for Business) for all privileged accounts.

### IA-2(2) Multi-factor Authentication to Non-privileged Accounts
- **Microsoft Entra ID (leveraged)** (implemented): Conditional Access requires MFA for all non-privileged users; legacy authentication protocols are blocked tenant-wide.

### IA-5 Authenticator Management
- **Azure Key Vault** (implemented): Application-to-service authentication uses managed identities, so no passwords or connection strings are stored in code. Remaining secrets live in Key Vault with RBAC, soft delete, purge protection and 90-day rotation.

### IR-4 Incident Handling
- **Log Analytics and Microsoft Sentinel (leveraged)** (implemented): Incidents are handled per the FIP Incident Response Plan (prepare, detect and analyze, contain, eradicate, recover, post-incident review). Sentinel playbooks automate enrichment and containment steps such as session revocation.

### IR-6 Incident Reporting
- **Field Inspection Portal** (partial): Suspected incidents are reported to the agency SOC within one hour of detection. The procedure for reporting to US-CERT/CISA through the agency is drafted but not yet exercised (see POA&M).

### RA-5 Vulnerability Monitoring and Scanning
- **Microsoft Defender for Cloud (leveraged)** (implemented): Defender Vulnerability Management scans hosts and Defender for SQL assesses the database continuously. Remediation SLAs are Critical 15 days, High 30 days, Moderate 90 days, tracked weekly.
- **CI/CD pipeline (GitHub Actions)** (planned): Software composition analysis and container image scanning in the pipeline are planned (see POA&M).

### SC-7 Boundary Protection
- **Azure Front Door with WAF** (implemented): Front Door with WAF (managed rule set, prevention mode) is the only public entry point. App Service access restrictions accept traffic only from the Front Door service tag with the instance's header ID.
- **Azure SQL Database** (implemented): Public network access is disabled; the database is reachable only through a private endpoint in the application virtual network.

### SC-8 Transmission Confidentiality and Integrity
- **Azure App Service (web and API tiers)** (implemented): HTTPS only with minimum TLS 1.2 is enforced end to end, from client to Front Door to App Service.

### SC-13 Cryptographic Protection
- **Azure Key Vault** (implemented): Cryptographic operations use FIPS 140-validated modules provided by the Azure platform; keys are RSA 3072 or stronger.

### SC-28 Protection of Information at Rest
- **Azure SQL Database** (implemented): Transparent Data Encryption uses a customer-managed key held in Key Vault with automatic rotation. Storage accounts use platform encryption with infrastructure encryption enabled.

### SI-2 Flaw Remediation
- **Azure App Service (web and API tiers)** (implemented): Platform patching is performed by Azure. Application dependencies are updated through Dependabot pull requests; Critical and High fixes follow the RA-5 SLAs.

### SI-4 System Monitoring
- **Log Analytics and Microsoft Sentinel (leveraged)** (implemented): Sentinel monitors identity, platform and application telemetry with scheduled analytics rules mapped to MITRE ATT&CK; Defender for Cloud workload protections provide threat detection for App Service, SQL and Key Vault.
- **Log Analytics and Microsoft Sentinel (leveraged)** (planned): User and entity behavior analytics (UEBA) for anomaly detection is planned (see POA&M).
