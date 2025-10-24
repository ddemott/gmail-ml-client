"""
Business logic services for Gmail ML Client.
Provides clean interface between API endpoints and core functionality.
"""

import os
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from .cfg import DEFAULT_TARGET_LABELS, JUNK_LABELS, SYNC_PAGE_SIZE, SYSTEM_LABELS
from .data_store import (
    Message,
    fetch_for_prediction,
    fetch_for_training,
    init_db,
    mark_review,
    save_prediction,
    upsert_message,
)
from .gmail_client import (
    ensure_label,
    get_labels,
    get_message,
    list_messages,
    modify_labels,
    trash_message,
)
from .logger import logger
from .model import predict as model_predict
from .model import train as model_train
from .preprocessor import extract_text
from .sorter import propose
from .trainer import train_from_feedback


class ActionType(Enum):
    TRASH = "trash"
    ROUTE = "route"
    REVIEW = "review"


@dataclass
class EmailAction:
    """Represents a proposed action for an email."""

    id: str
    snippet: str
    spam_score: float
    confidence: float
    predicted_label: Optional[str]
    target_label: Optional[str]
    action: ActionType

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "snippet": self.snippet,
            "spam_score": self.spam_score,
            "confidence": self.confidence,
            "predicted_label": self.predicted_label,
            "target_label": self.target_label,
            "action": self.action.value,
        }


@dataclass
class SyncResult:
    """Result of email synchronization."""

    total_messages: int
    processed_messages: int
    failed_messages: int
    errors: List[str]


@dataclass
class TrainingResult:
    """Result of model training."""

    success: bool
    report: str
    classes: List[str]
    error: Optional[str] = None


@dataclass
class ApplyResult:
    """Result of applying actions."""

    total_actions: int
    applied_actions: int
    dry_run: bool
    errors: List[str]


class GmailService:
    """Service for Gmail operations."""

    def __init__(self):
        self.logger = logger

    def initialize(self) -> bool:
        """Initialize the Gmail service and database."""
        try:
            self.logger.info("Initializing Gmail ML Client")
            init_db()
            get_labels()
            self.logger.info("Initialization completed successfully")
            return True
        except Exception as e:
            self.logger.error(f"Initialization failed: {e}")
            raise

    def ensure_default_labels(self) -> Dict[str, str]:
        """Create default target labels if missing."""
        try:
            self.logger.info("Ensuring default labels exist")
            created_labels = {}
            for name in DEFAULT_TARGET_LABELS:
                label_id = ensure_label(name)
                created_labels[name] = label_id
                self.logger.debug(f"Ensured label {name} ({label_id})")
            self.logger.info("Label creation completed")
            return created_labels
        except Exception as e:
            self.logger.error(f"Label creation failed: {e}")
            raise

    def get_all_labels(self) -> List[Dict[str, str]]:
        """Get all Gmail labels."""
        try:
            return get_labels()
        except Exception as e:
            self.logger.error(f"Failed to get labels: {e}")
            raise


class EmailSyncService:
    """Service for email synchronization."""

    def __init__(self):
        self.logger = logger

    def sync_messages(self, query: Optional[str] = None, limit: int = SYNC_PAGE_SIZE) -> SyncResult:
        """Sync messages from Gmail to local database."""
        try:
            self.logger.info(f"Starting sync with query='{query}', limit={limit}")
            init_db()

            msgs = list_messages(query=query, max_results=limit)
            if not msgs:
                self.logger.info("No messages found to sync")
                return SyncResult(0, 0, 0, [])

            processed = 0
            failed = 0
            errors = []

            for mmeta in msgs:
                try:
                    msg_id = mmeta["id"] if isinstance(mmeta, dict) else mmeta
                    m = get_message(msg_id)
                    text = extract_text(m)
                    upsert_message(m["id"], m.get("snippet", ""), text)
                    processed += 1
                except Exception as e:
                    failed += 1
                    error_msg = f"Failed to process message {mmeta.get('id', 'unknown')}: {e}"
                    self.logger.warning(error_msg)
                    errors.append(error_msg)
                    continue

            result = SyncResult(len(msgs), processed, failed, errors)
            self.logger.info(f"Sync completed: {processed} processed, {failed} failed")
            return result

        except Exception as e:
            self.logger.error(f"Sync failed: {e}")
            raise


class PredictionService:
    """Service for email prediction and classification."""

    def __init__(self):
        self.logger = logger

    def get_predictions(self, limit: int = 50) -> List[EmailAction]:
        """Get predictions for unreviewed messages."""
        try:
            self.logger.info(f"Making predictions for up to {limit} messages")
            actions_data = propose(limit=limit)

            actions = []
            for a in actions_data:
                action = EmailAction(
                    id=a["id"],
                    snippet=a["snippet"],
                    spam_score=a["spam_score"],
                    confidence=a["conf"],
                    predicted_label=a["pred_label"],
                    target_label=a["target"],
                    action=ActionType(a["action"]),
                )
                actions.append(action)

            self.logger.info(f"Generated {len(actions)} predictions")
            return actions

        except Exception as e:
            self.logger.error(f"Prediction failed: {e}")
            raise

    def review_message(self, message_id: str, label: str) -> bool:
        """Mark a message as reviewed with the given label."""
        try:
            mark_review(message_id, label.upper())
            self.logger.debug(f"Marked message {message_id} as reviewed with label {label}")
            return True
        except Exception as e:
            self.logger.error(f"Review failed for message {message_id}: {e}")
            raise


class TrainingService:
    """Service for model training."""

    def __init__(self):
        self.logger = logger

    def train_model(self, epochs: int = 6) -> TrainingResult:
        """Train the neural classifier from reviewed feedback."""
        try:
            self.logger.info(f"Starting training with {epochs} epochs")
            report, classes = train_from_feedback(epochs=epochs)

            if not classes:
                return TrainingResult(
                    success=False,
                    report="",
                    classes=[],
                    error="No labeled feedback available. Use review functionality first.",
                )

            self.logger.info("Training completed successfully")
            return TrainingResult(success=True, report=report, classes=classes)

        except Exception as e:
            error_msg = f"Training failed: {e}"
            self.logger.error(error_msg)
            return TrainingResult(success=False, report="", classes=[], error=error_msg)

    def get_training_data_stats(self) -> Dict[str, Any]:
        """Get statistics about available training data."""
        try:
            texts, labels = fetch_for_training()
            if not texts:
                return {"total_samples": 0, "label_counts": {}}

            label_counts = {}
            for label in labels:
                label_counts[label] = label_counts.get(label, 0) + 1

            return {
                "total_samples": len(texts),
                "label_counts": label_counts,
                "unique_labels": len(set(labels)),
            }
        except Exception as e:
            self.logger.error(f"Failed to get training data stats: {e}")
            raise


class ActionService:
    """Service for applying actions to emails."""

    def __init__(self):
        self.logger = logger

    def apply_actions(self, dry_run: bool = True, limit: int = 100) -> ApplyResult:
        """Apply predicted actions to Gmail."""
        try:
            self.logger.info(f"Applying actions (dry_run={dry_run})")
            actions_data = propose(limit=limit)

            if not actions_data:
                self.logger.info("No actions to apply")
                return ApplyResult(0, 0, dry_run, [])

            applied = 0
            errors = []

            for a in actions_data:
                try:
                    if a["action"] == "trash" and a["spam_score"] >= 0.85:
                        if not dry_run:
                            trash_message(a["id"])
                            applied += 1
                        self.logger.debug(
                            f"{'DRY: ' if dry_run else ''}Trashed {a['id']} (spam={a['spam_score']:.2f})"
                        )

                    elif a["action"] == "route" and a["target"]:
                        if not dry_run:
                            label_id = ensure_label(a["target"])
                            modify_labels(a["id"], add=[label_id], remove=["INBOX"])
                            applied += 1
                        self.logger.debug(
                            f"{'DRY: ' if dry_run else ''}Routed {a['id']} -> {a['target']} (conf={a['conf']:.2f})"
                        )

                except Exception as e:
                    error_msg = f"Failed to apply action for {a['id']}: {e}"
                    self.logger.warning(error_msg)
                    errors.append(error_msg)

            result = ApplyResult(len(actions_data), applied, dry_run, errors)
            self.logger.info(f"Apply completed: {applied} actions applied (dry_run={dry_run})")
            return result

        except Exception as e:
            self.logger.error(f"Apply failed: {e}")
            raise


# Service instances for dependency injection
gmail_service = GmailService()
sync_service = EmailSyncService()
prediction_service = PredictionService()
training_service = TrainingService()
action_service = ActionService()
