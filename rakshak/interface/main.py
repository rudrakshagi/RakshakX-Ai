"""Command line interface entrypoint for RakshakX."""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys

logger = logging.getLogger(__name__)


def render_banner() -> None:
    banner = """
===================================================================
    ____        __         __          __   _  __
   / __ \\____ _/ /_______ / /_  ____ _/ /__/ |/ /
  / /_/ / __ `/ //_/ ___// __ \\/ __ `/ //_/|   / 
 / _, _/ /_/ / ,< (__  )/ / / / /_/ / ,<  /   |  
/_/ |_|\\__,_/_/|_/____//_/ /_/\\__,_/_/|_|/_/|_|  
                                                 
 Autonomous AI Multi-Agent Penetration Testing & Exploit Engine
===================================================================
"""
    try:
        print(banner)
    except UnicodeEncodeError:
        print("\n=== RakshakX: Autonomous AI Pentesting Engine ===\n")


def main() -> None:
    """CLI parsing and scan execution entry point."""
    parser = argparse.ArgumentParser(
        prog="rakshak",
        description="RakshakX: Autonomous AI Multi-Agent Penetration Testing Engine",
    )
    parser.add_argument(
        "--target",
        "-t",
        required=False,
        help="Target URL, domain, or local repository path for pentesting",
    )
    parser.add_argument(
        "--view",
        "-v",
        help="Launch the interactive web console for an existing scan ID",
    )
    parser.add_argument(
        "--port",
        "-p",
        type=int,
        default=8080,
        help="Port for the web viewer console (default: 8080)",
    )
    parser.add_argument(
        "--mode",
        "-m",
        choices=["deep", "quick", "recon"],
        default="deep",
        help="Scan depth mode (default: deep)",
    )
    parser.add_argument(
        "--whitebox",
        action="store_true",
        help="Enable whitebox source code analysis",
    )
    parser.add_argument(
        "--budget",
        type=float,
        default=10.0,
        help="Maximum LLM spend ceiling in USD (default: $10.00)",
    )
    parser.add_argument(
        "--max-turns",
        type=int,
        default=100,
        help="Maximum agent turns (default: 100)",
    )

    args = parser.parse_args()

    # Configure logging format
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    render_banner()

    # If --view is passed, start the Web Viewer Dashboard
    if args.view:
        from rakshak.interface.viewer.server import start_viewer_server
        print(f"[+] Starting RakshakX Web Console for Scan: {args.view}")
        print(f"[+] Console Dashboard URL: http://127.0.0.1:{args.port}")
        try:
            start_viewer_server(scan_id=args.view, port=args.port)
        except KeyboardInterrupt:
            print("\n[*] Web viewer stopped.")
        sys.exit(0)

    if not args.target:
        print("[!] Error: Either --target (for scanning) or --view (for viewing) is required.")
        sys.exit(1)

    print(f"[+] Starting scan against target: {args.target}")
    print(f"[+] Mode: {args.mode.upper()} | Max Budget: ${args.budget:.2f} | Whitebox: {args.whitebox}")

    try:
        from rakshak.core.runner import run_rakshak_scan
        asyncio.run(run_rakshak_scan(
            target=args.target,
            scan_mode=args.mode,
            is_whitebox=args.whitebox,
            max_budget_usd=args.budget,
            max_turns=args.max_turns,
        ))
        print("\n[+] Assessment completed successfully. Reports saved to rakshak_runs/")
    except KeyboardInterrupt:
        print("\n[!] Assessment interrupted by user.")
        sys.exit(130)
    except Exception as exc:
        print(f"\n[!] Assessment failed: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
