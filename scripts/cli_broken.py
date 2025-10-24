import json
import sys
from typing import Optional

import typer
from cfg import JUNK_LABELS, SYNC_PAGE_SIZE, SYSTEM_LABELS
from data_store import init_db, mark_review, upsert_message
from gmail_client import (
    ensure_label,
    get_labels,
    get_message,
    list_messages,
    modify_labels,
    trash_message,
)
from logger import logger
from preprocessor import extract_text
from rich import box, print
from rich.table import Table
from sorter import propose
from tqdm import tqdm
from trainer import train_from_feedback

app = typer.Typer(help="Gmail ML Client - trainable spam filter and auto sorter")


@app.command("help-docs")
def help_docs(
    topic: Optional[str] = typer.Argument(None, help="Specific help topic to show"),
    web: bool = typer.Option(False, "--web", help="Open web documentation"),
    readme: bool = typer.Option(False, "--readme", help="Open README.md"),
    cli: bool = typer.Option(False, "--cli", help="Open CLI help"),
    api: bool = typer.Option(False, "--api", help="Open API docs"),
):
    """Show comprehensive help and documentation."""
    import subprocess

    # Handle documentation flags
    if web:
        subprocess.run([sys.executable, "help.py", "--web"])
        return
    elif readme:
        subprocess.run([sys.executable, "help.py", "--readme"])
        return
    elif cli:
        subprocess.run([sys.executable, "help.py", "--cli"])
        return
    elif api:
        subprocess.run([sys.executable, "help.py", "--api"])
        return

    # Handle help topics or show main help
    if topic:
        subprocess.run([sys.executable, "help.py", topic])
    else:
        subprocess.run([sys.executable, "help.py"])


@app.command()
def quick_help():
    """Show quick start guide."""
    print(
        """
[bold blue]🚀 Gmail ML Client - Quick Start[/bold blue]

[yellow]1. Setup (one-time):[/yellow]
   python cli.py init              # Initialize & verify Gmail auth
   python cli.py ensure-labels     # Create email labels

[yellow]2. Basic workflow:[/yellow]
   python cli.py sync --limit 50   # Download emails from Gmail
   python cli.py review --limit 20 # Review and label emails
   python cli.py train             # Train ML model
   python cli.py predict           # See predictions
   python cli.py apply             # Apply actions (dry run first!)

[yellow]3. Get help:[/yellow]
   python cli.py help-docs           # Complete help system
   python cli.py help-docs commands  # CLI commands reference
   python cli.py help-docs workflow  # Step-by-step guide
   python cli.py help-docs --web     # Open web docs

[green]Ready to start? Run: python cli.py init[/green]
"""
    )


@app.command()
def init():
    """Initialize local DB and verify Gmail auth."""
    try:
        logger.info("Initializing Gmail ML Client")
        init_db()
        get_labels()
        print("[green]DB ready and Gmail auth OK.[/green]")
        logger.info("Initialization completed successfully")
    except Exception as e:
        logger.error(f"Initialization failed: {e}")
        print(f"[red]Initialization failed: {e}[/red]")
        raise typer.Exit(1)


@app.command("ensure-labels")
def ensure_labels():
    """Create default target labels if missing."""
    try:
        logger.info("Ensuring default labels exist")
        for name in ["Work", "Personal", "Receipts", "Finance", "Newsletters", "Social", "Updates"]:
            lid = ensure_label(name)
            print(f"Ensured label {name} ({lid})")
        logger.info("Label creation completed")
    except Exception as e:
        logger.error(f"Label creation failed: {e}")
        print(f"[red]Label creation failed: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def sync(limit: int = typer.Option(200, help="Maximum messages to sync")):
    """Fetch messages into local store (subject+body text only)."""
    try:
        logger.info(f"Starting sync with limit={limit}")
        init_db()
        msgs = list_messages(max_results=limit)

        if not msgs:
            print("[yellow]No messages found.[/yellow]")
            return

        for mmeta in tqdm(msgs, desc="Downloading"):
            try:
                m = get_message(mmeta["id"]) if isinstance(mmeta, dict) else get_message(mmeta)
                text = extract_text(m)
                upsert_message(m["id"], m.get("snippet", ""), text)
            except Exception as e:
                logger.warning(f"Failed to process message {mmeta.get('id', 'unknown')}: {e}")
                continue

        print(f"[green]Synced {len(msgs)} messages into local store.[/green]")
        logger.info(f"Sync completed: {len(msgs)} messages")
    except Exception as e:
        logger.error(f"Sync failed: {e}")
        print(f"[red]Sync failed: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def train(epochs: int = typer.Option(6, help="Number of training epochs")):
    """Train the neural classifier from your reviewed feedback."""
    report, classes = train_from_feedback(epochs=epochs)
    print("\n[bold]Training Report[/bold]\n")
    print(report)
    print("Classes:", classes)


@app.command()
def predict(limit: int = typer.Option(50, help="Maximum messages to predict")):
    """Run predictions over unreviewed messages and show proposed actions."""
    acts = propose(limit=limit)
    if not acts:
        print("No messages pending review/prediction.")
        return
    tbl = Table(title="Proposed Actions", box=box.MINIMAL)
    for h in ["id", "action", "spam_score", "conf", "pred_label", "target", "snippet"]:
        tbl.add_column(h)
    for a in acts:
        tbl.add_row(
            a["id"],
            a["action"],
            f"{a['spam_score']:.2f}",
            f"{a['conf']:.2f}",
            a["pred_label"] or "-",
            a["target"] or "-",
            a["snippet"] or "",
        )
    print(tbl)


@app.command()
def review(limit: int = typer.Option(30, help="Maximum messages to review")):
    """Interactive review: confirm trash/route or set correct label (SPAM, Work, Receipts, etc.)."""
    acts = propose(limit=limit)
    if not acts:
        print("No items to review.")
        return
    print("[yellow]Enter label. 'SPAM' to trash; leave blank to skip; 'q' to quit.[/yellow]")
    for a in acts:
        print(
            f"\n[id={a['id']}] {a['snippet']}\nProposed: {a['action']} -> {a['target']} (spam={a['spam_score']:.2f}, conf={a['conf']:.2f})"
        )
        lab = input("Your label [ENTER=skip, q=quit]: ").strip()
        if lab.lower() == "q":
            break
        if lab:
            mark_review(a["id"], lab.upper())
            print("Saved.")
        else:
            print("Skipped.")


@app.command()
def apply(execute: bool = typer.Option(False, help="Execute actions (default: dry run)")):
    """Apply actions to Gmail (trash or route+archive). Default is DRY RUN. Use --execute to actually apply."""
    # Handle CliRunner inconsistencies: sometimes strings, sometimes None/bool
    if isinstance(execute, str):
        execute = execute.lower() in ("true", "1", "yes", "on")
    elif execute is None:
        execute = True  # Flag present
    # else: execute is already bool (False when flag absent)
    dry_run = not execute
    acts = propose(limit=100)
    if not acts:
        print("Nothing to apply.")
        return
    applied = 0
    for a in acts:
        if a["action"] == "trash" and a["spam_score"] >= 0.85:
            if dry_run:
                print(f"DRY: trash {a['id']} (spam={a['spam_score']:.2f})")
            else:
                trash_message(a["id"])
                applied += 1
        elif a["action"] == "route" and a["target"]:
            if dry_run:
                print(f"DRY: route {a['id']} -> {a['target']} (conf={a['conf']:.2f})")
            else:
                lid = ensure_label(a["target"])
                modify_labels(a["id"], add=[lid], remove=["INBOX"])
                applied += 1
        else:
            # leave for manual review
            pass
    print(f"Applied={applied} (dry_run={dry_run})")


if __name__ == "__main__":
    app()
