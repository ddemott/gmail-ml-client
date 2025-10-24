#!/usr/bin/env python3
"""
Move Emails to Folders - Apply your trained model predictions to actually move emails in Gmail
"""

import os
import sys

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import time

from data_store import Message, Session, init_db
from gmail_client import get_labels, get_message, list_messages, modify_labels
from model import predict
from preprocessor import extract_text


def get_label_id_map():
    """Get mapping of label names to IDs."""
    labels = get_labels()
    label_map = {}
    for label in labels:
        label_map[label["name"]] = label["id"]
    return label_map


def move_emails_to_folders(limit=50, dry_run=True):
    """
    Actually move emails to their predicted folders in Gmail.

    Args:
        limit: Number of recent emails to process
        dry_run: If True, only show what would be done without making changes
    """

    print("📧 Gmail ML Client - Move Emails to Folders")
    print("=" * 60)

    if dry_run:
        print("🔍 DRY RUN MODE - No actual changes will be made")
    else:
        print("⚡ LIVE MODE - Emails will actually be moved!")

    print("🤖 Using your trained model to organize emails...")
    print("")

    # Initialize database
    init_db()

    try:
        # Get label mapping
        print("🏷️  Getting Gmail label information...")
        label_map = get_label_id_map()
        print(f"📊 Found {len(label_map)} labels in your Gmail")

        # Get recent emails from Gmail
        print(f"📥 Fetching {limit} recent emails from Gmail...")
        messages = list_messages(max_results=limit)
        print(f"📧 Found {len(messages)} recent emails")

        if not messages:
            print("❌ No emails found")
            return

        session = Session()
        moved_count = 0
        skipped_count = 0
        error_count = 0

        try:
            print(f"\n🤖 Processing emails with your trained model...")

            for i, msg in enumerate(messages, 1):
                try:
                    print(f"\n📧 Email {i}/{len(messages)}")

                    # Get full message
                    full_msg = get_message(msg["id"])
                    text = extract_text(full_msg)

                    if not text or len(text.strip()) < 10:
                        print(f"   ⚠️  Skipped (no text content)")
                        skipped_count += 1
                        continue

                    # Get prediction from your trained model
                    predictions, confidence, spam_scores = predict([text])
                    prediction = predictions[0] if predictions else "UNKNOWN"
                    conf = confidence[0] if confidence else 0.0
                    spam_score = spam_scores[0] if spam_scores else 0.5

                    # Show prediction
                    snippet = full_msg.get("snippet", text[:100]).replace("\n", " ")[:80]
                    print(f'   📝 Snippet: "{snippet}..."')
                    print(f"   🎯 Predicted: {prediction} (confidence: {conf:.2f})")

                    # Check confidence threshold
                    if conf < 0.75:  # Only move high-confidence predictions
                        print(f"   ⚠️  Confidence too low ({conf:.2f}) - skipping")
                        skipped_count += 1
                        continue

                    # Check if target label exists
                    if prediction not in label_map:
                        print(f"   ❌ Label '{prediction}' not found in Gmail - skipping")
                        skipped_count += 1
                        continue

                    # Get current labels
                    current_labels = full_msg.get("labelIds", [])
                    target_label_id = label_map[prediction]

                    # Check if already has the target label
                    if target_label_id in current_labels:
                        print(f"   ✅ Already has label '{prediction}' - skipping")
                        skipped_count += 1
                        continue

                    # Prepare label changes
                    labels_to_add = [target_label_id]
                    labels_to_remove = []

                    # Remove from INBOX if moving to a category (except for important categories)
                    inbox_id = label_map.get("INBOX")
                    if inbox_id and inbox_id in current_labels:
                        if not prediction.startswith("CATEGORY_") or prediction == "SPAM":
                            labels_to_remove.append(inbox_id)

                    print(
                        f"   📋 Action: Add '{prediction}', Remove from INBOX: {len(labels_to_remove) > 0}"
                    )

                    if dry_run:
                        print(f"   🔍 DRY RUN - Would move email to '{prediction}'")
                        moved_count += 1
                    else:
                        # Actually modify the message
                        try:
                            modify_labels(msg["id"], add=labels_to_add, remove=labels_to_remove)
                            print(f"   ✅ Successfully moved to '{prediction}'")
                            moved_count += 1

                            # Small delay to be nice to Gmail API
                            time.sleep(0.2)

                        except Exception as e:
                            print(f"   ❌ Failed to move email: {e}")
                            error_count += 1

                    # Save the action to database for tracking
                    session = Session()
                    existing = session.query(Message).filter_by(id=msg["id"]).first()

                    if existing:
                        existing.target_label = prediction
                        existing.text = text
                    else:
                        message_obj = Message(
                            id=msg["id"],
                            snippet=full_msg.get("snippet", ""),
                            text=text,
                            target_label=prediction,
                            reviewed=False,
                        )
                        session.add(message_obj)

                    session.commit()
                    session.close()

                except Exception as e:
                    print(f"   ❌ Error processing email: {e}")
                    error_count += 1
                    continue

            print(f"\n🎉 PROCESSING COMPLETE!")
            print("=" * 50)
            print(f"📧 Total emails processed: {len(messages)}")
            if dry_run:
                print(f"🔍 Would move: {moved_count} emails")
            else:
                print(f"✅ Successfully moved: {moved_count} emails")
            print(f"⚠️  Skipped: {skipped_count} emails")
            print(f"❌ Errors: {error_count} emails")

            if dry_run and moved_count > 0:
                print(f"\n🚀 To actually move emails, run:")
                print(f"   python move_emails_to_folders.py --live")
            elif moved_count > 0:
                print(f"\n🎯 SUCCESS! Your emails have been organized!")
                print(f"📁 Check your Gmail - emails should be in their predicted folders")

        finally:
            session.close()

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()


def main():
    """Main function with command line argument handling."""
    import argparse

    parser = argparse.ArgumentParser(description="Move emails to folders based on ML predictions")
    parser.add_argument(
        "--live", action="store_true", help="Actually move emails (default is dry-run)"
    )
    parser.add_argument(
        "--limit", type=int, default=50, help="Number of emails to process (default: 50)"
    )

    args = parser.parse_args()

    # Confirm if not dry run
    if args.live:
        print("⚠️  WARNING: This will actually move emails in your Gmail!")
        confirmation = input("Are you sure you want to proceed? (type 'yes' to confirm): ")
        if confirmation.lower() != "yes":
            print("❌ Cancelled")
            return

    move_emails_to_folders(limit=args.limit, dry_run=not args.live)


if __name__ == "__main__":
    main()
