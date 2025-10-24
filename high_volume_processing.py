#!/usr/bin/env python3
"""
High-Volume Email Processing - Process hundreds of emails efficiently
"""

import os
import sys

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import time

from sqlalchemy import func

from data_store import Message, Session, init_db
from gmail_client import get_message, list_messages
from model import predict
from preprocessor import extract_text


def high_volume_processing():
    print("🚀 Gmail ML Client - High-Volume Processing")
    print("=" * 60)
    print("Processing large batches of emails efficiently")
    print("")

    # Initialize database
    init_db()

    # Ask user how many emails to process
    while True:
        try:
            max_emails = input("How many emails to process? (50-1000, or 'max' for 1000): ").strip()
            if max_emails.lower() == "max":
                max_emails = 1000
                break
            else:
                max_emails = int(max_emails)
                if 50 <= max_emails <= 1000:
                    break
                else:
                    print("❌ Please enter a number between 50 and 1000")
        except ValueError:
            print("❌ Please enter a valid number or 'max'")

    print(f"\n📥 Fetching up to {max_emails} emails from Gmail...")

    try:
        messages = list_messages(max_results=max_emails)
        print(f"📊 Found {len(messages)} emails to process")

        if not messages:
            print("❌ No emails found")
            return

        session = Session()
        processed = 0
        classified = 0
        new_classifications = 0
        batch_size = 25  # Process in batches for efficiency

        try:
            print(f"\n🤖 Processing emails in batches of {batch_size}...")

            for i in range(0, len(messages), batch_size):
                batch = messages[i : i + batch_size]
                batch_num = (i // batch_size) + 1
                total_batches = (len(messages) + batch_size - 1) // batch_size

                print(f"\n📦 Batch {batch_num}/{total_batches} - Processing {len(batch)} emails...")

                batch_processed = 0
                batch_new = 0

                for msg in batch:
                    try:
                        # Quick check if already processed
                        existing = session.query(Message).filter_by(id=msg["id"]).first()

                        if existing and existing.target_label:
                            classified += 1
                            continue

                        # Get full message
                        full_msg = get_message(msg["id"])
                        text = extract_text(full_msg)

                        if not text or len(text.strip()) < 10:
                            continue

                        # Get prediction from your trained model
                        predictions, confidence, spam_scores = predict([text])
                        prediction = predictions[0] if predictions else "UNKNOWN"
                        conf = confidence[0] if confidence else 0.0

                        # Save or update the message with classification
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

                        batch_processed += 1
                        batch_new += 1
                        processed += 1
                        new_classifications += 1

                    except Exception as e:
                        print(f"      ⚠️  Error processing email: {e}")
                        continue

                # Commit batch
                session.commit()
                print(
                    f"   ✅ Batch complete: {batch_processed} processed, {len(batch) - batch_processed} already done"
                )

                # Show progress
                progress = ((i + len(batch)) / len(messages)) * 100
                print(f"   📊 Overall progress: {progress:.1f}% ({i + len(batch)}/{len(messages)})")

                # Small delay between batches
                time.sleep(0.5)

            # Show final statistics
            print(f"\n🎉 HIGH-VOLUME PROCESSING COMPLETE!")
            print("=" * 50)
            print(f"📧 Total emails found: {len(messages)}")
            print(f"✅ Already classified: {classified}")
            print(f"🆕 Newly classified: {new_classifications}")
            print(
                f"📊 Processing efficiency: {((classified + new_classifications) / len(messages) * 100):.1f}%"
            )

            # Show updated classification summary
            print(f"\n📊 UPDATED CLASSIFICATION SUMMARY:")
            print("-" * 40)

            # Get top 15 classifications
            results = (
                session.query(Message.target_label, func.count(Message.id).label("count"))
                .filter(Message.target_label.isnot(None))
                .group_by(Message.target_label)
                .order_by(func.count(Message.id).desc())
                .limit(15)
                .all()
            )

            total_classified_now = sum(result.count for result in results)

            for result in results:
                percentage = (result.count / total_classified_now) * 100
                print(f"   {result.target_label}: {result.count} emails ({percentage:.1f}%)")

            print(f"\n🎯 NEXT STEPS:")
            print("• Start web interface: python -m uvicorn api:app --host localhost --port 8000")
            print("• Review classifications at: http://localhost:8000/docs")
            print("• Your email organization system is running at scale!")

        finally:
            session.close()

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    high_volume_processing()
