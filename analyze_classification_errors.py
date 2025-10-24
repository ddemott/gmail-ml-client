#!/usr/bin/env python3
"""
Error Analysis Tool - Find potentially misclassified emails from recent processing
"""

import os
import sys

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import desc, func

from data_store import Message, Session, init_db
from model import predict


def analyze_classification_errors():
    print("🔍 Classification Error Analysis")
    print("=" * 60)
    print("Analyzing recent 1,000-email processing for potential errors")
    print("")

    # Initialize database
    init_db()
    session = Session()

    try:
        # Get statistics on recent processing
        total_emails = session.query(Message).filter(Message.target_label.isnot(None)).count()

        print(f"📊 Total classified emails in system: {total_emails}")

        # Find emails with low confidence that might be errors
        print(f"\n🔍 Finding potentially problematic classifications...")

        # Get recent unreviewed emails
        recent_emails = (
            session.query(Message)
            .filter(
                Message.target_label.isnot(None),
                Message.reviewed == False,  # Auto-classified
                Message.text.isnot(None),
            )
            .order_by(desc(Message.id))
            .limit(100)
            .all()
        )

        print(f"📧 Checking {len(recent_emails)} recent auto-classified emails...")

        potential_errors = []
        low_confidence = []
        inconsistencies = []
        spam_borderline = []

        for i, msg in enumerate(recent_emails):
            try:
                # Re-classify with current model
                predictions, confidence, spam_scores = predict([msg.text])
                current_prediction = predictions[0] if predictions else "UNKNOWN"
                conf = confidence[0] if confidence else 0.0
                spam_score = spam_scores[0] if spam_scores else 0.5

                text_snippet = msg.text[:80].replace("\n", " ").strip() + "..."

                # Check for various types of potential issues

                # 1. Model inconsistency (prediction changed)
                if current_prediction != msg.target_label:
                    inconsistencies.append(
                        {
                            "id": msg.id,
                            "text": text_snippet,
                            "stored": msg.target_label,
                            "predicted": current_prediction,
                            "confidence": conf,
                            "reason": "Model prediction changed",
                        }
                    )

                # 2. Low confidence classifications
                elif conf < 0.5:
                    low_confidence.append(
                        {
                            "id": msg.id,
                            "text": text_snippet,
                            "label": msg.target_label,
                            "confidence": conf,
                            "reason": f"Low confidence ({conf:.2f})",
                        }
                    )

                # 3. Borderline spam (might be false positive/negative)
                if 0.3 < spam_score < 0.7 and msg.target_label != "SPAM":
                    spam_borderline.append(
                        {
                            "id": msg.id,
                            "text": text_snippet,
                            "label": msg.target_label,
                            "spam_score": spam_score,
                            "reason": f"Borderline spam score ({spam_score:.2f})",
                        }
                    )

                # Show progress
                if (i + 1) % 25 == 0:
                    print(f"   📊 Checked {i + 1}/{len(recent_emails)} emails...")

            except Exception as e:
                print(f"   ⚠️  Error checking email {msg.id}: {e}")
                continue

        # Report findings
        print(f"\n📊 ERROR ANALYSIS RESULTS")
        print("=" * 40)
        print(f"Emails analyzed: {len(recent_emails)}")
        print(f"Model inconsistencies: {len(inconsistencies)}")
        print(f"Low confidence classifications: {len(low_confidence)}")
        print(f"Borderline spam classifications: {len(spam_borderline)}")

        # Show model inconsistencies (most important)
        if inconsistencies:
            print(f"\n❌ MODEL INCONSISTENCIES (Potential Errors):")
            print("-" * 50)

            for i, error in enumerate(inconsistencies[:10], 1):  # Show top 10
                print(f"\n{i}. Email ID: {error['id']}")
                print(f"   Text: \"{error['text']}\"")
                print(f"   Stored as: {error['stored']}")
                print(
                    f"   Model now predicts: {error['predicted']} (conf: {error['confidence']:.2f})"
                )
                print(f"   Issue: {error['reason']}")

                # Show pattern analysis
                if "job" in error["text"].lower() and error["stored"] != error["predicted"]:
                    if "job" in error["predicted"].lower() or "job" in error["stored"].lower():
                        print(f"   🎯 Pattern: Job-related classification difference")

                if error["stored"] == "SPAM" and error["predicted"] != "SPAM":
                    print(
                        f"   🚨 Pattern: Potential false positive (legitimate email marked as spam)"
                    )

                if error["stored"] != "SPAM" and error["predicted"] == "SPAM":
                    print(f"   🚨 Pattern: Potential false negative (spam not detected)")

        # Show low confidence classifications
        if low_confidence:
            print(f"\n⚠️  LOW CONFIDENCE CLASSIFICATIONS:")
            print("-" * 40)

            for i, issue in enumerate(low_confidence[:5], 1):  # Show top 5
                print(f"\n{i}. Email ID: {issue['id']}")
                print(f"   Text: \"{issue['text']}\"")
                print(f"   Classified as: {issue['label']}")
                print(f"   Confidence: {issue['confidence']:.2f}")
                print(f"   Issue: {issue['reason']}")

        # Show borderline spam
        if spam_borderline:
            print(f"\n🚨 BORDERLINE SPAM CLASSIFICATIONS:")
            print("-" * 40)

            for i, issue in enumerate(spam_borderline[:5], 1):  # Show top 5
                print(f"\n{i}. Email ID: {issue['id']}")
                print(f"   Text: \"{issue['text']}\"")
                print(f"   Classified as: {issue['label']}")
                print(f"   Spam score: {issue['spam_score']:.2f}")
                print(f"   Issue: {issue['reason']}")

        # Overall assessment
        total_issues = len(inconsistencies) + len(low_confidence) + len(spam_borderline)

        print(f"\n🎯 OVERALL ASSESSMENT:")
        print("=" * 30)

        if total_issues == 0:
            print("🎉 EXCELLENT! No significant issues found!")
            print("✅ Your model is performing consistently")
            print("✅ All classifications appear correct")

        elif total_issues < 5:
            print("✅ VERY GOOD! Very few potential issues")
            print(f"📊 Issue rate: {(total_issues/len(recent_emails)*100):.1f}%")
            print("🎯 Model performing at production quality")

        elif total_issues < 15:
            print("👍 GOOD! Some issues but overall solid performance")
            print(f"📊 Issue rate: {(total_issues/len(recent_emails)*100):.1f}%")
            print("🔧 May benefit from reviewing flagged emails")

        else:
            print("⚠️  NEEDS ATTENTION! Multiple potential issues found")
            print(f"📊 Issue rate: {(total_issues/len(recent_emails)*100):.1f}%")
            print("🔧 Recommend reviewing and correcting flagged emails")

        print(f"\n💡 NEXT STEPS:")
        if inconsistencies:
            print("• Review model inconsistencies first (highest priority)")
        if low_confidence:
            print("• Check low-confidence classifications")
        if spam_borderline:
            print("• Verify borderline spam classifications")
        print("• Use manual correction tools to fix any confirmed errors")

    finally:
        session.close()


if __name__ == "__main__":
    analyze_classification_errors()
