"""Rich-based CLI display helpers."""

from __future__ import annotations

import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console(legacy_windows=False)


def banner():
    console.print(
        Panel(
            Text("FACE  →  WEB  →  BLOCKCHAIN", justify="center", style="bold cyan")
            + Text("\nFace Identification  →  Web Discovery  →  On-Chain Proof", justify="center", style="dim")
            + Text("\nBuilt from scratch · Free-tier only · HH GOA 2026", justify="center", style="dim italic"),
            border_style="cyan",
            padding=(1, 4),
        )
    )


def step(n: int, total: int, msg: str):
    console.print(f"\n[bold cyan][{n}/{total}][/] [white]{msg}[/]")

def success(msg: str):
    console.print(f"      [green]✓ {msg}[/]")

def warning(msg: str):
    console.print(f"      [yellow]⚠ {msg}[/]")

def error(msg: str):
    console.print(f"      [red]❌ {msg}[/]")

def info(msg: str):
    console.print(f"      [dim]{msg}[/]")


def match_box(platform: str, similarity: float, url: str, confidence_tier: str = "HIGH"):
    tier_label = "HIGH CONFIDENCE MATCH ✓" if confidence_tier == "HIGH" else "PROBABLE MATCH ✓ (Pose/Lighting Variation)"
    border = "green" if confidence_tier == "HIGH" else "yellow"
    console.print(
        Panel(
            f"[bold {border}]{tier_label}[/]\n\n"
            f"[white]Platform:[/] [cyan]{platform}[/]\n"
            f"[white]Similarity:[/] [{border}]{similarity*100:.1f}%[/]  [dim]({confidence_tier} tier)[/]\n\n"
            f"[white]URL:[/]\n[dim link={url}]{url}[/]",
            title="Face Verification",
            border_style=border,
        )
    )


def blockchain_box(
    content_hash: str,
    tx_hash: str,
    block_number: int | str,
    contract: str,
    network: str = "Polygon Amoy",
):
    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column("k", style="dim")
    table.add_column("v", style="white")
    table.add_row("Network:", f"[cyan]{network}[/]")
    table.add_row("Content Hash:", f"[yellow]{content_hash}[/]")
    table.add_row("Transaction:", f"[magenta]{tx_hash}[/]")
    table.add_row("Block:", str(block_number))
    table.add_row("Contract:", f"[dim]{contract}[/]")
    console.print(
        Panel(table, title="[bold green]BLOCKCHAIN RECORD ✓[/]", border_style="green")
    )


def verification_box(local_hash: str, chain_hash: str | None, verified: bool, tampered: bool = False):
    if verified:
        console.print(
            Panel(
                f"[white]Local Hash:[/]   [yellow]{local_hash}[/]\n"
                f"[white]Chain Hash:[/]   [yellow]{chain_hash}[/]\n\n"
                f"[bold green]✓ VERIFIED — DATA INTEGRITY VALID[/]",
                title="Blockchain Verification",
                border_style="green",
            )
        )
    elif tampered:
        console.print(
            Panel(
                f"[white]Local Hash:[/]   [red]{local_hash}[/]\n"
                f"[white]Chain Hash:[/]   [yellow]{chain_hash}[/]\n\n"
                f"[bold red]❌ TAMPER DETECTED — DATA HAS CHANGED[/]",
                title="Blockchain Verification",
                border_style="red",
            )
        )
    else:
        console.print(
            Panel(
                f"[white]Local Hash:[/]   [yellow]{local_hash}[/]\n"
                f"[white]Chain Hash:[/]   [dim]{chain_hash or '— not found —'}[/]\n\n"
                f"[bold red]❌ VERIFICATION FAILED[/]",
                title="Blockchain Verification",
                border_style="red",
            )
        )


def candidates_table(candidates: list[dict]):
    if not candidates:
        info("No candidates returned.")
        return
    table = Table(title="Candidates (ranked)", show_lines=False)
    table.add_column("#", style="dim", width=4)
    table.add_column("Source", style="cyan")
    table.add_column("Title", style="white", max_width=55, overflow="ellipsis")
    table.add_column("URL", style="dim", max_width=45, overflow="ellipsis")
    table.add_column("Type", justify="right", style="magenta")
    from app.search.ranking import _social_score

    for c in candidates[:12]:
        score = _social_score(c.get("url", ""))
        table.add_row(
            str(c.get("position", "")),
            c.get("source", "")[:20],
            c.get("title", "")[:55],
            c.get("url", "")[:45],
            "social" if score else "web",
        )
    console.print(table)
 
 
def top_matches_table(evaluated: list[dict]):
    """Show summary table of evaluated candidates and their similarity."""
    if not evaluated:
        return
    table = Table(title="Candidate Face Match Summary", show_lines=False)
    table.add_column("#", style="dim", width=4)
    table.add_column("Source", style="cyan")
    table.add_column("Similarity", justify="right")
    table.add_column("Status")
    table.add_column("URL", style="dim", max_width=50, overflow="ellipsis")

    for idx, item in enumerate(evaluated[:8], 1):
        cand = item.get("candidate", {})
        sim = item.get("similarity", 0.0)
        tier = item.get("confidence_tier", "UNMATCHED")
        if tier == "HIGH":
            sim_str = f"[bold green]{sim*100:.1f}%[/]"
            stat_str = "[bold green]HIGH MATCH ✓[/]"
        elif tier == "PROBABLE":
            sim_str = f"[bold yellow]{sim*100:.1f}%[/]"
            stat_str = "[yellow]PROBABLE MATCH[/]"
        elif item.get("has_face", False):
            sim_str = f"[dim red]{sim*100:.1f}%[/]"
            stat_str = "[dim]No match[/]"
        else:
            sim_str = "[dim]—[/]"
            stat_str = "[dim red]No face detected[/]"

        table.add_row(
            str(idx),
            cand.get("source", "")[:20],
            sim_str,
            stat_str,
            cand.get("url", "")[:50],
        )
    console.print(table)
