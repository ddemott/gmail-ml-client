#!/usr/bin/env python3
"""
Train from existing Gmail folders/labels
This script gets emails that are already organized in your Gmail folders
and uses them as training data.
"""

import time
from collections import defaultdict

from data_store import init_db, mark_review, upsert_message
from gmail_client import get_labels, get_message, list_messages
from preprocessor import extract_text


def train_from_gmail_folders(target_labels=None, emails_per_folder=10):
    """
    Get emails from your existing Gmail folders and use them for training.

    Args:
        target_labels: List of Gmail label names to train on
        emails_per_folder: Number of emails to get from each folder
    """

    print("🎯 Training from Your Existing Gmail Folders")
    print("=" * 60)

    init_db()

    # Get your Gmail labels
    print("📋 Getting your Gmail labels...")
    all_labels = get_labels()
    user_labels = [l for l in all_labels if l.get("type") == "user"]

    print(f"📊 Found {len(user_labels)} custom labels in your Gmail")

    # Filter to target labels if specified
    if target_labels:
        user_labels = [l for l in user_labels if l.get("name") in target_labels]
        print(f"🎯 Focusing on {len(user_labels)} target labels")

    training_stats = defaultdict(int)

    for label_info in user_labels:
        label_name = label_info.get("name")
        label_id = label_info.get("id")

        print(f"\n📁 Processing folder: {label_name}")

        try:
            # Get messages from this folder using label name (works better than ID)
            query = f"label:{label_name}"
            print(f"   🔍 Searching with: {query}")

            message_ids = list_messages(query=query, max_results=emails_per_folder)

            if not message_ids:
                print(f"   📧 No messages found in this folder")
                continue

            print(f"   📧 Found {len(message_ids)} messages")

            processed = 0
            for i, msg_info in enumerate(message_ids):
                try:
                    msg_id = msg_info["id"]

                    # Get message details
                    message = get_message(msg_id)

                    if message:
                        # Extract text content
                        text = extract_text(message)
                        snippet = message.get("snippet", "")[:100]

                        # Store in database
                        upsert_message(msg_id, snippet, text)

                        # Mark as reviewed with this label
                        mark_review(msg_id, label_name)

                        processed += 1
                        training_stats[label_name] += 1

                        if processed % 3 == 0:
                            print(f"   ✅ Processed {processed}/{len(message_ids)}")

                    # Small delay to avoid rate limiting
                    time.sleep(0.1)

                except Exception as e:
                    print(f"   ⚠️  Error processing message: {e}")
                    continue

            print(f"   🎉 Completed: {processed} emails labeled as '{label_name}'")

        except Exception as e:
            print(f"   ❌ Error processing folder {label_name}: {e}")
            continue

    # Show training summary
    print(f"\n📊 Training Data Summary:")
    print("=" * 40)
    total_samples = sum(training_stats.values())

    for label, count in sorted(training_stats.items()):
        print(f"   {label}: {count} emails")

    print(f"\n🎉 Total training samples: {total_samples}")

    return training_stats


def suggest_priority_folders():
    """Suggest which folders to start with based on your labels."""

    priority_folders = [
        "[Gmail]/Amazon",
        "[Gmail]/Family",
        "[Gmail]/Bills",
        "[Gmail]/Job",
        "[Gmail]/Computer Related",
        "[Gmail]/Finance",
        "[Gmail]/Health",
        "[Gmail]/Auto Related",
        "[Gmail]/Paypal",
        "[Gmail]/Microsoft",
    ]

    print(f"💡 Suggested Priority Folders:")
    for i, folder in enumerate(priority_folders, 1):
        print(f"   {i:2d}. {folder}")

    return priority_folders


def main():
    """Main training workflow."""

    print("🚀 Gmail ML Client - Train from Existing Folders")
    print("=" * 60)

    print("Choose training approach:")
    print("1. Train on priority folders (recommended to start)")
    print("2. Train on ALL your folders (may take a while)")
    print("3. Train on specific folders (you choose)")
    print("4. Show available folders first")

    choice = input("\nEnter choice (1-4): ").strip()

    if choice == "1":
        priority_folders = suggest_priority_folders()
        print(f"\n🚀 Training on {len(priority_folders)} priority folders...")

        stats = train_from_gmail_folders(target_labels=priority_folders, emails_per_folder=8)

    elif choice == "2":
        print(f"\n🚀 Training on ALL folders (this will take a while)...")
        stats = train_from_gmail_folders(emails_per_folder=5)

    elif choice == "3":
        print("Enter folder names (separated by commas):")
        print("Example: [Gmail]/Amazon, [Gmail]/Family, [Gmail]/Bills")
        custom_folders = input().split(",")
        custom_folders = [folder.strip() for folder in custom_folders]

        print(f"\n🚀 Training on custom folders: {custom_folders}")
        stats = train_from_gmail_folders(target_labels=custom_folders, emails_per_folder=10)

    elif choice == "4":
        # Just show available folders
        all_labels = get_labels()
        user_labels = [l for l in all_labels if l.get("type") == "user"]

        print(f"\n📋 Your Available Gmail Folders:")
        for i, label in enumerate(sorted(user_labels, key=lambda x: x.get("name")), 1):
            print(f"   {i:2d}. {label.get('name')}")

        return

    else:
        print("Invalid choice.")
        return

    # After training data collection, offer to train the model
    if "stats" in locals() and stats:
        print(f"\n🤖 Ready to train the model!")
        train_now = input("Train the model now? (y/n): ").strip().lower()

        if train_now == "y":
            print(f"\n🔄 Training model...")
            import subprocess

            result = subprocess.run([".venv\\Scripts\\python.exe", "simple_train.py"])

            if result.returncode == 0:
                print(f"\n🎉 Training completed! Your model now knows your folder organization.")
            else:
                print(f"\n⚠️  Training had issues. Run 'python simple_train.py' manually.")


if __name__ == "__main__":
    main()
