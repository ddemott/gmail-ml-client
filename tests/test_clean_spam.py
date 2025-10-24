#!/usr/bin/env python3
"""
Test the cleaned spam model to see if it's better at distinguishing
genuine spam from legitimate emails.
"""

import os
import sys

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.gmail_ml_client.gmail_client import get_message, list_messages
from src.gmail_ml_client.model import load, predict
from src.gmail_ml_client.preprocessor import extract_text


def main():
    try:
        print("🧪 Testing Cleaned SPAM Model")
        print("=" * 50)
        print("Testing model trained ONLY on genuine SPAM folder data")
        print("(No more TRASH folder contamination)")
        print("")

        # Load the cleaned model
        print("🤖 Loading cleaned model...")
        try:
            vectorizer, label_encoder, model = load()
            classes = label_encoder.classes_
            print(f"✅ Model loaded! Categories: {len(classes)}")

            # Show if SPAM is in the classes
            if "SPAM" in classes:
                print("✅ SPAM detection enabled")
            else:
                print("⚠️  No SPAM category found")

        except Exception as e:
            print(f"❌ Error loading model: {e}")
            return

        print("\n🔍 Testing on recent inbox emails...")

        # Get recent messages from inbox
        messages = list_messages(max_results=15)
        if not messages:
            print("❌ No messages found")
            return

        print(f"📧 Testing {len(messages)} recent emails...\n")

        spam_detected = 0
        legitimate_detected = 0

        for i, msg in enumerate(messages, 1):
            try:
                # Get message details
                full_msg = get_message(msg["id"])
                text = extract_text(full_msg)

                # Get subject and sender
                headers = full_msg.get("payload", {}).get("headers", [])
                subject = next(
                    (h["value"] for h in headers if h["name"] == "Subject"), "No Subject"
                )
                sender = next(
                    (h["value"] for h in headers if h["name"] == "From"), "Unknown Sender"
                )

                # Make prediction
                predictions, confidences, spam_scores = predict([text])
                prediction = predictions[0]
                confidence = confidences[0]
                spam_score = spam_scores[0]

                # Classify result
                is_spam = prediction == "SPAM" or spam_score > 0.7
                if is_spam:
                    spam_detected += 1
                    status = "🚨 SPAM"
                else:
                    legitimate_detected += 1
                    status = "✅ LEGITIMATE"

                print(f"📧 Email {i}: {status}")
                print(f"   From: {sender[:50]}...")
                print(f"   Subject: {subject[:50]}...")
                print(f"   🎯 Category: {prediction} (confidence: {confidence:.1%})")
                print(f"   🕵️ Spam Score: {spam_score:.1%}")
                print()

            except Exception as e:
                print(f"❌ Error processing email {i}: {e}")

        print("📊 DETECTION SUMMARY:")
        print("=" * 30)
        print(f"🚨 Emails flagged as SPAM: {spam_detected}")
        print(f"✅ Emails classified as legitimate: {legitimate_detected}")
        print(f"📧 Total emails tested: {spam_detected + legitimate_detected}")

        print("\n💡 ABOUT THE CLEANED MODEL:")
        print("• Trained ONLY on genuine SPAM folder emails")
        print("• Removed TRASH folder contamination")
        print("• Should have fewer false positives")
        print("• Better at identifying real spam patterns")

        print("\n🔍 Look for these improvements:")
        print("• Legitimate emails should rarely be flagged as spam")
        print("• Real spam should be detected with high confidence")
        print("• Business emails, newsletters should be categorized properly")

    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()
