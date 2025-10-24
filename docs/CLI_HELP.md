# Gmail ML Client - Command Line Interface Documentation

## Overview
The Gmail ML Client provides a powerful command-line interface for managing Gmail emails with machine learning-powered classification and automation.

## Global Usage
```bash
python cli.py [COMMAND] [OPTIONS]
```

## Commands Reference

### `init`
**Initialize the Gmail ML Client and verify authentication**

```bash
python cli.py init
```

**What it does:**
- Creates and initializes the local SQLite database
- Tests Gmail API authentication
- Verifies OAuth credentials are working
- Creates necessary model directories

**Example output:**
```
✓ Database initialized at state.db
✓ Gmail authentication verified
✓ Model directory created
Gmail ML Client ready for use!
```

**Troubleshooting:**
- If authentication fails, ensure `credentials.json` is in the project root
- Check that Gmail API is enabled in Google Cloud Console

---

### `ensure-labels`
**Create default email labels in Gmail if they don't exist**

```bash
python cli.py ensure-labels
```

**What it does:**
- Creates standard organizational labels: Work, Personal, Receipts, Finance, Newsletters, Social, Updates
- Only creates labels that don't already exist
- Returns the Gmail label IDs for each created/existing label

**Example output:**
```
Ensured label Work (Label_123)
Ensured label Personal (Label_456)
Ensured label Receipts (Label_789)
...
```

---

### `sync`
**Download emails from Gmail into local database**

```bash
python cli.py sync [OPTIONS]
```

**Options:**
- `--q TEXT`: Gmail search query (optional)
- `--limit INTEGER`: Maximum number of emails to sync (default: 200)

**Examples:**
```bash
# Sync recent emails
python cli.py sync

# Sync only unread emails
python cli.py sync --q "is:unread"

# Sync specific sender
python cli.py sync --q "from:example@email.com"

# Sync limited number
python cli.py sync --limit 50
```

**Gmail Query Syntax:**
- `is:unread` - Unread emails
- `from:email@domain.com` - From specific sender
- `subject:meeting` - Emails with "meeting" in subject
- `has:attachment` - Emails with attachments
- `newer_than:7d` - Emails from last 7 days
- `label:inbox` - Emails in inbox

**What it does:**
- Fetches email metadata and content from Gmail
- Extracts and preprocesses text content
- Stores emails in local SQLite database
- Skips emails already in database

---

### `train`
**Train the machine learning model on reviewed emails**

```bash
python cli.py train [OPTIONS]
```

**Options:**
- `--epochs INTEGER`: Number of training epochs (default: 6)

**Examples:**
```bash
# Standard training
python cli.py train

# Extended training
python cli.py train --epochs 10
```

**Requirements:**
- Must have reviewed emails (use `review` command first)
- Requires at least 2 different labels for classification
- Minimum 10 emails recommended for meaningful training

**What it does:**
- Loads reviewed emails from database
- Creates TF-IDF features from email text
- Trains neural network classifier
- Saves trained model artifacts
- Shows training performance metrics

**Example output:**
```
Training with 150 samples, 4 classes
Vectorized to 50000 features
Training completed in 45.2 seconds

Classification Report:
           precision    recall  f1-score   support
Work          0.92      0.89      0.90        28
Personal      0.88      0.91      0.89        23
Spam          0.95      0.98      0.96        42
Receipts      0.87      0.85      0.86        17

Classes: ['Personal', 'Receipts', 'Spam', 'Work']
```

---

### `predict`
**Generate predictions for unreviewed emails**

```bash
python cli.py predict [OPTIONS]
```

**Options:**
- `--limit INTEGER`: Maximum number of emails to predict (default: 50)

**Examples:**
```bash
# Standard prediction
python cli.py predict

# Predict more emails
python cli.py predict --limit 100
```

**What it does:**
- Loads unreviewed emails from database
- Generates ML predictions for each email
- Suggests actions (trash, route to label, or review)
- Shows confidence scores and reasoning

**Example output:**
```
┌──────────────┬─────────┬────────────┬──────┬────────────┬──────────┬─────────────────────────────────┐
│ id           │ action  │ spam_score │ conf │ pred_label │ target   │ snippet                         │
├──────────────┼─────────┼────────────┼──────┼────────────┼──────────┼─────────────────────────────────┤
│ msg_12345    │ route   │ 0.15       │ 0.89 │ Work       │ Work     │ Meeting reminder for tomorrow   │
│ msg_67890    │ trash   │ 0.92       │ 0.95 │ Spam       │ TRASH    │ Get rich quick! Click here now  │
│ msg_54321    │ route   │ 0.08       │ 0.76 │ Personal   │ Personal │ Family dinner this weekend      │
└──────────────┴─────────┴────────────┴──────┴────────────┴──────────┴─────────────────────────────────┘
```

**Action Types:**
- **route**: Move to predicted label
- **trash**: Move to trash (high spam score)
- **review**: Manual review needed (low confidence)

---

### `review`
**Interactively review and label emails for training**

```bash
python cli.py review [OPTIONS]
```

**Options:**
- `--limit INTEGER`: Maximum number of emails to review (default: 30)

**Examples:**
```bash
# Standard review session
python cli.py review

# Review more emails
python cli.py review --limit 50
```

**What it does:**
- Shows emails with current predictions
- Prompts for correct labels
- Stores human feedback for training
- Supports quick labeling workflow

**Interactive session:**
```
[id=msg_12345] Team standup notes from yesterday's meeting
Proposed: route -> Work (spam=0.12, conf=0.85)
Your label [ENTER=skip, q=quit]: Work

[id=msg_67890] Congratulations! You've won $1,000,000!
Proposed: trash -> TRASH (spam=0.96, conf=0.98)
Your label [ENTER=skip, q=quit]: SPAM

[id=msg_54321] Invoice for recent purchase #INV-2024-001
Proposed: review -> ? (spam=0.23, conf=0.65)
Your label [ENTER=skip, q=quit]: Receipts
```

**Valid Labels:**
- **SPAM**: Mark as spam (will be trashed)
- **Work**: Work-related emails
- **Personal**: Personal correspondence
- **Receipts**: Purchases, invoices, receipts
- **Finance**: Banking, credit cards, bills
- **Newsletters**: Newsletters, updates
- **Social**: Social media notifications
- **Updates**: Software updates, announcements
- **ENTER**: Skip this email
- **q**: Quit review session

---

### `apply`
**Apply predicted actions to Gmail emails**

```bash
python cli.py apply [OPTIONS]
```

**Options:**
- `--no-dry-run`: Actually apply actions (default is dry run)

**Examples:**
```bash
# Preview actions (safe)
python cli.py apply

# Actually apply actions (caution!)
python cli.py apply --no-dry-run
```

**Safety Features:**
- **Default dry run**: Shows what would happen without making changes
- **High confidence only**: Only applies actions with high confidence scores
- **Spam threshold**: Only trashes emails with spam score ≥ 0.85
- **Route threshold**: Only routes emails with confidence ≥ 0.92

**What it does:**
- Loads predicted actions from database
- Applies Gmail API operations:
  - **Trash**: Moves high-spam emails to trash
  - **Route**: Adds target label and removes INBOX
  - **Skip**: Leaves uncertain emails for manual review

**Example output:**
```bash
# Dry run mode
DRY: trash msg_12345 (spam=0.92)
DRY: route msg_67890 -> Work (conf=0.94)
DRY: route msg_54321 -> Receipts (conf=0.89)
Applied=0 (dry_run=True)

# Actual application
Moved msg_12345 to trash
Routed msg_67890 to Work
Routed msg_54321 to Receipts
Applied=3 (dry_run=False)
```

---

## Workflows

### Initial Setup Workflow
```bash
# 1. Initialize application
python cli.py init

# 2. Create email labels
python cli.py ensure-labels

# 3. Download some emails
python cli.py sync --limit 100

# 4. Review and label emails for training
python cli.py review --limit 30

# 5. Train the model
python cli.py train

# 6. See predictions
python cli.py predict

# 7. Apply actions (dry run first!)
python cli.py apply
python cli.py apply --no-dry-run
```

### Daily Usage Workflow
```bash
# 1. Sync new emails
python cli.py sync

# 2. Get predictions
python cli.py predict

# 3. Apply high-confidence actions
python cli.py apply --no-dry-run

# 4. Review uncertain emails (optional)
python cli.py review --limit 10

# 5. Retrain model (weekly/monthly)
python cli.py train
```

### Model Improvement Workflow
```bash
# 1. Review more emails to improve training data
python cli.py review --limit 50

# 2. Retrain with expanded dataset
python cli.py train --epochs 8

# 3. Evaluate new predictions
python cli.py predict

# 4. Test with dry run
python cli.py apply

# 5. Apply if satisfied
python cli.py apply --no-dry-run
```

---

## Configuration

### Spam Detection Thresholds
Edit `cfg.py` to adjust classification thresholds:

```python
THRESHOLDS = {
    "spam": 0.85,     # Emails above this score are considered spam
    "certain": 0.92,  # Only auto-apply actions above this confidence
}
```

### Custom Keyword Rules
Add domain-specific rules in `cfg.py`:

```python
RULES_INCLUDE = {
    "Receipts": ["receipt", "invoice", "order", "purchase"],
    "Work": ["standup", "sprint", "jira", "pull request"],
    "Finance": ["bank", "statement", "due", "bill"],
    # Add your custom rules here
}
```

### Sync Settings
Adjust email sync behavior:

```python
SYNC_PAGE_SIZE = 200  # Max emails per sync operation
```

---

## Error Handling

### Common Error Messages

**"credentials.json not found"**
- Solution: Download OAuth credentials from Google Cloud Console

**"Gmail API error: 403"**
- Solution: Ensure Gmail API is enabled and credentials are valid

**"No labeled feedback yet"**
- Solution: Use `review` command to label emails before training

**"Insufficient training data"**
- Solution: Review more emails to get diverse training examples

**"Model artifacts not found"**
- Solution: Run `train` command to create the ML model

### Debug Information
Check `logs/gmail_ml_client.log` for detailed error information and debugging output.

---

## Performance Tips

### Sync Performance
- Use specific queries to sync only needed emails
- Limit sync size for faster operations
- Run sync regularly rather than large batches

### Training Performance
- Start with 50-100 reviewed emails minimum
- Ensure balanced representation of all labels
- Use reasonable epoch counts (6-10 typically sufficient)

### Prediction Accuracy
- Review and correct misclassified emails regularly
- Add custom keyword rules for domain-specific patterns
- Retrain model as you accumulate more labeled data

---

## Integration Examples

### Cron Job for Automated Processing
```bash
# Add to crontab for hourly email processing
0 * * * * cd /path/to/gmail-client && python cli.py sync && python cli.py apply --no-dry-run
```

### Batch Scripts
```bash
#!/bin/bash
# weekly-retrain.sh
cd /path/to/gmail-client
python cli.py sync --limit 500
python cli.py review --limit 20
python cli.py train
python cli.py predict
python cli.py apply --no-dry-run
```

### PowerShell Automation (Windows)
```powershell
# daily-email-process.ps1
Set-Location "C:\path\to\gmail-client"
& .\.venv\Scripts\python.exe cli.py sync
& .\.venv\Scripts\python.exe cli.py predict
& .\.venv\Scripts\python.exe cli.py apply --no-dry-run
```

---

## Advanced Usage

### Custom Gmail Queries
```bash
# Process only recent important emails
python cli.py sync --q "is:important newer_than:1d"

# Sync emails from specific domains
python cli.py sync --q "from:@company.com OR from:@client.com"

# Process unread newsletters
python cli.py sync --q "is:unread category:promotions"
```

### Bulk Operations
```bash
# Process large email backlog
for i in {1..10}; do
    python cli.py sync --limit 200
    python cli.py predict --limit 200
    python cli.py apply --no-dry-run
    sleep 30  # Respect API rate limits
done
```

### Training Data Management
```bash
# Review emails that were misclassified
python cli.py sync --q "label:work -is:starred"  # Get work emails
python cli.py review --limit 100                 # Review and correct
python cli.py train --epochs 10                  # Retrain with corrections
```

---

**For REST API documentation, see `API_DOCS.md`**
