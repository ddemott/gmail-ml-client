#!/usr/bin/env python3
"""
Real Email Processing Script - Run your trained model on actual Gmail
"""

import os
import sys

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import time

from data_store import Message, Session, init_db
from gmail_client import get_message, list_messages
from model import predict
from preprocessor import extract_text


def process_real_emails():
    print("📧 Gmail ML Client - Real Email Processing")
    print("=" * 60)
    print("Processing your actual Gmail with the trained model")
    print("")

    # Initialize database
    init_db()

    # Get recent emails from Gmail
    print("📥 Fetching recent emails from Gmail...")
    try:
        # Get last 200 emails for more comprehensive processing
        messages = list_messages(max_results=200)
        print(f"📊 Found {len(messages)} recent emails")

        if not messages:
            print("❌ No new emails found")
            return

        session = Session()
        processed = 0
        classified = 0

        try:
            print("\n🤖 Processing emails with your trained model...")

            for i, msg in enumerate(messages, 1):
                try:
                    print(f"\n📧 Email {i}/{len(messages)}")

                    # Get full message
                    full_msg = get_message(msg["id"])
                    text = extract_text(full_msg)

                    if not text or len(text.strip()) < 10:
                        print("   ⚠️  Skipped (no text content)")
                        continue

                    # Check if already processed
                    existing = session.query(Message).filter_by(id=msg["id"]).first()

                    if existing and existing.target_label:
                        print(f"   ✅ Already classified as: {existing.target_label}")
                        classified += 1
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

                    if spam_score > 0.7:
                        print(f"   🚨 Spam Score: {spam_score:.2f} - Likely SPAM")

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
                            reviewed=False,  # Not manually reviewed yet
                        )
                        session.add(message_obj)

                    processed += 1

                    # Commit every 10 messages
                    if processed % 10 == 0:
                        session.commit()
                        print("   💾 Saved batch of 10 classifications")

                    # Small delay to be nice to Gmail API
                    time.sleep(0.1)

                except Exception as e:
                    print(f"   ❌ Error processing email: {e}")
                    continue

            # Final commit
            session.commit()

            print("\n🎉 PROCESSING COMPLETE!")
            print("=" * 40)
            print(f"📧 Total emails processed: {processed}")
            print(f"✅ Already classified: {classified}")
            print(f"🆕 Newly classified: {processed}")
            print("🎯 Your model automatically sorted emails into your 54 categories!")

            # Show classification summary
            print("\n📊 CLASSIFICATION SUMMARY:")
            print("-" * 30)

            # Get classification counts using SQLAlchemy ORM
            from sqlalchemy import func

            results = (
                session.query(Message.target_label, func.count(Message.id).label("count"))
                .filter(Message.target_label.isnot(None))
                .group_by(Message.target_label)
                .order_by(func.count(Message.id).desc())
                .limit(10)
                .all()
            )

            for result in results:
                print(f"   {result.target_label}: {result.count} emails")

            print("\n🎯 NEXT STEPS:")
            print("1. Review classifications in web interface: http://localhost:8000/docs")
            print("2. Use /api/messages to see all classified emails")
            print("3. Correct any mistakes with /api/review")
            print("4. Your emails are now automatically organized!")

        finally:
            session.close()

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    process_real_emails()
