# Log 03 — Issues & caveats (kya fail hua, kya blindly trust mat karo)

## 1. `finish_scan` kabhi call nahi hua (main failure)

- Agent ne recon kiya (steps [2]–[46]), `think` kiya ([47]), report file kiya ([50]–[51]) — phir `finish_scan` ke bajaye `exec_command` ko `{"shell": true}` (boolean) ke saath call karne laga.
- SDK ka `ExecCommandArgs` schema `shell` ko **string** maangta hai → har attempt par pydantic `ValidationError` → `UserError: Error running tool exec_command` → turn failed.
- `raw_scan.log` mein ye failure 3+ baar repeat hua (lines 4, 113, 222 — har baar full traceback ke saath).
- Fail hone wale turns `agents.db` mein persist nahi hue (DB 52 messages par [51] par ruk gayi), isliye transcript mein ye loop dikhai nahi deta — sirf `raw_scan.log` mein hai.
- Process 10-min timeout par kill hua (`SCAN_RESULT` print kabhi nahi aaya). Report pipeline ne jo tha usi se `report.md/pdf/sarif.json` bana diye, isliye report §1/§6 mein placeholder text hai ("Scan in progress...").

## 2. Caido interception caveat (evidence ko carefully padho)

- Sandbox ke bahar jaane wala traffic Caido proxy se guzarta hai (`https_proxy=http://127.0.0.1:48080`, step [42] mein agent ne khud dekha).
- `curl -s https://rudrakshai.in/` ka HTML `<title>Caido</title>` ke saath aaya (step [30]) — ye sandbox proxy ka page hai, asal site ka homepage nahi (homepage ka title "Rudraksh AGI | AI-Native Software Company" hai, jo seedhi fetch mein dikha).
- `curl -sI` ne ajeeb double-status diya (`200 OK` + `500 Internal Server Error`, steps [14]–[45] repeat) — ye bhi proxy-path ka artifact lagta hai.
- Isliye "missing security headers" finding **directionally sahi hai** (observed responses mein HSTS/X-Frame-Options/CSPach/X-Content-Type-Optionsach mein se kuch nahi tha), lekin evidence proxy ke through collect hua tha — production claim se pehle seedhi (non-proxied) `curl -sI` se re-verify karo.

## 3. Chhoti observations

- `dig ... ANY` ne empty output diya (step [3]); agent ne adapt karke `NS` query ki jo chali ([8]).
- `openssl s_client` mein 20.7s lage (step [12]) — egress slow hai; yehi latency poore run ko ~9 min tak kheench gayi (start 21:22 → artifacts 21:31).
- Tracing backend har turn par `401` de raha tha (`[non-fatal] Tracing client error 401`) — telemetry/export par koi asar nahi, scan par bhi nahi; sirf log noise hai.
- `agents.json` mein agent status ab bhi `running` hai — graceful shutdown nahi hua (kill hua), dobara resume karne par stale state milegi.

## 4. Agla fix (code side)

- `exec_command` (`Shell` capability) ke schema mein `shell` param ka type/description model-friendly banana ya system prompt mein example dena taaki model boolean na bheje.
- `finish_scan` na aane par runner ko nudge/force-stop karna (max_turns hit hone par bhi process latka raha).
- Public-scope runs ke liye proxy-bypass ya direct-egress flag taaki evidence proxy-artifact se contaminate na ho.
