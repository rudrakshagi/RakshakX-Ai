"""Live interactive Terminal Dashboard for monitoring active pentests."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from rich.console import Group
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


class ScanDashboard:
    """Renders a real-time terminal UI for live scans."""

    def __init__(self, scan_id: str, target: str, mode: str = "DEEP") -> None:
        self.scan_id = scan_id
        self.target = target
        self.mode = mode
        self.start_time = datetime.now(UTC)
        self.agents: dict[str, dict[str, Any]] = {}
        self.findings: list[dict[str, Any]] = []
        self.logs: list[str] = []
        self.spent_usd: float = 0.0
        self.budget_usd: float = 10.0

    def add_agent(self, agent_id: str, name: str, status: str = "running") -> None:
        self.agents[agent_id] = {"name": name, "status": status, "turns": 0}

    def update_agent_status(self, agent_id: str, status: str) -> None:
        if agent_id in self.agents:
            self.agents[agent_id]["status"] = status

    def add_finding(self, title: str, severity: str, cvss: float, endpoint: str) -> None:
        self.findings.append({
            "title": title,
            "severity": severity,
            "cvss": cvss,
            "endpoint": endpoint,
        })

    def log_event(self, message: str) -> None:
        ts = datetime.now(UTC).strftime("%H:%M:%S")
        self.logs.append(f"[{ts}] {message}")
        if len(self.logs) > 8:
            self.logs.pop(0)

    def render(self) -> Layout:
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main", ratio=1),
            Layout(name="footer", size=7),
        )

        # Header Panel
        elapsed = str(datetime.now(UTC) - self.start_time).split(".")[0]
        header_text = Text()
        header_text.append(" RakshakX Live Pentest | ", style="bold red")
        header_text.append(f"Scan ID: {self.scan_id} | ", style="bold cyan")
        header_text.append(f"Target: {self.target} | ", style="bold green")
        header_text.append(f"Mode: {self.mode} | ", style="bold yellow")
        header_text.append(f"Elapsed: {elapsed}", style="bold white")
        layout["header"].update(Panel(header_text, border_style="red"))

        # Main Body: Split into Agents Tree (left) and Findings (right)
        layout["main"].split_row(
            Layout(name="agents", ratio=1),
            Layout(name="findings", ratio=1),
        )

        # Agents Table
        agents_table = Table(expand=True, box=None)
        agents_table.add_column("Agent ID", style="cyan", width=10)
        agents_table.add_column("Specialization", style="white")
        agents_table.add_column("Status", style="bold")

        for aid, a in self.agents.items():
            st = a["status"]
            st_style = "green" if st == "running" else "yellow" if st == "waiting" else "blue"
            agents_table.add_row(aid, a["name"], f"[{st_style}]{st.upper()}[/{st_style}]")

        layout["agents"].update(Panel(agents_table, title="[bold cyan]Active Agent Graph[/bold cyan]", border_style="cyan"))

        # Findings Table
        findings_table = Table(expand=True, box=None)
        findings_table.add_column("Severity", width=10)
        findings_table.add_column("Vulnerability Title", style="white")
        findings_table.add_column("CVSS", width=6)

        for f in self.findings:
            sev = f["severity"].upper()
            sev_style = "bold red" if sev in ("CRITICAL", "HIGH") else "bold yellow"
            findings_table.add_row(f"[{sev_style}]{sev}[/{sev_style}]", f["title"], str(f["cvss"]))

        layout["findings"].update(Panel(
            findings_table if self.findings else Text("No verified vulnerabilities filed yet.", style="dim italic"),
            title=f"[bold red]Confirmed Findings ({len(self.findings)})[/bold red]",
            border_style="red",
        ))

        # Footer: Logs & Cost
        log_text = "\n".join(self.logs) if self.logs else "Scan engine initializing..."
        footer_group = Group(
            Text(f"Estimated Spend: ${self.spent_usd:.2f} / ${self.budget_usd:.2f}", style="bold yellow"),
            Text(log_text, style="dim white"),
        )
        layout["footer"].update(Panel(footer_group, title="[bold white]Activity Stream & Budget[/bold white]", border_style="white"))

        return layout
