#!/usr/bin/env python3
"""
Check the SPAM folder specifically and analyze spam content.
"""

import os
import sys

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from gmail_client import get_labels, get_message, list_messages
from preprocessor import extract_text


def main():
    try:
        print("🕵️ Analyzing SPAM Folder for Training Data")
        print("=" * 60)

        # Get all labels to find spam-related ones
        print("📁 Finding spam-related labels...")
        labels = get_labels()

        spam_labels = []
        for label in labels:
            label_name = label["name"].lower()
            if any(spam_word in label_name for spam_word in ["spam", "junk", "trash"]):
                spam_labels.append(label)
                print(f"   Found: {label['name']} (ID: {label['id']})")

        if not spam_labels:
            print("❌ No SPAM labels found. Using Gmail's built-in SPAM folder...")
            # Look for Gmail's spam folder
            for label in labels:
                if label["name"] == "SPAM":
                    spam_labels = [label]
                    break

        if not spam_labels:
            print("❌ No SPAM folder found!")
            print("💡 Tip: Gmail's spam folder should automatically exist")
            return

        total_spam_count = 0
        all_spam_messages = []

        for spam_label in spam_labels:
            label_id = spam_label["id"]
            label_name = spam_label["name"]

            print(f"\n📊 Checking {label_name}...")

            # Get messages from this spam folder (get more for training)
            messages = list_messages(label_ids=[label_id], max_results=1000)
            count = len(messages) if messages else 0
            total_spam_count += count

            print(f"   📧 Found {count} spam messages")

            if messages:
                all_spam_messages.extend(messages[:100])  # Take up to 100 for analysis

                # Analyze a few spam messages to see content
                print(f"   🔍 Analyzing sample spam content...")
                sample_messages = messages[:3]  # Look at first 3

                for i, msg in enumerate(sample_messages, 1):
                    try:
                        full_msg = get_message(msg["id"])
                        headers = full_msg.get("payload", {}).get("headers", [])
                        subject = next(
                            (h["value"] for h in headers if h["name"] == "Subject"), "No Subject"
                        )
                        sender = next(
                            (h["value"] for h in headers if h["name"] == "From"), "Unknown"
                        )

                        print(f"      {i}. From: {sender[:50]}...")
                        print(f"         Subject: {subject[:60]}...")

                    except Exception as e:
                        print(f"      {i}. Error reading message: {e}")

        print(f"\n📈 SPAM ANALYSIS SUMMARY:")
        print("=" * 40)
        print(f"Total SPAM messages found: {total_spam_count}")
        print(f"Available for training: {min(total_spam_count, 500)}")

        if total_spam_count > 0:
            print(f"\n💡 RECOMMENDATIONS:")
            print("• You have enough spam data for good training!")
            print("• Gmail automatically moves spam to SPAM folder")
            print("• We can train with up to 500 spam messages")
            print("• This will help the model learn spam patterns")

            print(f"\n🚀 READY TO TRAIN:")
            print("• Run: python train_spam_data.py")
            print("• This will add spam training to your existing model")
        else:
            print(f"\n⚠️  LIMITED SPAM DATA:")
            print("• Consider manually marking some emails as spam")
            print("• Gmail will learn and auto-detect more spam over time")
            print("• You can still train with whatever spam data exists")

    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()
