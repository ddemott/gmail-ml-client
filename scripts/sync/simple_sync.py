#!/usr/bin/env python3
"""
Simple approach: Get recent emails and manually review/label them
"""

import time

from data_store import init_db, upsert_message
from gmail_client import get_message, list_messages
from preprocessor import extract_text


def sync_recent_emails_for_review(limit=50):
    """
    Get recent emails and prepare them for manual review/labeling.
    This avoids the 400 error from complex label queries.
    """

    print("📧 Syncing Recent Emails for Review")
    print("=" * 50)

    # Initialize database
    init_db()

    try:
        # Get recent messages (this works - we tested it)
        print(f"🔍 Fetching {limit} recent messages...")
        message_ids = list_messages(max_results=limit)

        if not message_ids:
            print("❌ No recent messages found")
            return False

        print(f"📧 Found {len(message_ids)} recent messages")

        synced_count = 0

        for i, msg_info in enumerate(message_ids, 1):
            try:
                msg_id = msg_info["id"]
                print(f"📧 Processing {i}/{len(message_ids)}: {msg_id}")

                # Get message details
                message = get_message(msg_id)

                if message:
                    # Extract text content
                    text = extract_text(message)
                    snippet = message.get("snippet", "")[:100]

                    # Store in database
                    upsert_message(msg_id, snippet, text)
                    synced_count += 1

                    print(f"✅ Synced: {snippet[:50]}...")
                else:
                    print("⚠️  Skipped: Could not retrieve message")

                # Add delay to avoid rate limiting
                time.sleep(0.2)

            except Exception as e:
                print(f"❌ Error processing message {msg_id}: {e}")
                continue

        print("\n🎉 Sync completed!")
        print(f"📊 Successfully synced: {synced_count}/{len(message_ids)} messages")

        # Show what needs review
        print("📝 Messages synced and ready for review via API")

        print("\n💡 Next steps:")
        print("   1. Start API server: python -m uvicorn api:app --host localhost --port 8000")
        print("   2. Visit: http://localhost:8000/docs")
        print("   3. Use /api/review to label emails with real message IDs")
        print("   4. Label with your categories like: [Gmail]/Amazon, [Gmail]/Family, etc.")

        return True

    except Exception as e:
        print(f"❌ Sync failed: {e}")
        return False


def show_review_status():
    """Show current review status."""

    try:
        from data_store import fetch_for_training

        # Get already reviewed
        texts, labels = fetch_for_training()

        print("\n📊 Current Status:")
        print(f"   ✅ Already reviewed: {len(texts)} emails")
        print("   📝 Messages available for review")

        if texts:
            from collections import Counter

            label_counts = Counter(labels)
            print("   🏷️  Current labels:")
            for label, count in label_counts.most_common():
                print(f"      {label}: {count} emails")

        print("\n🎯 Goal: Review 10-20 emails per category")

    except Exception as e:
        print(f"❌ Could not get status: {e}")


if __name__ == "__main__":
    print("🚀 Gmail ML Client - Simple Email Sync")
    print("=" * 50)

    # Show current status
    show_review_status()

    print("\nOptions:")
    print("1. Sync recent emails for review")
    print("2. Show current status only")

    choice = input("\nEnter choice (1-2): ").strip()

    if choice == "1":
        # Sync recent emails
        success = sync_recent_emails_for_review(limit=30)

        if success:
            show_review_status()

    elif choice == "2":
        print("Current status shown above.")

    else:
        print("Invalid choice.")
