# Offensive Playbook: Open Redirect & CORS Misconfiguration

## 1. Overview & Attack Surface
Open redirects turn trusted domains into phishing launchpads (OAuth `redirect_uri` theft,
token leakage via `Referer`); permissive CORS (`Access-Control-Allow-Origin: <attacker>`
+ `Allow-Credentials: true`) lets attacker JavaScript read cross-origin responses.

## 2. Classification & Detection
### A. Open redirect parameters
Fuzz `?next=`, `?redirect=`, `?url=`, `?return=`, `?continue=`, OAuth `redirect_uri`:
- `?next=https://evil.example` (absolute), `?next=//evil.example` (protocol-relative),
  `?next=/\\/evil.example`, `?next=https://target.evil.example` (subdomain confusion).
- Confirm 30x to attacker host: `curl -sI "<target>/login?next=https://evil.example" | grep -i '^location'`.

### B. CORS misconfiguration
Send `Origin: https://evil.example` and inspect:
- Reflected `Access-Control-Allow-Origin: https://evil.example` (+ `Allow-Credentials: true`) = exploitable.
- `Access-Control-Allow-Origin: null` + credentials = exploitable via sandboxed iframe.
- `Vary: Origin` absent + `*` cached = cache-poisoning angle (note as Probable).
Probe: `curl -sI -H "Origin: https://evil.example" <target>/api/me | grep -i 'access-control'`.

### C. Impact chaining
Redirect + OAuth = code/token theft. CORS + authenticated JSON API = account takeover
read primitive. Always name the chained impact in the finding, not just the primitive.

## 3. Sandbox Automated Validation
```bash
curl -sI "TARGET/login?next=https://evil.example" | grep -i '^location'
curl -s -H "Origin: https://evil.example" -I TARGET/api/me | grep -i 'access-control-allow'
```

## 4. Verification & Reporting
1. Redirect: 30x `Location` to attacker host = Confirmed. CORS: reflected origin
   WITH credentials on an authenticated endpoint = Confirmed (anonymous public
   endpoint reflection alone = Probable).
2. File finding via `create_vulnerability_report`:
   - **Category**: Open Redirect / CORS (OWASP A01:2021)
   - **CWE**: CWE-601 (Open Redirect), CWE-942 (Permissive CORS)
   - **CVSS 3.1**: `AV:N/AC:L/PR:N/UI:R/S:C/C:L/I:L/A:N` (Base 6.1 Medium; higher with OAuth/token chain)
   - **Remediation**: Strict allowlist for redirect targets (IDs, not URLs); CORS
     allowlist of exact origins, never reflect + credentials, `Vary: Origin`.
