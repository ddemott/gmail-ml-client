#!/usr/bin/env python3
"""
Fine-tune spam detection by adjusting the threshold and reviewing predictions.
Help balance between catching spam and avoiding false positives.
"""

import os
import sys

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


from gmail_client import get_message, list_messages
from model import load, predict
from preprocessor import extract_text


def main():
    try:
        print("🎛️ SPAM Detection Fine-Tuning")
        print("=" * 50)
        print("Let's find the right balance for spam detection")
        print("")

        # Load model
        vectorizer, label_encoder, model = load()

        # Get test emails
        messages = list_messages(max_results=10)
        test_emails = []

        print("📧 Analyzing email patterns...")

        for msg in messages[:10]:
            try:
                full_msg = get_message(msg["id"])
                text = extract_text(full_msg)
                headers = full_msg.get("payload", {}).get("headers", [])
                subject = next(
                    (h["value"] for h in headers if h["name"] == "Subject"), "No Subject"
                )
                sender = next((h["value"] for h in headers if h["name"] == "From"), "Unknown")

                # Get predictions
                predictions, confidences, spam_scores = predict([text])
                prediction = predictions[0]
                confidence = confidences[0]
                spam_score = spam_scores[0]

                test_emails.append(
                    {
                        "sender": sender,
                        "subject": subject,
                        "prediction": prediction,
                        "confidence": confidence,
                        "spam_score": spam_score,
                    }
                )

            except Exception:
                continue

        # Test different spam thresholds
        thresholds = [0.3, 0.5, 0.7, 0.8, 0.9]

        print("\n🎯 Testing Different SPAM Detection Thresholds:")
        print("=" * 60)

        for threshold in thresholds:
            spam_count = 0
            legitimate_count = 0

            print(
                f"\n📊 Threshold: {threshold:.1%} (emails with spam score > {threshold:.1%} = SPAM)"
            )
            print("-" * 50)

            for email in test_emails:
                is_spam = (email["prediction"] == "SPAM") or (email["spam_score"] > threshold)

                if is_spam:
                    spam_count += 1
                    status = "🚨 SPAM"
                else:
                    legitimate_count += 1
                    status = "✅ LEGIT"

                print(
                    f"{status} | {email['sender'][:30]:<30} | {email['subject'][:25]:<25} | Score: {email['spam_score']:.1%}"
                )

            print(f"\n   Results: {spam_count} spam, {legitimate_count} legitimate")

        print("\n💡 RECOMMENDATIONS:")
        print("=" * 40)
        print("🎯 Threshold 0.7 (70%) - Balanced approach")
        print("   • Catches obvious spam")
        print("   • Reduces false positives on newsletters/notifications")
        print("")
        print("🎯 Threshold 0.5 (50%) - More aggressive")
        print("   • Catches more potential spam")
        print("   • May flag some legitimate emails")
        print("")
        print("🎯 Threshold 0.9 (90%) - Conservative")
        print("   • Only flags very obvious spam")
        print("   • May miss some subtle spam")

        print("\n📝 NEXT STEPS:")
        print("1. Choose a threshold that works for your email patterns")
        print("2. Monitor results and adjust as needed")
        print("3. Add more training data for edge cases")
        print("4. Consider creating a 'Newsletter' category for legitimate marketing")

        print("\n🔧 TO ADJUST THRESHOLD:")
        print("• Modify the spam detection logic in your application")
        print("• Use spam_score > threshold instead of just prediction == 'SPAM'")
        print("• You can implement this in the prediction testing scripts")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
