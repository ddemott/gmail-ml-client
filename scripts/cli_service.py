"""
Enhanced CLI that uses the service layer instead of direct module calls.
Demonstrates proper separation of concerns.
"""

import typer
from logger import logger
from rich import box, print
from rich.console import Console
from rich.table import Table
from services import (
    action_service,
    gmail_service,
    prediction_service,
    sync_service,
    training_service,
)

console = Console()
app = typer.Typer(help="Gmail ML Client - Service-based CLI interface")


@app.command()
def init():
    """Initialize local DB and verify Gmail auth."""
    try:
        logger.info("Starting initialization via service layer")
        success = gmail_service.initialize()
        if success:
            print("[green]✓ Gmail ML Client initialized successfully[/green]")
        else:
            print("[red]✗ Initialization failed[/red]")
            raise typer.Exit(1)
    except Exception as e:
        logger.error(f"CLI initialization failed: {e}")
        print(f"[red]✗ Initialization failed: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def ensure_labels():
    """Create default target labels if missing."""
    try:
        logger.info("Creating default labels via service layer")
        created_labels = gmail_service.ensure_default_labels()

        print("[green]✓ Default labels ensured:[/green]")
        for name, label_id in created_labels.items():
            print(f"  • {name} ({label_id})")

    except Exception as e:
        logger.error(f"CLI label creation failed: {e}")
        print(f"[red]✗ Label creation failed: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def sync(
    query: str | None = typer.Option(None, "--query", "-q", help="Gmail search query"),
    limit: int = typer.Option(200, "--limit", "-l", help="Maximum messages to sync"),
):
    """Fetch messages into local store via service layer."""
    try:
        logger.info(f"Starting sync via service layer: query='{query}', limit={limit}")

        with console.status("[bold green]Syncing emails...", spinner="dots"):
            result = sync_service.sync_messages(query=query, limit=limit)

        # Display results
        print("[green]✓ Sync completed:[/green]")
        print(f"  • Total messages: {result.total_messages}")
        print(f"  • Processed: {result.processed_messages}")
        print(f"  • Failed: {result.failed_messages}")

        if result.errors:
            print(f"[yellow]⚠ Errors encountered ({len(result.errors)}):[/yellow]")
            for error in result.errors[:3]:  # Show first 3 errors
                print(f"  • {error}")
            if len(result.errors) > 3:
                print(f"  • ... and {len(result.errors) - 3} more")

    except Exception as e:
        logger.error(f"CLI sync failed: {e}")
        print(f"[red]✗ Sync failed: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def train(epochs: int = typer.Option(6, "--epochs", "-e", help="Number of training epochs")):
    """Train the neural classifier via service layer."""
    try:
        logger.info(f"Starting training via service layer: epochs={epochs}")

        with console.status("[bold blue]Training model...", spinner="dots"):
            result = training_service.train_model(epochs=epochs)

        if result.success:
            print("[green]✓ Training completed successfully[/green]")
            print("\n[bold]Training Report:[/bold]")
            print(result.report)
            print(f"\n[bold]Classes:[/bold] {', '.join(result.classes)}")
        else:
            print(f"[red]✗ Training failed: {result.error}[/red]")
            raise typer.Exit(1)

    except Exception as e:
        logger.error(f"CLI training failed: {e}")
        print(f"[red]✗ Training failed: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def predict(limit: int = typer.Option(50, "--limit", "-l", help="Maximum predictions to show")):
    """Run predictions via service layer and show proposed actions."""
    try:
        logger.info(f"Getting predictions via service layer: limit={limit}")

        with console.status("[bold cyan]Making predictions...", spinner="dots"):
            actions = prediction_service.get_predictions(limit=limit)

        if not actions:
            print("[yellow]No messages pending review/prediction.[/yellow]")
            return

        # Create results table
        table = Table(title="Proposed Actions", box=box.MINIMAL)
        table.add_column("ID", style="dim")
        table.add_column("Action", style="bold")
        table.add_column("Spam Score", justify="right")
        table.add_column("Confidence", justify="right")
        table.add_column("Predicted Label")
        table.add_column("Target")
        table.add_column("Snippet", max_width=40)

        for action in actions:
            # Color code spam scores
            spam_color = (
                "red"
                if action.spam_score > 0.8
                else "green"
                if action.spam_score < 0.3
                else "yellow"
            )
            spam_score = f"[{spam_color}]{action.spam_score:.2f}[/{spam_color}]"

            # Color code confidence
            conf_color = (
                "green"
                if action.confidence > 0.9
                else "yellow"
                if action.confidence > 0.7
                else "red"
            )
            confidence = f"[{conf_color}]{action.confidence:.2f}[/{conf_color}]"

            # Color code actions
            action_colors = {"trash": "red", "route": "green", "review": "yellow"}
            action_colored = f"[{action_colors.get(action.action.value, 'white')}]{action.action.value}[/{action_colors.get(action.action.value, 'white')}]"

            table.add_row(
                action.id[-8:],  # Show last 8 chars of ID
                action_colored,
                spam_score,
                confidence,
                action.predicted_label or "-",
                action.target_label or "-",
                (action.snippet[:37] + "...") if len(action.snippet) > 40 else action.snippet,
            )

        console.print(table)
        print(f"\n[green]✓ Displayed {len(actions)} predictions[/green]")

    except Exception as e:
        logger.error(f"CLI prediction failed: {e}")
        print(f"[red]✗ Prediction failed: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def review(limit: int = typer.Option(30, "--limit", "-l", help="Maximum messages to review")):
    """Interactive review via service layer."""
    try:
        logger.info(f"Starting review via service layer: limit={limit}")

        with console.status("[bold cyan]Loading messages for review...", spinner="dots"):
            actions = prediction_service.get_predictions(limit=limit)

        if not actions:
            print("[yellow]No items to review.[/yellow]")
            return

        print(
            "[yellow]Enter label (SPAM, Work, Personal, etc.). Leave blank to skip. 'q' to quit.[/yellow]"
        )

        reviewed_count = 0
        for action in actions:
            # Display message info
            print(f"\n[bold blue]Message ID:[/bold blue] {action.id}")
            print(f"[bold]Snippet:[/bold] {action.snippet}")
            print(f"[bold]Proposed:[/bold] {action.action.value} -> {action.target_label or 'N/A'}")
            print(
                f"[bold]Spam Score:[/bold] {action.spam_score:.2f}, [bold]Confidence:[/bold] {action.confidence:.2f}"
            )

            # Get user input
            label = console.input(
                "\n[bold green]Your label [ENTER=skip, q=quit]:[/bold green] "
            ).strip()

            if label.lower() == "q":
                break

            if label:
                try:
                    prediction_service.review_message(action.id, label.upper())
                    print(f"[green]✓ Saved as {label.upper()}[/green]")
                    reviewed_count += 1
                except Exception as e:
                    print(f"[red]✗ Failed to save review: {e}[/red]")
            else:
                print("[dim]Skipped[/dim]")

        print(f"\n[green]✓ Review session completed. Reviewed {reviewed_count} messages.[/green]")

    except Exception as e:
        logger.error(f"CLI review failed: {e}")
        print(f"[red]✗ Review failed: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def apply(
    dry_run: bool = typer.Option(
        True, "--dry-run/--no-dry-run", help="Preview actions without applying"
    ),
    limit: int = typer.Option(100, "--limit", "-l", help="Maximum actions to apply"),
):
    """Apply actions via service layer."""
    try:
        mode = "DRY RUN" if dry_run else "LIVE"
        logger.info(f"Applying actions via service layer: mode={mode}, limit={limit}")

        if not dry_run:
            confirm = console.input(
                "\n[bold red]WARNING:[/bold red] This will modify your Gmail account. Type 'yes' to continue: "
            )
            if confirm.lower() != "yes":
                print("[yellow]Operation cancelled.[/yellow]")
                return

        with console.status(
            f"[bold {'yellow' if dry_run else 'red'}]{'Previewing' if dry_run else 'Applying'} actions...",
            spinner="dots",
        ):
            result = action_service.apply_actions(dry_run=dry_run, limit=limit)

        # Display results
        if dry_run:
            print("[yellow]📋 DRY RUN PREVIEW:[/yellow]")
        else:
            print("[green]✅ ACTIONS APPLIED:[/green]")

        print(f"  • Total actions available: {result.total_actions}")
        print(f"  • Actions {'previewed' if dry_run else 'applied'}: {result.applied_actions}")

        if result.errors:
            print(f"[red]⚠ Errors encountered ({len(result.errors)}):[/red]")
            for error in result.errors[:3]:
                print(f"  • {error}")
            if len(result.errors) > 3:
                print(f"  • ... and {len(result.errors) - 3} more")

        if dry_run and result.applied_actions > 0:
            print("\n[bold blue]💡 To apply these actions for real, run:[/bold blue]")
            print(f"   [dim]python cli_service.py apply --no-dry-run --limit {limit}[/dim]")

    except Exception as e:
        logger.error(f"CLI apply failed: {e}")
        print(f"[red]✗ Apply failed: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def status():
    """Show system status and training statistics."""
    try:
        logger.info("Getting system status via service layer")

        with console.status("[bold cyan]Loading status...", spinner="dots"):
            training_stats = training_service.get_training_data_stats()

        # Create status table
        print("[bold blue]📊 Gmail ML Client Status[/bold blue]\n")

        # Training data overview
        if training_stats["total_samples"] > 0:
            print("[green]✓ Training Data Available[/green]")
            print(f"  • Total samples: {training_stats['total_samples']}")
            print(f"  • Unique labels: {training_stats['unique_labels']}")

            print("\n[bold]Label Distribution:[/bold]")
            for label, count in training_stats["label_counts"].items():
                percentage = (count / training_stats["total_samples"]) * 100
                print(f"  • {label}: {count} ({percentage:.1f}%)")

            if training_stats["total_samples"] < 50:
                print(
                    f"\n[yellow]⚠ Recommendation: Add more training data (current: {training_stats['total_samples']}, recommended: 50+)[/yellow]"
                )
        else:
            print("[yellow]⚠ No training data available[/yellow]")
            print("  • Use 'review' command to create training data")
            print("  • Then use 'train' command to build the model")

        # Show next steps
        print("\n[bold blue]💡 Suggested Workflow:[/bold blue]")
        if training_stats["total_samples"] == 0:
            print("  1. [dim]python cli_service.py sync[/dim] - Get emails")
            print("  2. [dim]python cli_service.py review[/dim] - Label emails")
            print("  3. [dim]python cli_service.py train[/dim] - Train model")
        elif training_stats["total_samples"] < 50:
            print("  1. [dim]python cli_service.py review[/dim] - Add more training data")
            print("  2. [dim]python cli_service.py train[/dim] - Re-train model")
        else:
            print("  1. [dim]python cli_service.py predict[/dim] - See predictions")
            print("  2. [dim]python cli_service.py apply --dry-run[/dim] - Preview actions")

    except Exception as e:
        logger.error(f"CLI status failed: {e}")
        print(f"[red]✗ Status check failed: {e}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
