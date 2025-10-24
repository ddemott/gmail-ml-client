#!/usr/bin/env python3
"""
Train the model with a large amount of SPAM data to improve spam detection.
This will help the model learn to distinguish between spam and legitimate emails.
"""

import os
import random
import sys

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import time

from data_store import Message, Session, init_db
from gmail_client import get_labels, get_message, list_messages
from preprocessor import extract_text
from simple_train import simple_train


def main():
    try:
        print("🚀 Gmail ML Client - SPAM Training")
        print("=" * 60)
        print("Training the model with large amounts of SPAM data...")
        print("This will help distinguish spam from legitimate emails.")

        # Initialize database
        init_db()

        # Get spam-related labels
        print("\n📁 Finding SPAM labels...")
        labels = get_labels()

        spam_labels = []
        for label in labels:
            label_name = label["name"].lower()
            if any(spam_word in label_name for spam_word in ["spam", "trash"]):
                if label["name"] in ["SPAM", "TRASH"]:  # Focus on main spam folders
                    spam_labels.append(label)
                    print(f"   ✅ Will train on: {label['name']}")

        if not spam_labels:
            print("❌ No SPAM labels found!")
            return

        print(f"\n🎯 Processing SPAM data from {len(spam_labels)} folders...")

        total_processed = 0
        session = Session()

        try:
            for spam_label in spam_labels:
                label_id = spam_label["id"]
                label_name = spam_label["name"]

                print(f"\n📁 Processing {label_name}...")

                # Get a large number of spam messages for training
                max_messages = 500 if label_name == "SPAM" else 200  # More from main SPAM folder
                messages = list_messages(label_ids=[label_id], max_results=max_messages)

                if not messages:
                    print(f"   ⚠️  No messages found in {label_name}")
                    continue

                print(f"   📧 Found {len(messages)} messages, processing...")

                processed_count = 0

                for i, msg in enumerate(messages):
                    try:
                        # Get message details
                        full_msg = get_message(msg["id"])
                        text = extract_text(full_msg)

                        if not text or len(text.strip()) < 10:
                            continue

                        # Text is already cleaned by extract_text

                        # Check if message already exists
                        existing = session.query(Message).filter_by(id=msg["id"]).first()

                        if existing:
                            # Update existing message to mark as spam
                            existing.target_label = "SPAM"
                            existing.reviewed = True
                            existing.gold_label = "SPAM"  # User confirmed it's spam
                        else:
                            # Create new message entry
                            message_obj = Message(
                                id=msg["id"],
                                snippet=full_msg.get("snippet", ""),
                                text=text,
                                target_label="SPAM",
                                reviewed=True,
                                gold_label="SPAM",  # Mark as confirmed spam
                            )
                            session.add(message_obj)

                        processed_count += 1
                        total_processed += 1

                        # Show progress every 25 messages
                        if processed_count % 25 == 0:
                            print(
                                f"   ✅ Processed {processed_count}/{len(messages)} ({label_name})"
                            )
                            session.commit()  # Save progress periodically

                        # Add small delay to be nice to Gmail API
                        if i % 10 == 0:
                            time.sleep(0.1)

                    except Exception as e:
                        print(f"   ⚠️  Error processing message {i+1}: {e}")
                        continue

                session.commit()
                print(
                    f"   🎉 Completed: {processed_count} SPAM messages processed from {label_name}"
                )

            print(f"\n📊 SPAM TRAINING SUMMARY:")
            print("=" * 40)
            print(f"Total SPAM messages processed: {total_processed}")

            if total_processed > 0:
                print(f"\n🤖 Training model with SPAM data...")

                # Now train the model with all the data (including new spam data)
                print("🔄 Starting enhanced training with SPAM detection...")
                simple_train()

                print(f"\n🎉 SUCCESS!")
                print("=" * 40)
                print("✅ Model retrained with large SPAM dataset")
                print("✅ Spam detection should be significantly improved")
                print("✅ Model now knows patterns from your real spam emails")

                print(f"\n📝 NEXT STEPS:")
                print("• Test the improved model: python test_predictions.py")
                print("• Check spam detection on new emails")
                print("• The model should now better identify spam vs legitimate emails")

            else:
                print("❌ No SPAM data was processed")

        finally:
            session.close()

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
