"""Passive recon scan driver for https://rudrakshai.in (user-owned site)."""
import asyncio
import sys

sys.path.insert(0, "/home/suryansh/RakshakX-Ai")

from rakshak.core.runner import run_rakshak_scan

PASSIVE_PROMPT = """PASSIVE RECONNAISSANCE ONLY on https://rudrakshai.in.
This site is owned by the user requesting the scan (Rudraksh AGI / Aditya Kumar Mishra).

Allowed (read-only, non-intrusive):
- DNS enumeration (dig, nslookup, host)
- TLS certificate inspection (openssl s_client, curl -vI)
- HTTP security headers review (curl -sI / -s)
- Technology fingerprinting from response headers and HTML meta tags

STRICTLY FORBIDDEN:
- brute-force, fuzzing, exploitation, PoC execution
- sqlmap, nuclei intrusive scans, login attempts
- any state-changing request (POST/PUT/DELETE)
- scanning any host other than rudrakshai.in

File vulnerability reports ONLY for confirmed passive observations
(e.g. missing security headers). End by calling finish_scan with a full report."""

async def main() -> None:
    result = await run_rakshak_scan(
        target="https://rudrakshai.in",
        scan_id="rudra-passive",
        scan_mode="quick",
        scope="https://rudrakshai.in",
        prompt_verbatim=PASSIVE_PROMPT,
        max_budget_usd=2.0,
        max_turns=20,
    )
    print("SCAN_RESULT:", type(result).__name__)
    fo = getattr(result, "final_output", None)
    print("FINAL_OUTPUT:")
    print((fo or "")[:3000])

if __name__ == "__main__":
    asyncio.run(main())
