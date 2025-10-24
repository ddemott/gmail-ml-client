#!/usr/bin/env python3
"""
Interactive Email Review Tool - Review and recategorize emails with full content
"""

import os
import sys

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data_store import Message, Session, init_db
from model import predict


def interactive_email_review():
    print("📧 Interactive Email Review Tool")
    print("=" * 60)
    print("Review emails with full content and recategorize as needed")
    print("")

    init_db()
    session = Session()

    try:
        # Get emails that need review
        print("🔍 Finding emails that need review...")

        # Get low-confidence emails from recent processing
        emails_to_review = (
            session.query(Message)
            .filter(
                Message.target_label.isnot(None),
                Message.reviewed == False,
                Message.text.isnot(None),
            )
            .order_by(Message.id.desc())
            .limit(20)
            .all()
        )

        if not emails_to_review:
            print("✅ No emails need review!")
            return

        print(f"📊 Found {len(emails_to_review)} emails to review")

        # Re-check these emails for confidence
        review_candidates = []

        for msg in emails_to_review:
            try:
                predictions, confidence, spam_scores = predict([msg.text])
                conf = confidence[0] if confidence else 0.0
                spam_score = spam_scores[0] if spam_scores else 0.5

                # Include low confidence or borderline spam
                if conf < 0.6 or (0.2 < spam_score < 0.8):
                    review_candidates.append(
                        {"message": msg, "confidence": conf, "spam_score": spam_score}
                    )
            except:
                continue

        if not review_candidates:
            print("✅ All recent emails have good confidence scores!")
            return

        print(f"\n📋 Reviewing {len(review_candidates)} emails needing attention...")

        reviewed_count = 0

        for i, candidate in enumerate(review_candidates, 1):
            msg = candidate["message"]
            conf = candidate["confidence"]
            spam_score = candidate["spam_score"]

            print(f"\n" + "=" * 70)
            print(f"📧 EMAIL {i}/{len(review_candidates)}")
            print(f"ID: {msg.id}")
            print(f"Current Label: {msg.target_label}")
            print(f"Confidence: {conf:.2f}")
            print(f"Spam Score: {spam_score:.2f}")
            print("-" * 70)

            # Show email content with better formatting
            if msg.text:
                # Clean up the text for better readability
                content = msg.text.replace("\n\n", "\n").replace("\r", "").strip()
                lines = content.split("\n")

                # Show first 10 lines or 500 characters, whichever is less
                preview_lines = []
                char_count = 0
                for line in lines:
                    if len(preview_lines) >= 10 or char_count > 500:
                        break
                    preview_lines.append(line.strip())
                    char_count += len(line)

                print("📄 EMAIL CONTENT:")
                for line in preview_lines:
                    if line:  # Skip empty lines
                        print(f"   {line}")

                if len(lines) > len(preview_lines) or char_count > 500:
                    print("   ... (content truncated)")

            print("-" * 70)
            print("📋 REVIEW OPTIONS:")
            print("1. Keep current classification")
            print("2. Mark as SPAM")
            print("3. Change to [Gmail]/Job")
            print("4. Change to [Gmail]/Finance")
            print("5. Change to CATEGORY_PROMOTIONS")
            print("6. Change to CATEGORY_PERSONAL")
            print("7. Change to CATEGORY_UPDATES")
            print("8. Enter custom category")
            print("9. Show more content")
            print("0. Skip this email")
            print("q. Quit review")

            while True:
                choice = input(f"\nChoose option (0-9, q): ").strip().lower()

                if choice == "1":
                    # Keep current, just mark as reviewed
                    msg.reviewed = True
                    session.commit()
                    print(f"✅ Kept as: {msg.target_label}")
                    reviewed_count += 1
                    break

                elif choice == "2":
                    # Mark as SPAM
                    msg.target_label = "SPAM"
                    msg.reviewed = True
                    session.commit()
                    print(f"🚫 Changed to: SPAM")
                    reviewed_count += 1
                    break

                elif choice == "3":
                    # Job category
                    msg.target_label = "[Gmail]/Job"
                    msg.reviewed = True
                    session.commit()
                    print(f"💼 Changed to: [Gmail]/Job")
                    reviewed_count += 1
                    break

                elif choice == "4":
                    # Finance category
                    msg.target_label = "[Gmail]/Finance"
                    msg.reviewed = True
                    session.commit()
                    print(f"💰 Changed to: [Gmail]/Finance")
                    reviewed_count += 1
                    break

                elif choice == "5":
                    # Promotions
                    msg.target_label = "CATEGORY_PROMOTIONS"
                    msg.reviewed = True
                    session.commit()
                    print(f"📢 Changed to: CATEGORY_PROMOTIONS")
                    reviewed_count += 1
                    break

                elif choice == "6":
                    # Personal
                    msg.target_label = "CATEGORY_PERSONAL"
                    msg.reviewed = True
                    session.commit()
                    print(f"👤 Changed to: CATEGORY_PERSONAL")
                    reviewed_count += 1
                    break

                elif choice == "7":
                    # Updates
                    msg.target_label = "CATEGORY_UPDATES"
                    msg.reviewed = True
                    session.commit()
                    print(f"📰 Changed to: CATEGORY_UPDATES")
                    reviewed_count += 1
                    break

                elif choice == "8":
                    # Custom category
                    custom_label = input("Enter custom category: ").strip()
                    if custom_label:
                        msg.target_label = custom_label
                        msg.reviewed = True
                        session.commit()
                        print(f"🏷️  Changed to: {custom_label}")
                        reviewed_count += 1
                        break
                    else:
                        print("❌ Invalid category")

                elif choice == "9":
                    # Show more content
                    print("\n📄 FULL EMAIL CONTENT:")
                    print("-" * 50)
                    if msg.text:
                        content = msg.text.replace("\r", "").strip()
                        print(content[:2000])  # Show up to 2000 characters
                        if len(content) > 2000:
                            print("... (truncated)")
                    print("-" * 50)

                elif choice == "0":
                    # Skip
                    print("⏭️  Skipped")
                    break

                elif choice == "q":
                    # Quit
                    print("👋 Quitting review...")
                    break

                else:
                    print("❌ Invalid choice. Please enter 0-9 or q")

            if choice == "q":
                break

        print(f"\n🎉 REVIEW COMPLETE!")
        print("=" * 40)
        print(f"Emails reviewed: {reviewed_count}")
        print(f"Total processed: {i}")

        if reviewed_count > 0:
            print(f"\n🤖 Recommendations:")
            print("• Consider retraining the model with these corrections:")
            print("  python simple_train.py")
            print("• Your corrections will improve future classifications!")

    except KeyboardInterrupt:
        print(f"\n\n👋 Review interrupted. Saving changes...")
        session.commit()

    finally:
        session.close()


if __name__ == "__main__":
    interactive_email_review()
