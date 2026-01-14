"""
Optional CLI for reviewing flagged grants.

This is designed for efficiency - most weeks should have 0-3 flagged items.
User can skip this step entirely if they trust secondary keyword matches.
"""

from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt

console = Console()


class ReviewCLI:
    """Interactive CLI for reviewing flagged grants."""

    def __init__(self, db):
        self.db = db
        self.reviewed = 0
        self.approved = 0
        self.skipped = 0

    def run(self, grants: list[dict]) -> list[dict]:
        """
        Run interactive review for flagged grants.

        Args:
            grants: List of flagged grants needing review

        Returns:
            List of approved grants
        """
        if not grants:
            console.print(
                "[green]No grants flagged for review. All auto-approved![/green]"
            )
            return []

        console.print(
            Panel(
                f"[yellow]{len(grants)} grants flagged for optional review[/yellow]\n"
                "These matched secondary keywords. Quick review recommended.\n\n"
                "Commands: [a]pprove | [s]kip | [q]uit | [A]pprove all",
                title="Review Mode",
            )
        )

        approved_grants = []

        for i, grant in enumerate(grants):
            remaining = len(grants) - i

            self._display_grant(grant, i + 1, len(grants))

            while True:
                choice = Prompt.ask(
                    f"[{i+1}/{len(grants)}] Action",
                    choices=["a", "s", "q", "A"],
                    default="a",
                )

                if choice == "a":
                    approved_grants.append(grant)
                    self.approved += 1
                    console.print("[green]Approved[/green]")
                    break

                elif choice == "s":
                    self.skipped += 1
                    console.print("[yellow]Skipped[/yellow]")
                    break

                elif choice == "q":
                    console.print(f"\n[yellow]Quit with {remaining} remaining[/yellow]")
                    self._print_summary()
                    return approved_grants

                elif choice == "A":
                    # Approve all remaining
                    approved_grants.append(grant)
                    approved_grants.extend(grants[i + 1 :])
                    self.approved += remaining
                    console.print(f"[green]Approved all {remaining} remaining[/green]")
                    self._print_summary()
                    return approved_grants

            self.reviewed += 1

        self._print_summary()
        return approved_grants

    def _display_grant(self, grant: dict, num: int, total: int):
        """Display a single grant for review."""
        console.print()

        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column("Field", style="cyan")
        table.add_column("Value")

        table.add_row("Title", grant.get("title", ""))
        table.add_row("Agency", grant.get("agency", ""))
        table.add_row("Deadline", grant.get("close_date") or "Rolling")
        table.add_row("Amount", self._format_amount(grant))
        table.add_row("Match", f"{grant.get('match_type')}: {grant.get('match_value')}")
        table.add_row("URL", grant.get("url", ""))

        console.print(Panel(table, title=f"Grant {num}/{total}"))

        if grant.get("summary"):
            console.print(Panel(grant["summary"], title="AI Summary"))

    def _format_amount(self, grant: dict) -> str:
        """Format award amount for display."""
        ceiling = grant.get("award_ceiling")
        floor = grant.get("award_floor")
        if ceiling:
            if floor:
                return f"${floor:,} - ${ceiling:,}"
            return f"Up to ${ceiling:,}"
        return "Varies"

    def _print_summary(self):
        """Print review session summary."""
        console.print()
        console.print(
            Panel(
                f"Reviewed: {self.reviewed}\n"
                f"Approved: {self.approved}\n"
                f"Skipped: {self.skipped}",
                title="Review Complete",
            )
        )
