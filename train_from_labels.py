#!/usr/bin/env python3
"""
Advanced training using existing Gmail labels
"""

import time
from collections import defaultdict

from data_store import init_db, mark_review, upsert_message
from gmail_client import get_labels, get_message, list_messages
from preprocessor import extract_text


def train_from_existing_labels(target_labels=None, emails_per_label=15):
    """
    Train model using emails that are already labeled in Gmail.

    Args:
        target_labels: List of label names to train on (None = use all)
        emails_per_label: Number of emails to get per label
    """

    print("🎯 Training from Existing Gmail Labels")
    print("=" * 60)

    # Initialize database
    init_db()

    # Get all labels
    all_labels = get_labels()
    user_labels = [l for l in all_labels if l.get("type") == "user"]

    if target_labels:
        # Filter to target labels only
        user_labels = [l for l in user_labels if l.get("name") in target_labels]

    print(f"📋 Found {len(user_labels)} labels to train on")

    training_data = defaultdict(list)

    for label_info in user_labels:
        label_name = label_info.get("name")
        label_id = label_info.get("id")

        print(f"\n🔍 Processing label: {label_name}")

        try:
            # Get messages with this label (use label name without quotes)
            query = f"label:{label_name}"
            message_ids = list_messages(query=query, max_results=emails_per_label)

            print(f"   📧 Found {len(message_ids)} messages")

            for i, msg_id in enumerate(message_ids):
                try:
                    message = get_message(msg_id)
                    if message:
                        # Extract text
                        text = extract_text(message)
                        snippet = message.get("snippet", "")[:100]

                        # Store in database
                        upsert_message(msg_id, snippet, text)

                        # Mark as reviewed with this label
                        mark_review(msg_id, label_name)

                        training_data[label_name].append(text[:100])

                        if (i + 1) % 5 == 0:
                            print(f"   ✅ Processed {i + 1}/{len(message_ids)}")

                except Exception as e:
                    print(f"   ⚠️  Error processing message: {e}")
                    continue

                # Add small delay to avoid rate limiting
                time.sleep(0.1)

        except Exception as e:
            print(f"   ❌ Error processing label {label_name}: {e}")
            continue

    # Show training data summary
    print(f"\n📊 Training Data Summary:")
    total_samples = 0
    for label, samples in training_data.items():
        count = len(samples)
        total_samples += count
        print(f"   {label}: {count} samples")

    print(f"\n🎉 Total training samples: {total_samples}")

    if total_samples > 0:
        print(f"\n🚀 Ready to train! Run: python simple_train.py")
        return True
    else:
        print(f"\n❌ No training data collected. Check Gmail access.")
        return False


def suggest_priority_labels():
    """Suggest which labels to start with."""

    priority_suggestions = [
        "[Gmail]/Family",
        "[Gmail]/Finance",
        "[Gmail]/Bills",
        "[Gmail]/Job",
        "[Gmail]/Health",
        "[Gmail]/Computer Related",
        "[Gmail]/CodeRelated",
        "[Gmail]/Amazon",
        "[Gmail]/Paypal",
        "[Gmail]/Auto Related",
    ]

    print(f"\n💡 Suggested Priority Labels (start with these):")
    for i, label in enumerate(priority_suggestions, 1):
        print(f"   {i:2d}. {label}")

    return priority_suggestions


if __name__ == "__main__":
    print("Choose training mode:")
    print("1. Train on priority labels (recommended)")
    print("2. Train on all labels (may take a while)")
    print("3. Train on custom selection")

    choice = input("\nEnter choice (1-3): ").strip()

    if choice == "1":
        priority_labels = suggest_priority_labels()
        print(f"\n🚀 Training on {len(priority_labels)} priority labels...")
        train_from_existing_labels(target_labels=priority_labels, emails_per_label=10)

    elif choice == "2":
        print(f"\n🚀 Training on ALL labels (this may take a while)...")
        train_from_existing_labels(emails_per_label=5)

    elif choice == "3":
        print("Enter label names separated by commas:")
        custom_labels = input().split(",")
        custom_labels = [label.strip() for label in custom_labels]
        print(f"\n🚀 Training on custom labels: {custom_labels}")
        train_from_existing_labels(target_labels=custom_labels, emails_per_label=10)

    else:
        print("Invalid choice. Use: python show_labels.py to see all labels.")
