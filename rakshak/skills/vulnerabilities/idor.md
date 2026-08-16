# Offensive Playbook: Insecure Direct Object References (IDOR) & Broken Object Level Auth (BOLA)

## 1. Overview & Attack Surface
IDOR / BOLA occurs when an application exposes a reference to an internal object (e.g. user ID, document ID, order UUID) in requests without validating whether the requesting user possesses authorization to access that object.

## 2. Reconnaissance & Target Identification
1. Inspect API traffic via Caido (`list_requests`) for endpoints containing entity identifiers:
   - `/api/v1/users/{id}/profile`
   - `/api/orders/{order_id}`
   - `/api/documents/download?id=1042`
   - GraphQL queries: `query { getInvoice(invoiceId: "INV-2024-001") { ... } }`

## 3. Systematic Testing Methodology

### Step 1: Establish Two Distinct User Contexts
In the sandbox, configure two authenticated sessions:
- **User A (Attacker)**: Token `TOKEN_A`, User ID `1001`
- **User B (Victim)**: Token `TOKEN_B`, User ID `1002`, Order ID `5542`

### Step 2: Cross-Account Direct Object Access
Replay User B's object request using User A's authorization token:
```bash
curl -i -s -H "Authorization: Bearer $TOKEN_A" "https://target.local/api/orders/5542"
```

### Step 3: Numerical & Sequential ID Fuzzing
For integer IDs, use `ffuf` or Python to probe sequential records:
```bash
ffuf -u "https://target.local/api/users/FUZZ/data" \
     -H "Authorization: Bearer $TOKEN_A" \
     -w <(seq 1 500) \
     -mc 200 -mr "email"
```

### Step 4: Method Mutation & Parameter Tampering
- Try switching HTTP methods (`GET` -> `POST` / `PUT` / `DELETE` / `PATCH`).
- Wrap ID in JSON array or object (`{"id": 1002}` -> `{"id": [1002]}`).
- Add wildcard or multi-ID query params (`?id=1002&id=1001`).

## 4. Verification & Reporting
1. Confirm access to unauthorized sensitive PII or data modification.
2. File finding via `create_vulnerability_report`:
   - **Category**: Broken Access Control (OWASP A01:2021)
   - **CWE**: CWE-639 / CWE-862
   - **CVSS 3.1**: `AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:L/A:N` (Base 7.1 High)
