#!/usr/bin/env python3
"""
Gmail ML Client - Welcome Script
First-time user onboarding and setup verification.
"""

import os
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.text import Text

console = Console()


def check_requirements():
    """Check if basic requirements are met."""
    issues = []

    # Check Python version
    if sys.version_info < (3, 8):
        issues.append("Python 3.8+ required")

    # Check required files
    project_root = Path(__file__).parent
    required_files = [
        "cfg.py",
        "cli.py",
        "gmail_client.py",
        "data_store.py",
        "requirements.txt",
        "help.py",
    ]

    for file in required_files:
        if not (project_root / file).exists():
            issues.append(f"Missing required file: {file}")

    # Check credentials
    if not (project_root / "credentials.json").exists():
        issues.append("credentials.json not found - Gmail authentication required")

    return issues


def show_welcome():
    """Display welcome message."""
    welcome_text = Text()
    welcome_text.append("🚀 Gmail ML Client\n", style="bold blue")
    welcome_text.append("Intelligent Email Processing with Machine Learning\n\n", style="blue")
    welcome_text.append("This tool helps you automatically organize and filter your Gmail emails\n")
    welcome_text.append("using machine learning trained on your preferences.", style="dim")

    console.print(Panel(welcome_text, title="Welcome", border_style="blue"))


def show_features():
    """Display key features."""
    features = [
        "🧠 Machine Learning email classification",
        "🏷️  Automatic email labeling and organization",
        "🚮 Intelligent spam detection and removal",
        "⚡ Bulk email processing and management",
        "📊 REST API for integration",
        "🔍 Gmail search and filtering",
        "📈 Training feedback and model improvement",
        "🛡️  Safe dry-run mode for testing actions",
    ]

    console.print("\n[bold]Key Features:[/bold]")
    for feature in features:
        console.print(f"  {feature}")


def show_setup_steps():
    """Display setup steps."""
    console.print("\n[bold yellow]📋 Setup Required:[/bold yellow]")
    console.print("1. [blue]Gmail API Setup[/blue] - Configure OAuth credentials")
    console.print("2. [blue]Initialize Database[/blue] - Create local email store")
    console.print("3. [blue]Create Labels[/blue] - Setup Gmail labels")
    console.print("4. [blue]Sync Emails[/blue] - Download emails for processing")
    console.print("5. [blue]Review & Train[/blue] - Label emails to train ML model")


def run_setup_wizard():
    """Interactive setup wizard."""
    console.print("\n[bold green]🔧 Setup Wizard[/bold green]")

    # Check if user wants to proceed
    if not Confirm.ask("Would you like to run the setup wizard?"):
        console.print("Setup skipped. Run 'python welcome.py' again anytime.")
        return

    # Step 1: Gmail Authentication
    console.print("\n[bold]Step 1: Gmail Authentication[/bold]")
    if not Path("credentials.json").exists():
        console.print("[red]❌ credentials.json not found[/red]")
        console.print("\n[yellow]Gmail API Setup Required:[/yellow]")
        console.print("1. Go to: [link]https://console.cloud.google.com/[/link]")
        console.print("2. Enable Gmail API")
        console.print("3. Create OAuth Desktop credentials")
        console.print("4. Download as 'credentials.json'")
        console.print("5. Place in project directory")

        if Confirm.ask("\nHave you completed Gmail API setup?"):
            if Path("credentials.json").exists():
                console.print("[green]✅ credentials.json found[/green]")
            else:
                console.print("[red]❌ credentials.json still not found[/red]")
                console.print("Please complete Gmail setup first.")
                return
        else:
            console.print("Complete Gmail setup then run this wizard again.")
            return
    else:
        console.print("[green]✅ credentials.json found[/green]")

    # Step 2: Initialize Application
    console.print("\n[bold]Step 2: Initialize Application[/bold]")
    if Confirm.ask("Initialize database and verify Gmail auth?"):
        console.print("Running: python cli.py init")
        os.system("python cli.py init")

    # Step 3: Create Labels
    console.print("\n[bold]Step 3: Create Gmail Labels[/bold]")
    if Confirm.ask("Create default email labels in Gmail?"):
        console.print("Running: python cli.py ensure-labels")
        os.system("python cli.py ensure-labels")

    # Step 4: Sync Sample Emails
    console.print("\n[bold]Step 4: Download Sample Emails[/bold]")
    if Confirm.ask("Download recent emails for testing? (limit: 50)"):
        console.print("Running: python cli.py sync --limit 50")
        os.system("python cli.py sync --limit 50")

    # Setup complete
    console.print("\n[bold green]🎉 Setup Complete![/bold green]")
    show_next_steps()


def show_next_steps():
    """Display next steps after setup."""
    console.print("\n[bold blue]🚀 Next Steps:[/bold blue]")
    console.print("1. [cyan]Review emails:[/cyan] python cli.py review --limit 20")
    console.print("2. [cyan]Train model:[/cyan] python cli.py train")
    console.print("3. [cyan]Get predictions:[/cyan] python cli.py predict")
    console.print("4. [cyan]Preview actions:[/cyan] python cli.py apply")
    console.print("5. [cyan]Apply actions:[/cyan] python cli.py apply --no-dry-run")

    console.print("\n[bold]📚 Getting Help:[/bold]")
    console.print("• [cyan]Quick help:[/cyan] python cli.py quick-help")
    console.print("• [cyan]Full help:[/cyan] python cli.py help")
    console.print("• [cyan]Workflows:[/cyan] python cli.py help workflow")
    console.print("• [cyan]Troubleshooting:[/cyan] python cli.py help trouble")


def main():
    """Main welcome script."""
    console.clear()

    # Show welcome
    show_welcome()
    show_features()

    # Check requirements
    issues = check_requirements()
    if issues:
        console.print("\n[bold red]⚠️  Setup Issues Found:[/bold red]")
        for issue in issues:
            console.print(f"  ❌ {issue}")
        console.print()

    # Show setup information
    show_setup_steps()

    # Run setup wizard if requested
    if issues or Confirm.ask("\nWould you like to run the interactive setup wizard?"):
        run_setup_wizard()
    else:
        show_next_steps()

    # Final message
    console.print(f"\n[dim]Run 'python welcome.py' anytime to return to this setup wizard.[/dim]")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[yellow]Setup cancelled by user.[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        console.print("For help, run: python cli.py help trouble")
