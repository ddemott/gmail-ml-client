#!/usr/bin/env python3
"""
Setup script for Gmail ML Client
Guides users through initial configuration and credential setup.
"""
from __future__ import annotations
import os
import sys
import webbrowser
from pathlib import Path
from rich import print
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt

console = Console()

def check_python_version():
    """Check if Python version is compatible."""
    if sys.version_info < (3, 8):
        console.print("[red]Error: Python 3.8+ required[/red]")
        sys.exit(1)
    console.print(f"[green]✓[/green] Python {sys.version.split()[0]} detected")

def check_credentials():
    """Check if credentials.json exists."""
    if Path("credentials.json").exists():
        console.print("[green]✓[/green] credentials.json found")
        return True
    else:
        console.print("[yellow]⚠[/yellow] credentials.json not found")
        return False

def setup_credentials():
    """Guide user through credential setup."""
    console.print(Panel.fit(
        "[bold]Gmail API Setup Required[/bold]\n\n"
        "To use the Gmail ML Client, you need to set up Gmail API credentials:\n\n"
        "1. [blue]Enable Gmail API[/blue] in Google Cloud Console\n"
        "2. [blue]Create OAuth client ID[/blue] (Desktop application)\n"
        "3. [blue]Download credentials[/blue] as 'credentials.json'\n"
        "4. [blue]Place file[/blue] in this directory",
        title="Setup Instructions"
    ))
    
    if Confirm.ask("Open Google Cloud Console now?"):
        webbrowser.open("https://console.cloud.google.com/apis/library/gmail.googleapis.com")
    
    console.print("\n[yellow]After setting up credentials:[/yellow]")
    console.print("1. Download the JSON file")
    console.print("2. Rename it to 'credentials.json'")
    console.print("3. Place it in this directory")
    console.print("4. Run this setup script again")

def check_dependencies():
    """Check if dependencies are installed."""
    try:
        import google.auth
        import tensorflow
        import sklearn
        import rich
        import typer
        console.print("[green]✓[/green] All dependencies installed")
        return True
    except ImportError as e:
        console.print(f"[red]✗[/red] Missing dependency: {e.name}")
        return False

def install_dependencies():
    """Guide user to install dependencies."""
    console.print("\n[yellow]Installing dependencies...[/yellow]")
    console.print("Run: [blue]pip install -r requirements.txt[/blue]")
    
    if Confirm.ask("Install dependencies now?"):
        import subprocess
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
            console.print("[green]✓[/green] Dependencies installed successfully")
            return True
        except subprocess.CalledProcessError:
            console.print("[red]✗[/red] Failed to install dependencies")
            return False
    return False

def test_basic_functionality():
    """Test basic functionality."""
    console.print("\n[yellow]Testing basic functionality...[/yellow]")
    try:
        # Test config validation
        from cfg import validate_config
        validate_config()
        console.print("[green]✓[/green] Configuration valid")
        
        # Test database initialization
        from data_store import init_db
        init_db()
        console.print("[green]✓[/green] Database initialized")
        
        return True
    except Exception as e:
        console.print(f"[red]✗[/red] Error: {e}")
        return False

def show_next_steps():
    """Show next steps after setup."""
    console.print(Panel.fit(
        "[bold green]Setup Complete![/bold green]\n\n"
        "[bold]Next steps:[/bold]\n\n"
        "1. [blue]Initialize:[/blue] python cli.py init\n"
        "2. [blue]Sync emails:[/blue] python cli.py sync\n"
        "3. [blue]Review/train:[/blue] python cli.py review\n"
        "4. [blue]Train model:[/blue] python cli.py train\n"
        "5. [blue]Make predictions:[/blue] python cli.py predict\n"
        "6. [blue]Apply actions:[/blue] python cli.py apply --dry-run",
        title="Success"
    ))

def main():
    """Main setup process."""
    console.print(Panel.fit(
        "[bold]Gmail ML Client Setup[/bold]\n\n"
        "This script will guide you through setting up the Gmail ML Client.",
        title="Welcome"
    ))
    
    # Check Python version
    check_python_version()
    
    # Check and install dependencies
    if not check_dependencies():
        if not install_dependencies():
            console.print("[red]Please install dependencies manually and re-run setup[/red]")
            sys.exit(1)
    
    # Check credentials
    if not check_credentials():
        setup_credentials()
        if not check_credentials():
            console.print("[yellow]Run setup again after adding credentials.json[/yellow]")
            sys.exit(0)
    
    # Test functionality
    if not test_basic_functionality():
        console.print("[red]Setup incomplete - please check errors above[/red]")
        sys.exit(1)
    
    # Show next steps
    show_next_steps()

if __name__ == "__main__":
    main()