from typing import Optional

import typer
from rich import box, print
from rich.table import Table
from tqdm import tqdm

from .cfg import JUNK_LABELS, SYNC_PAGE_SIZE, SYSTEM_LABELS
from .data_store import init_db, mark_review, upsert_message
from .gmail_client import (
    ensure_label,
    get_labels,
    get_message,
    list_messages,
    modify_labels,
    trash_message,
)
from .logger import logger
from .preprocessor import extract_text
from .sorter import propose
from .trainer import train_from_feedback

app = typer.Typer(help="Gmail ML Client - trainable spam filter and auto sorter")


@app.command()
def init() -> None:
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


@app.command()
def ensure_labels() -> None:
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
def sync(q: Optional[str] = None, limit: int = 200) -> None:
    """Fetch messages into local store (subject+body text only)."""
    try:
        logger.info(f"Starting sync with query='{q}', limit={limit}")
        init_db()
        msgs = list_messages(query=q, max_results=limit)

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
def train(epochs: int = 6) -> None:
    """Train the neural classifier from your reviewed feedback."""
    try:
        logger.info(f"Starting training with {epochs} epochs")
        report, classes = train_from_feedback(epochs=epochs)
        print("\n[bold]Training Report[/bold]\n")
        print(report)
        print("Classes:", classes)
        logger.info("Training completed successfully")
    except Exception as e:
        logger.error(f"Training failed: {e}")
        print(f"[red]Training failed: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def predict(limit: int = 50) -> None:
    """Run predictions over unreviewed messages and show proposed actions."""
    try:
        logger.info(f"Making predictions for up to {limit} messages")
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
        logger.info(f"Displayed predictions for {len(acts)} messages")
    except Exception as e:
        logger.error(f"Prediction failed: {e}")
        print(f"[red]Prediction failed: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def review(limit: int = 30) -> None:
    """Interactive review: confirm trash/route or set correct label (SPAM, Work, Receipts, etc.)."""
    try:
        logger.info(f"Starting review for up to {limit} messages")
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
        logger.info("Review session completed")
    except Exception as e:
        logger.error(f"Review failed: {e}")
        print(f"[red]Review failed: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def apply(dry_run: bool = True) -> None:
    """Apply actions to Gmail (trash or route+archive). Default is DRY RUN."""
    try:
        logger.info(f"Applying actions (dry_run={dry_run})")
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
        logger.info(f"Apply completed: {applied} actions applied")
    except Exception as e:
        logger.error(f"Apply failed: {e}")
        print(f"[red]Apply failed: {e}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
