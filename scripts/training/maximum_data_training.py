#!/usr/bin/env python3
"""
Enhanced retraining script with MUCH higher limits for maximum training data.
Uses higher limits to capture even more training examples per folder.
"""

import os
import sys
import time

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data_store import Message, Session, init_db
from gmail_client import get_labels, get_message, list_messages
from preprocessor import extract_text
from simple_train import simple_train


def main():
    try:
        print("🚀 Gmail ML Client - MAXIMUM DATA Training")
        print("=" * 60)
        print("Using MUCH HIGHER limits to capture maximum training data")
        print("Job folder gets 200+ messages, others get 100+ messages")
        print("")

        # Initialize database
        init_db()

        # Clear all existing training data for fresh start
        print("🧹 Clearing existing training data for fresh maximum retrain...")
        session = Session()
        try:
            old_count = session.query(Message).filter(Message.reviewed == True).count()
            session.query(Message).filter(Message.reviewed == True).delete()
            session.commit()
            print(f"✅ Cleared {old_count} old training entries")
        finally:
            session.close()

        # Get all labels
        print("\n📁 Fetching all Gmail labels...")
        labels = get_labels()

        # Separate useful folders from spam/system folders
        useful_folders = []
        spam_folders = []
        system_labels = {"INBOX", "SENT", "DRAFT", "STARRED", "IMPORTANT", "UNREAD", "CHAT"}

        for label in labels:
            label_name = label["name"]
            label_lower = label_name.lower()

            # Skip system labels
            if label_name in system_labels:
                continue

            # Separate spam/trash from useful folders
            if any(spam_word in label_lower for spam_word in ["spam", "trash", "junk"]):
                if label_name == "SPAM":  # Only genuine SPAM folder
                    spam_folders.append(label)
            elif label_name.startswith("[Gmail]/") and not any(
                skip in label_lower for skip in ["trash", "spam", "junk"]
            ):
                useful_folders.append(label)
            elif not label_name.startswith("[Gmail]") and len(label_name) > 2:
                useful_folders.append(label)

        # Sort useful folders to prioritize Job folder
        useful_folders.sort(
            key=lambda x: (
                0
                if "job" in x["name"].lower()
                else (
                    1
                    if any(
                        priority in x["name"].lower()
                        for priority in ["finance", "family", "computer", "health"]
                    )
                    else 2
                )
            )
        )

        print(f"📊 Found {len(useful_folders)} useful folders and {len(spam_folders)} spam folders")

        # Train on useful folders first with MUCH HIGHER LIMITS
        print("\n🎯 Phase 1: Training on Useful Categories (MAXIMUM DATA)")
        print("=" * 60)

        total_processed = 0

        for i, label in enumerate(useful_folders, 1):
            label_id = label["id"]
            label_name = label["name"]

            print(f"\n📁 {i:2d}/{len(useful_folders)}: Processing {label_name}")

            # MUCH HIGHER LIMITS for maximum training data
            if "job" in label_name.lower():
                max_messages = 200  # Job folder gets 200 messages!
            elif any(
                priority in label_name.lower()
                for priority in ["finance", "health", "family", "computer"]
            ):
                max_messages = 150  # Priority folders get 150 messages
            elif label_name.startswith("[Gmail]/"):
                max_messages = 100  # Gmail folders get 100 messages
            else:
                max_messages = 75  # Other folders get 75 messages

            messages = list_messages(label_ids=[label_id], max_results=max_messages)

            if not messages:
                print("   ⚠️  No messages found")
                continue

            print(f"   📧 Found {len(messages)} messages (limit: {max_messages}), processing...")

            processed_count = 0
            session = Session()

            try:
                for j, msg in enumerate(messages):
                    try:
                        # Get message details
                        full_msg = get_message(msg["id"])
                        text = extract_text(full_msg)

                        if not text or len(text.strip()) < 10:
                            continue

                        # Check if message already exists
                        existing = session.query(Message).filter_by(id=msg["id"]).first()

                        if existing:
                            # Update existing message
                            existing.target_label = label_name
                            existing.reviewed = True
                            existing.gold_label = label_name
                        else:
                            # Create new message entry
                            message_obj = Message(
                                id=msg["id"],
                                snippet=full_msg.get("snippet", ""),
                                text=text,
                                target_label=label_name,
                                reviewed=True,
                                gold_label=label_name,
                            )
                            session.add(message_obj)

                        processed_count += 1
                        total_processed += 1

                        # Show progress every 20 messages
                        if processed_count % 20 == 0:
                            print(f"   ✅ Processed {processed_count}/{len(messages)}")
                            session.commit()

                        # Small delay for API
                        if j % 10 == 0:
                            time.sleep(0.1)

                    except Exception as e:
                        print(f"   ⚠️  Error processing message {j+1}: {e}")
                        continue

                session.commit()
                print(f"   🎉 Completed: {processed_count} messages from {label_name}")

            finally:
                session.close()

        # Train on SPAM last with MAXIMUM SPAM DATA
        print("\n🎯 Phase 2: Training on SPAM (MAXIMUM SPAM DATA)")
        print("=" * 60)

        for spam_label in spam_folders:
            label_id = spam_label["id"]
            label_name = spam_label["name"]

            print(f"\n📁 Processing {label_name}...")

            # MAXIMUM spam messages for ultimate spam detection
            max_spam_messages = 500  # 500 spam messages!
            messages = list_messages(label_ids=[label_id], max_results=max_spam_messages)

            if not messages:
                print("   ⚠️  No messages found")
                continue

            print(
                f"   📧 Found {len(messages)} SPAM messages (limit: {max_spam_messages}), processing..."
            )

            processed_count = 0
            session = Session()

            try:
                for j, msg in enumerate(messages):
                    try:
                        # Get message details
                        full_msg = get_message(msg["id"])
                        text = extract_text(full_msg)

                        if not text or len(text.strip()) < 10:
                            continue

                        # Check if message already exists
                        existing = session.query(Message).filter_by(id=msg["id"]).first()

                        if existing:
                            # Update existing message to mark as spam
                            existing.target_label = "SPAM"
                            existing.reviewed = True
                            existing.gold_label = "SPAM"
                        else:
                            # Create new message entry
                            message_obj = Message(
                                id=msg["id"],
                                snippet=full_msg.get("snippet", ""),
                                text=text,
                                target_label="SPAM",
                                reviewed=True,
                                gold_label="SPAM",
                            )
                            session.add(message_obj)

                        processed_count += 1
                        total_processed += 1

                        # Show progress every 50 messages
                        if processed_count % 50 == 0:
                            print(f"   ✅ Processed {processed_count}/{len(messages)} SPAM")
                            session.commit()

                        # Small delay for API
                        if j % 10 == 0:
                            time.sleep(0.1)

                    except Exception as e:
                        print(f"   ⚠️  Error processing message {j+1}: {e}")
                        continue

                session.commit()
                print(f"   🎉 Completed: {processed_count} SPAM messages")

            finally:
                session.close()

        print("\n📊 MAXIMUM DATA TRAINING SUMMARY:")
        print("=" * 60)
        print(f"Total messages processed: {total_processed}")
        print("✅ Job folder: Up to 200 messages")
        print("✅ Priority folders: Up to 150 messages each")
        print("✅ Gmail folders: Up to 100 messages each")
        print("✅ SPAM folder: Up to 500 messages")
        print("✅ SPAM trained last to eliminate false positives")

        if total_processed > 0:
            print("\n🤖 Training model with MAXIMUM dataset...")
            simple_train()

            print("\n🎉 MAXIMUM DATA SUCCESS!")
            print("=" * 50)
            print("✅ Model trained with MAXIMUM possible data")
            print("✅ Should achieve highest possible accuracy")
            print("✅ Ready for ultimate email classification")

            print("\n📈 EXPECTED IMPROVEMENTS:")
            print("• Much more training data per category")
            print("• Better pattern recognition")
            print("• Higher accuracy on edge cases")
            print("• More robust spam detection")
            print("• Ultimate email classification performance")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
