#!/usr/bin/env python3
"""
Gmail ML Client - Interactive Help System
Provides comprehensive help and documentation access via CLI.
"""

import os
import sys
import webbrowser
from pathlib import Path

def show_main_help():
    """Display main help menu."""
    print("""
╭─────────────────────────────────────────────────────────────────────────────╮
│                        Gmail ML Client - Help System                        │
╰─────────────────────────────────────────────────────────────────────────────╯

🚀 QUICK START:
   1. python cli.py init              # Initialize app and test Gmail auth
   2. python cli.py ensure-labels     # Create email labels
   3. python cli.py sync --limit 50   # Download emails from Gmail
   4. python cli.py review --limit 20 # Review and label emails
   5. python cli.py train             # Train ML model
   6. python cli.py predict           # See predictions
   7. python cli.py apply             # Apply actions (dry run first!)

📚 DOCUMENTATION:
   help commands    # Show all available CLI commands
   help workflow    # Step-by-step workflow guide
   help api         # REST API documentation
   help config      # Configuration options
   help setup       # Gmail authentication setup
   help trouble     # Troubleshooting guide
   help examples    # Usage examples

🛠️  DIRECT ACCESS:
   help --web       # Open web documentation
   help --readme    # Open README.md
   help --cli       # Open CLI_HELP.md
   help --api       # Open API_DOCS.md

💡 EXAMPLES:
   python help.py commands
   python help.py workflow
   python help.py --web
   
Type 'python help.py <topic>' for specific help.
""")

def show_commands_help():
    """Display CLI commands help."""
    print("""
╭─────────────────────────────────────────────────────────────────────────────╮
│                           CLI Commands Reference                            │
╰─────────────────────────────────────────────────────────────────────────────╯

🔧 SETUP COMMANDS:
   init                    Initialize database and verify Gmail auth
   ensure-labels          Create default email labels in Gmail

📧 EMAIL COMMANDS:
   sync [--q QUERY] [--limit N]       Download emails from Gmail
   review [--limit N]                 Interactive email review and labeling
   
🧠 MACHINE LEARNING:
   train [--epochs N]                 Train ML model on reviewed emails
   predict [--limit N]                Generate predictions for emails
   
⚡ ACTION COMMANDS:
   apply [--no-dry-run]               Apply actions to Gmail (default: dry run)

📊 INFORMATION:
   help                               Show this help system
   
🔍 COMMAND DETAILS:

   sync --q "is:unread" --limit 100   # Sync unread emails
   review --limit 30                  # Review 30 emails for training
   train --epochs 10                  # Extended training
   predict --limit 50                 # Get predictions for 50 emails
   apply                              # Preview actions (safe)
   apply --no-dry-run                 # Actually apply actions

📚 For detailed command documentation, run: python help.py workflow
""")

def show_workflow_help():
    """Display workflow guide."""
    print("""
╭─────────────────────────────────────────────────────────────────────────────╮
│                              Workflow Guide                                 │
╰─────────────────────────────────────────────────────────────────────────────╯

🚀 INITIAL SETUP (One-time):

   Step 1: Setup Gmail Authentication
   ──────────────────────────────────
   • Go to Google Cloud Console
   • Enable Gmail API  
   • Create OAuth credentials (Desktop app)
   • Download as credentials.json
   • Run: python test_gmail_auth.py

   Step 2: Initialize Application
   ─────────────────────────────────
   python cli.py init                 # Setup database & verify auth
   python cli.py ensure-labels        # Create email labels

📧 DAILY WORKFLOW:

   Step 1: Sync Emails
   ──────────────────
   python cli.py sync                 # Download recent emails
   python cli.py sync --q "is:unread" # Sync only unread

   Step 2: Review for Training (Initial/Periodic)
   ─────────────────────────────────────────────
   python cli.py review --limit 30    # Label emails for ML training

   Step 3: Train Model (After reviewing)
   ────────────────────────────────────
   python cli.py train                # Train ML classifier

   Step 4: Generate Predictions
   ───────────────────────────
   python cli.py predict              # See what model suggests

   Step 5: Apply Actions
   ────────────────────
   python cli.py apply                # Preview actions (safe!)
   python cli.py apply --no-dry-run   # Actually apply to Gmail

🔄 ONGOING MAINTENANCE:

   Weekly:  Review misclassified emails and retrain
   Monthly: Review and update keyword rules in cfg.py
   As needed: Adjust thresholds in cfg.py

💡 TIPS:
   • Start with 20-30 reviewed emails minimum for training
   • Use dry-run mode first to preview actions
   • Review model predictions regularly to improve accuracy
   • Check logs/gmail_ml_client.log for troubleshooting
""")

def show_api_help():
    """Display API documentation help."""
    print("""
╭─────────────────────────────────────────────────────────────────────────────╮
│                            REST API Documentation                           │
╰─────────────────────────────────────────────────────────────────────────────╯

🌐 API SERVER:
   python api.py                      # Start REST API server
   http://localhost:8000/docs         # Interactive API documentation
   http://localhost:8000/redoc        # Alternative API docs

🔑 AUTHENTICATION:
   X-API-Key: your-api-key-here       # Include in request headers
   
📡 KEY ENDPOINTS:

   GET  /health                       # Check server health
   GET  /api/emails                   # List emails
   POST /api/emails/sync              # Trigger Gmail sync
   PUT  /api/emails/{id}/review       # Mark email as reviewed
   POST /api/ml/train                 # Train ML model
   POST /api/ml/predict               # Generate predictions
   POST /api/actions/apply            # Apply actions to Gmail
   GET  /api/stats/overview           # System statistics

💻 EXAMPLE USAGE:

   # Get unreviewed emails
   curl -H "X-API-Key: key" http://localhost:8000/api/emails?reviewed=false

   # Train model
   curl -X POST -H "X-API-Key: key" \\
        -H "Content-Type: application/json" \\
        -d '{"epochs": 6}' \\
        http://localhost:8000/api/ml/train

   # Apply actions (dry run)
   curl -X POST -H "X-API-Key: key" \\
        -H "Content-Type: application/json" \\
        -d '{"dry_run": true}' \\
        http://localhost:8000/api/actions/apply

📚 For complete API documentation: python help.py --api
🌐 Online docs: http://localhost:8000/docs (when server running)
""")

def show_setup_help():
    """Display setup and authentication help."""
    print("""
╭─────────────────────────────────────────────────────────────────────────────╮
│                          Gmail Authentication Setup                         │
╰─────────────────────────────────────────────────────────────────────────────╯

🔐 GMAIL API SETUP:

   Step 1: Google Cloud Console
   ───────────────────────────
   1. Go to: https://console.cloud.google.com/
   2. Create new project or select existing
   3. Enable Gmail API
   4. Go to "APIs & Services" → "Credentials"

   Step 2: Create OAuth Credentials
   ───────────────────────────────
   1. Click "CREATE CREDENTIALS" → "OAuth client ID"
   2. Choose "Desktop application"
   3. Name it "Gmail ML Client"
   4. Download credentials.json

   Step 3: Place Credentials File
   ─────────────────────────────
   Save credentials.json in project root:
   GmailClient/credentials.json

   Step 4: Test Authentication
   ──────────────────────────
   python test_gmail_auth.py          # Test authentication
   python cli.py init                 # Initialize app

🚨 TROUBLESHOOTING AUTH:

   "Access blocked" error:
   • Add yourself as test user in OAuth consent screen
   • Wait 10-30 minutes for Google to process new OAuth app

   "credentials.json not found":
   • Ensure file is in project root directory
   • Check filename is exactly "credentials.json"

   "Gmail API not enabled":
   • Enable Gmail API in Google Cloud Console
   • Wait a few minutes for activation

🔧 OAUTH CONSENT SCREEN:
   • App name: "Gmail ML Client"
   • User support email: your email
   • Developer contact: your email
   • Add yourself as test user

📄 For complete setup guide: python help.py --readme
""")

def show_config_help():
    """Display configuration help."""
    print("""
╭─────────────────────────────────────────────────────────────────────────────╮
│                            Configuration Options                            │
╰─────────────────────────────────────────────────────────────────────────────╯

⚙️  MAIN CONFIGURATION FILE: cfg.py

📊 CLASSIFICATION THRESHOLDS:
   THRESHOLDS = {
       "spam": 0.85,       # Spam score threshold for trash
       "certain": 0.92,    # Confidence threshold for auto-apply
   }

🏷️  EMAIL LABELS:
   DEFAULT_TARGET_LABELS = [
       "Work", "Personal", "Receipts", "Finance",
       "Newsletters", "Social", "Updates"
   ]

🔍 KEYWORD RULES:
   RULES_INCLUDE = {
       "Receipts": ["receipt", "invoice", "order"],
       "Work": ["standup", "sprint", "jira"],
       "Finance": ["bank", "statement", "due"],
   }

   RULES_EXCLUDE = {
       "Receipts": ["privacy policy", "terms"],
   }

🔧 SYSTEM SETTINGS:
   SYNC_PAGE_SIZE = 200           # Max emails per sync
   DB_PATH = "state.db"           # Database file location
   MODEL_DIR = "model_artifacts"  # ML model storage

📝 LOGGING CONFIGURATION:
   Edit logger.py to adjust log levels and output formats

🎯 TUNING TIPS:
   • Lower spam threshold (0.80) = more aggressive spam filtering
   • Higher certain threshold (0.95) = more conservative auto-apply
   • Add custom keywords for your specific email patterns
   • Adjust sync_page_size based on Gmail quota usage

🔄 RELOAD CONFIG:
   Restart application after changing cfg.py
   Some settings require retraining the model
""")

def show_troubleshooting_help():
    """Display troubleshooting guide."""
    print("""
╭─────────────────────────────────────────────────────────────────────────────╮
│                           Troubleshooting Guide                             │
╰─────────────────────────────────────────────────────────────────────────────╯

🔧 COMMON ISSUES:

   ❌ "credentials.json not found"
   Solution: Download OAuth credentials from Google Cloud Console
   → python help.py setup

   ❌ "Gmail API error: 403" 
   Solution: Enable Gmail API, check credentials validity
   → https://console.cloud.google.com/apis/library/gmail.googleapis.com

   ❌ "No labeled feedback yet"
   Solution: Review emails first to create training data
   → python cli.py review --limit 30

   ❌ "Insufficient training data"
   Solution: Need minimum 10 emails with 2+ different labels
   → python cli.py review --limit 50

   ❌ "Model artifacts not found"
   Solution: Train the model first
   → python cli.py train

   ❌ "Access blocked: email-microservice..."
   Solution: Add yourself as test user in OAuth consent screen
   Wait 10-30 minutes for Google to process new OAuth app

🔍 DEBUGGING:

   Check Logs:
   logs/gmail_ml_client.log           # Detailed operation logs
   
   Test Components:
   python test_core_functionality.py  # Test core functions
   python test_e2e_functionality.py   # Test full workflows
   python test_gmail_auth.py          # Test Gmail authentication

   Database Issues:
   state.db                           # SQLite database file
   Use SQLite browser to inspect data

📊 PERFORMANCE ISSUES:

   Slow Sync:
   • Use specific Gmail queries: --q "is:unread"
   • Reduce sync limit: --limit 50
   • Check Gmail API quotas

   Poor Classification:
   • Need more training data (50+ reviewed emails)
   • Ensure balanced labels (examples of each type)
   • Add custom keyword rules in cfg.py
   • Adjust thresholds in cfg.py

   Memory Usage:
   • Reduce TF-IDF max_features in model.py
   • Use smaller training datasets
   • Restart application periodically

🆘 GETTING HELP:

   1. Check logs first: logs/gmail_ml_client.log
   2. Run diagnostic tests: python test_*.py
   3. Verify configuration: python help.py config
   4. Test with minimal data first
   5. Use dry-run mode: python cli.py apply

📞 SUPPORT RESOURCES:
   • README.md - Complete documentation
   • CLI_HELP.md - Detailed CLI reference
   • API_DOCS.md - REST API documentation
   • Test files - Validation and examples
""")

def show_examples_help():
    """Display usage examples."""
    print("""
╭─────────────────────────────────────────────────────────────────────────────╮
│                              Usage Examples                                 │
╰─────────────────────────────────────────────────────────────────────────────╯

📧 EMAIL SYNC EXAMPLES:

   # Basic sync
   python cli.py sync
   
   # Sync specific emails
   python cli.py sync --q "from:boss@company.com"
   python cli.py sync --q "is:unread newer_than:7d"
   python cli.py sync --q "has:attachment subject:invoice"
   
   # Limited sync
   python cli.py sync --limit 25

🧠 TRAINING EXAMPLES:

   # Initial training workflow
   python cli.py sync --limit 100        # Get emails
   python cli.py review --limit 30       # Label emails
   python cli.py train                   # Train model
   
   # Extended training
   python cli.py train --epochs 10
   
   # Retrain after more reviews
   python cli.py review --limit 50       # More training data
   python cli.py train                   # Retrain model

🔮 PREDICTION EXAMPLES:

   # See predictions
   python cli.py predict
   python cli.py predict --limit 100
   
   # Preview actions
   python cli.py apply                   # Safe dry run
   
   # Apply high-confidence actions
   python cli.py apply --no-dry-run

🏷️  LABEL MANAGEMENT:

   # Create standard labels
   python cli.py ensure-labels
   
   # Review specific emails
   python cli.py review --limit 20
   # During review, use labels: Work, Personal, SPAM, Receipts, etc.

🔧 CONFIGURATION EXAMPLES:

   Edit cfg.py:
   
   # Adjust spam sensitivity
   THRESHOLDS = {"spam": 0.80, "certain": 0.95}
   
   # Add custom rules
   RULES_INCLUDE = {
       "Finance": ["bank", "credit card", "payment"],
       "Support": ["ticket", "issue", "bug report"],
   }

📊 MONITORING EXAMPLES:

   # Check application logs
   tail -f logs/gmail_ml_client.log
   
   # Database inspection
   sqlite3 state.db
   .tables
   SELECT COUNT(*) FROM messages;
   SELECT gold_label, COUNT(*) FROM messages WHERE reviewed=1 GROUP BY gold_label;

🚀 AUTOMATION EXAMPLES:

   # Daily email processing (bash)
   #!/bin/bash
   cd /path/to/gmail-client
   python cli.py sync --limit 200
   python cli.py predict
   python cli.py apply --no-dry-run

   # Weekly model retraining (PowerShell)
   Set-Location "C:\\path\\to\\gmail-client"
   & python cli.py sync --limit 500
   & python cli.py review --limit 20
   & python cli.py train
   & python cli.py apply --no-dry-run

🌐 API EXAMPLES:

   # Start API server
   python api.py
   
   # Use API (curl examples)
   curl http://localhost:8000/health
   curl -H "X-API-Key: key" http://localhost:8000/api/emails
   
   # Python API client
   import requests
   headers = {"X-API-Key": "your-key"}
   response = requests.get("http://localhost:8000/api/emails", headers=headers)
   emails = response.json()

💡 WORKFLOW COMBINATIONS:

   # Process recent emails only
   python cli.py sync --q "newer_than:1d" --limit 50
   python cli.py predict --limit 50
   python cli.py apply --no-dry-run
   
   # Focus on specific sender
   python cli.py sync --q "from:important@client.com"
   python cli.py review --limit 10
   python cli.py train
   
   # Bulk cleanup
   python cli.py sync --q "older_than:30d is:unread" --limit 1000
   python cli.py apply --no-dry-run
""")

def open_documentation(doc_type):
    """Open documentation files or web resources."""
    project_root = Path(__file__).parent
    
    docs = {
        'readme': project_root / 'README.md',
        'cli': project_root / 'CLI_HELP.md', 
        'api': project_root / 'API_DOCS.md',
        'architecture': project_root / 'ARCHITECTURE.md',
        'tests': project_root / 'FINAL_TEST_VALIDATION_REPORT.md'
    }
    
    if doc_type == 'web':
        # Try to open local API docs if server is running
        try:
            webbrowser.open('http://localhost:8000/docs')
            print("🌐 Opened API documentation in browser")
        except:
            print("❌ Could not open browser. Start API server first: python api.py")
    elif doc_type in docs:
        doc_path = docs[doc_type]
        if doc_path.exists():
            if sys.platform.startswith('win'):
                os.startfile(doc_path)
            elif sys.platform.startswith('darwin'):
                os.system(f'open "{doc_path}"')
            else:
                os.system(f'xdg-open "{doc_path}"')
            print(f"📖 Opened {doc_path.name}")
        else:
            print(f"❌ Documentation file not found: {doc_path}")
    else:
        print(f"❌ Unknown documentation type: {doc_type}")

def main():
    """Main help system entry point."""
    if len(sys.argv) < 2:
        show_main_help()
        return
    
    topic = sys.argv[1].lower()
    
    # Handle web/file opening flags
    if topic.startswith('--'):
        doc_type = topic[2:]  # Remove --
        open_documentation(doc_type)
        return
    
    # Handle help topics
    help_topics = {
        'commands': show_commands_help,
        'workflow': show_workflow_help,
        'api': show_api_help,
        'setup': show_setup_help,
        'config': show_config_help,
        'trouble': show_troubleshooting_help,
        'troubleshooting': show_troubleshooting_help,
        'examples': show_examples_help,
    }
    
    if topic in help_topics:
        help_topics[topic]()
    else:
        print(f"❌ Unknown help topic: {topic}")
        print("\nAvailable topics:")
        for topic_name in help_topics.keys():
            print(f"   {topic_name}")
        print("\nOr use flags: --web, --readme, --cli, --api")

if __name__ == "__main__":
    main()