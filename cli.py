import json
import sys
from typing import Optional

import typer

# from rich import box, print
# from rich.table import Table
from tqdm import tqdm

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
from sorter import propose
from trainer import train_from_feedback

app = typer.Typer(
    help="Gmail ML Client - trainable spam filter and auto sorter", rich_markup_mode=None
)


@app.command()
def quick_help():
    """Show quick start guide."""
    print(
        """
🚀 Gmail ML Client - Quick Start

1. Setup (one-time):
   python cli.py init              # Initialize & verify Gmail auth
   python cli.py ensure-labels     # Create email labels

2. Basic workflow:
   python cli.py sync --limit 50   # Download emails from Gmail
   python cli.py review --limit 20 # Review and label emails
   python cli.py train             # Train ML model
   python cli.py predict           # See predictions
   python cli.py apply             # Apply actions (dry run first!)

3. Get help:
   python cli.py --help            # Show available commands

Ready to start? Run: python cli.py init
"""
    )


@app.command()
def init():
    """Initialize local DB and verify Gmail auth."""
    try:
        logger.info("Initializing Gmail ML Client")
        init_db()
        get_labels()
        print("DB ready and Gmail auth OK.")
        logger.info("Initialization completed successfully")
    except Exception as e:
        logger.error(f"Initialization failed: {e}")
        print(f"Initialization failed: {e}")
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
        print(f"Label creation failed: {e}")
        raise typer.Exit(1)


@app.command()
def sync(limit: int = typer.Option(200, "--limit", help="Maximum messages to sync")):
    """Fetch messages into local store (subject+body text only)."""
    try:
        logger.info(f"Starting sync with limit={limit}")
        init_db()
        msgs = list_messages(max_results=limit)

        if not msgs:
            print("No messages found.")
            return

        for mmeta in tqdm(msgs, desc="Downloading"):
            try:
                m = get_message(mmeta["id"]) if isinstance(mmeta, dict) else get_message(mmeta)
                text = extract_text(m)
                upsert_message(m["id"], m.get("snippet", ""), text)
            except Exception as e:
                logger.warning(f"Failed to process message {mmeta.get('id', 'unknown')}: {e}")
                continue

        print(f"Synced {len(msgs)} messages into local store.")
        logger.info(f"Sync completed: {len(msgs)} messages")
    except Exception as e:
        logger.error(f"Sync failed: {e}")
        print(f"Sync failed: {e}")
        raise typer.Exit(1)


@app.command()
def train(epochs: int = typer.Option(6, "--epochs", help="Number of training epochs")):
    """Train the neural classifier from your reviewed feedback."""
    report, classes = train_from_feedback(epochs=epochs)
    print("\nTraining Report\n")
    print(report)
    print("Classes:", classes)


@app.command()
def predict(limit: int = typer.Option(50, "--limit", help="Maximum messages to predict")):
    """Run predictions over unreviewed messages and show proposed actions."""
    acts = propose(limit=limit)
    if not acts:
        print("No messages pending review/prediction.")
        return
    print("Proposed Actions")
    print("-" * 80)
    print(
        f"{'ID':<20} {'Action':<8} {'Spam':<6} {'Conf':<6} {'Label':<12} {'Target':<12} {'Snippet'}"
    )
    print("-" * 80)
    for a in acts:
        print(
            f"{a['id']:<20} {a['action']:<8} {a['spam_score']:<6.2f} {a['conf']:<6.2f} {str(a['pred_label'] or '-'):12} {str(a['target'] or '-'):12} {a['snippet'] or ''}"
        )
    print("-" * 80)


@app.command()
def review(limit: int = typer.Option(30, "--limit", help="Maximum messages to review")):
    """Interactive review: confirm trash/route or set correct label (SPAM, Work, Receipts, etc.)."""
    acts = propose(limit=limit)
    if not acts:
        print("No items to review.")
        return
    print("Enter label. 'SPAM' to trash; leave blank to skip; 'q' to quit.")
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
def apply(execute: str = typer.Option("false", "--execute")):
    """Apply actions to Gmail (trash or route+archive). Default is DRY RUN."""
    dry_run = execute.lower() != "true"
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
