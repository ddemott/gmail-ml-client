#!/usr/bin/env python3
"""
Low Confidence Email Review Tool
Specifically targets emails with confidence scores between spam and certain thresholds
"""

import os
import sys
from typing import Any, Dict, List

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.gmail_ml_client.cfg import THRESHOLDS
from src.gmail_ml_client.data_store import Message, get_session, init_db
from src.gmail_ml_client.model import predict


def review_low_confidence_emails(limit: int = 20) -> None:
    """
    Review emails with low confidence scores that need manual verification.

    Low confidence emails are those with:
    - Confidence < certain_threshold (0.92) AND
    - Spam score < spam_threshold (0.85)
    """
    print("🎯 Low Confidence Email Review Tool")
    print("=" * 60)
    print(f"Reviewing emails with confidence: {THRESHOLDS['spam']:.2f} - {THRESHOLDS['certain']:.2f}")
    print("These emails need manual verification before auto-processing")
    print()

    init_db()
    session = get_session()()

    try:
        # Get emails that might need review (unreviewed with predictions)
        print("🔍 Finding low confidence emails...")

        candidates = (
            session.query(Message)
            .filter(
                Message.target_label.isnot(None),
                Message.reviewed == False,
                Message.text.isnot(None),
                Message.label_guess.isnot(None)
            )
            .order_by(Message.created_at.desc())
            .limit(limit * 2)  # Get more candidates to filter
            .all()
        )

        if not candidates:
            print("✅ No emails found for review!")
            return

        # Filter for truly low confidence emails
        low_confidence_emails = []

        for msg in candidates:
            try:
                predictions, confidence, spam_scores = predict([msg.text])
                conf = confidence[0] if confidence else 0.0
                spam_score = spam_scores[0] if spam_scores else 0.5

                # Low confidence = not certain but not obviously spam
                if (conf < THRESHOLDS['certain'] and
                    spam_score < THRESHOLDS['spam'] and
                    conf > 0.1):  # Avoid completely uncertain predictions

                    low_confidence_emails.append({
                        "message": msg,
                        "confidence": conf,
                        "spam_score": spam_score,
                        "predicted_label": predictions[0] if predictions else "UNKNOWN"
                    })

            except Exception as e:
                print(f"⚠️  Error predicting for message {msg.id}: {e}")
                continue

        if not low_confidence_emails:
            print("✅ No low confidence emails found!")
            print("All recent emails have sufficient confidence scores.")
            return

        # Sort by confidence (lowest first)
        low_confidence_emails.sort(key=lambda x: x['confidence'])

        print(f"📊 Found {len(low_confidence_emails)} low confidence emails to review")
        print()

        reviewed_count = 0

        for i, candidate in enumerate(low_confidence_emails, 1):
            msg = candidate["message"]
            conf = candidate["confidence"]
            spam_score = candidate["spam_score"]
            predicted = candidate["predicted_label"]

            print(f"\n" + "=" * 70)
            print(f"📧 LOW CONFIDENCE EMAIL {i}/{len(low_confidence_emails)}")
            print(f"ID: {msg.id}")
            print(f"Predicted: {predicted}")
            print(f"Confidence: {conf:.3f} ⚠️  LOW")
            print(f"Spam Score: {spam_score:.3f}")
            print("-" * 70)

            # Show email snippet
            if msg.snippet:
                print("📄 SNIPPET:")
                print(f"   {msg.snippet[:200]}{'...' if len(msg.snippet) > 200 else ''}")

            # Show key content if available
            if msg.text:
                content = msg.text.replace("\n\n", "\n").replace("\r", "").strip()
                lines = [line.strip() for line in content.split("\n") if line.strip()]

                # Look for subject-like content
                subject_candidates = []
                for line in lines[:5]:  # Check first few lines
                    if len(line) < 100 and not line.startswith("http") and not "@" in line:
                        subject_candidates.append(line)

                if subject_candidates:
                    print("📧 SUBJECT:")
                    print(f"   {subject_candidates[0][:100]}")

            print("-" * 70)
            print("🎯 DECISION NEEDED:")
            print("1. ✅ Accept prediction")
            print("2. 🚫 Mark as SPAM")
            print("3. ✏️  Change category")
            print("4. 👀 Show full content")
            print("5. ⏭️  Skip for now")
            print("q. Quit review")

            while True:
                choice = input(f"\nChoose action (1-5, q): ").strip().lower()

                if choice == "1":
                    # Accept the prediction
                    msg.reviewed = True
                    msg.gold_label = predicted
                    session.commit()
                    print(f"✅ Accepted: {predicted}")
                    reviewed_count += 1
                    break

                elif choice == "2":
                    # Mark as SPAM
                    msg.target_label = "SPAM"
                    msg.gold_label = "SPAM"
                    msg.reviewed = True
                    session.commit()
                    print("🚫 Marked as SPAM")
                    reviewed_count += 1
                    break

                elif choice == "3":
                    # Change category
                    print("\nAvailable categories:")
                    print("• Work, Personal, Receipts, Finance")
                    print("• Newsletters, Social, Updates")
                    print("• Or enter any custom label")

                    new_label = input("New category: ").strip()
                    if new_label:
                        msg.target_label = new_label
                        msg.gold_label = new_label
                        msg.reviewed = True
                        session.commit()
                        print(f"✏️  Changed to: {new_label}")
                        reviewed_count += 1
                        break
                    else:
                        print("❌ No category entered")

                elif choice == "4":
                    # Show full content
                    print("\n📄 FULL EMAIL CONTENT:")
                    print("-" * 50)
                    if msg.text:
                        content = msg.text.replace("\r", "").strip()
                        print(content[:1500])  # Show up to 1500 characters
                        if len(content) > 1500:
                            print("... (truncated - use 'interactive_email_review.py' for full content)")
                    print("-" * 50)

                elif choice == "5":
                    # Skip
                    print("⏭️  Skipped")
                    break

                elif choice == "q":
                    # Quit
                    print("👋 Quitting review...")
                    break

                else:
                    print("❌ Invalid choice. Please enter 1-5 or q")

            if choice == "q":
                break

        print(f"\n🎉 REVIEW COMPLETE!")
        print("=" * 40)
        print(f"Low confidence emails reviewed: {reviewed_count}")
        print(f"Total processed: {i}")

        if reviewed_count > 0:
            print(f"\n🤖 Next Steps:")
            print("• Retrain model with corrections:")
            print("  python simple_train.py")
            print("• Your reviews improve future accuracy!")

    except KeyboardInterrupt:
        print(f"\n\n👋 Review interrupted. Saving changes...")
        session.commit()

    finally:
        session.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Review low confidence emails")
    parser.add_argument("--limit", type=int, default=20,
                       help="Maximum emails to review (default: 20)")

    args = parser.parse_args()
    review_low_confidence_emails(limit=args.limit)
