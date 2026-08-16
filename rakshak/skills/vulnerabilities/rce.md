# Offensive Playbook: Remote Code Execution (RCE) & Command Injection

## 1. Overview & Attack Surface
Remote Code Execution (RCE) and OS Command Injection occur when an application passes unsanitized user input directly to a system shell (e.g. `system()`, `exec()`, `popen()`, `subprocess.Popen(shell=True)`) or evaluates untrusted code dynamically.

## 2. Common Attack Vectors & Shell Metacharacters
- Command Separators: `;`, `&`, `&&`, `|`, `||`, `\n`
- Command Substitution: `` `whoami` ``, `$(id)`, `${IFS}`
- Argument Injection: `--output=/var/www/html/shell.php`

## 3. Heuristic Probing & Blind Timing Confirmation

### A. Direct Output Probing
```bash
https://target.local/api/tools/ping?host=127.0.0.1;id
https://target.local/api/tools/dns?domain=google.com|cat /etc/passwd
```

### B. Blind Time Delay Injection (PoC Verification)
When output is not rendered in the response, verify execution through sleep delays:
```bash
https://target.local/api/convert?input=file.txt;sleep 5
```
Verify via `time curl -s "..."` inside the sandbox to confirm 5-second response delay.

### C. File Upload to Web Shell (Polyglot Exploitation)
If application accepts file uploads and stores them in a web-accessible directory:
1. Upload minimal web shell (e.g. `shell.php`, `shell.phtml`, `shell.jsp`, `shell.aspx`).
2. If extension is restricted, test bypasses:
   - Double extensions: `exploit.php.png` or `exploit.png.php`
   - Null byte: `exploit.php%00.png`
   - Case manipulation: `exploit.PhP` or `exploit.pHP5`
   - `.htaccess` override to enable PHP execution on `.png` files.

## 4. Verification & Reporting
1. Confirm arbitrary OS command execution (e.g. output of `id` or `uname -a`).
2. File finding via `create_vulnerability_report`:
   - **Category**: Injection / Server-Side Execution (OWASP A03:2021)
   - **CWE**: CWE-78 / CWE-94
   - **CVSS 3.1**: `AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H` (Base 9.8 Critical)
   - **Remediation**: Avoid system shell invocations; use parameterized argument lists without shell wrappers.
