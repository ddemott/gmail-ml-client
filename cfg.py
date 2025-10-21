from __future__ import annotations

# Thresholds for decisions
THRESHOLDS = {
    "spam": 0.85,       # probability to send to Trash
    "certain": 0.92,    # auto-apply if >= this; else send to review
}

# Labels treated as spam/junk (besides system SPAM)
JUNK_LABELS = {"Junk", "JUNK", "Bulk", "Promotions:Spammy"}

# Non-system labels to consider as routing targets
DEFAULT_TARGET_LABELS = [
    "Work", "Personal", "Receipts", "Finance", "Newsletters", "Social", "Updates"
]

# Simple keyword rules to bias target suggestions (still overridden by model if confident)
# label -> list of include keywords (lowercased)
RULES_INCLUDE = {
    "Receipts": ["receipt", "invoice", "order", "transaction", "purchase", "payment"],
    "Finance": ["bank", "statement", "due", "bill", "credit card", "mortgage"],
    "Newsletters": ["unsubscribe", "newsletter", "weekly", "digest"],
    "Social": ["followed you", "like", "commented", "mentioned you"],
    "Work": ["standup", "sprint", "jira", "pull request", "deployment", "oncall"],
    "Updates": ["update", "policy", "terms", "what's new", "changelog"],
}

# Rules to exclude routing to a label if present
RULES_EXCLUDE = {
    "Receipts": ["privacy policy", "terms of service"],
}

# Gmail system labels to ignore as targets
SYSTEM_LABELS = {
    "INBOX", "UNREAD", "STARRED", "IMPORTANT", "TRASH", "DRAFT", "SENT",
    "CATEGORY_PERSONAL", "CATEGORY_SOCIAL", "CATEGORY_PROMOTIONS",
    "CATEGORY_UPDATES", "CATEGORY_FORUMS", "SPAM", "CATEGORY_SPAM",
}

# Maximum messages to pull per sync
SYNC_PAGE_SIZE = 200

DB_PATH = "state.db"
MODEL_DIR = "model_artifacts"

def validate_config():
    """Validate configuration settings."""
    errors = []
    
    # Validate thresholds
    if not (0.0 <= THRESHOLDS["spam"] <= 1.0):
        errors.append("THRESHOLDS['spam'] must be between 0.0 and 1.0")
    
    if not (0.0 <= THRESHOLDS["certain"] <= 1.0):
        errors.append("THRESHOLDS['certain'] must be between 0.0 and 1.0")
    
    if THRESHOLDS["spam"] >= THRESHOLDS["certain"]:
        errors.append("THRESHOLDS['certain'] should be higher than THRESHOLDS['spam']")
    
    # Validate sync page size
    if SYNC_PAGE_SIZE <= 0:
        errors.append("SYNC_PAGE_SIZE must be positive")
    
    # Validate target labels don't conflict with system labels
    conflicts = set(DEFAULT_TARGET_LABELS) & SYSTEM_LABELS
    if conflicts:
        errors.append(f"DEFAULT_TARGET_LABELS conflicts with SYSTEM_LABELS: {conflicts}")
    
    # Validate rules
    for label in RULES_INCLUDE:
        if label not in DEFAULT_TARGET_LABELS:
            errors.append(f"RULES_INCLUDE contains label '{label}' not in DEFAULT_TARGET_LABELS")
    
    for label in RULES_EXCLUDE:
        if label not in DEFAULT_TARGET_LABELS:
            errors.append(f"RULES_EXCLUDE contains label '{label}' not in DEFAULT_TARGET_LABELS")
    
    if errors:
        raise ValueError("Configuration validation failed:\n" + "\n".join(f"- {e}" for e in errors))

# Validate on import
validate_config()
