#!/usr/bin/env python3
"""
Sync Gmail emails directly
"""

from cfg import SYNC_PAGE_SIZE
from data_store import init_db, upsert_message
from gmail_client import get_message, list_messages
from logger import logger
from preprocessor import extract_text


def sync_gmail_emails(limit=50):
    """Sync emails from Gmail to local database."""

    print("📧 Starting Gmail sync...")

    try:
        # Initialize database
        init_db()

        # Get list of recent messages
        print("🔍 Fetching message list from Gmail...")
        message_ids = list_messages(max_results=limit)

        if not message_ids:
            print("❌ No messages found or Gmail access failed")
            return False

        print(f"📋 Found {len(message_ids)} messages to sync")

        synced_count = 0

        for i, msg_id in enumerate(message_ids, 1):
            try:
                print(f"📧 Syncing message {i}/{len(message_ids)}: {msg_id}")

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
                    print(f"⚠️  Skipped message {msg_id}: Could not retrieve")

            except Exception as e:
                print(f"❌ Error syncing message {msg_id}: {e}")
                continue

        print(f"\n🎉 Gmail sync completed!")
        print(f"📊 Successfully synced: {synced_count}/{len(message_ids)} messages")
        print(f"📝 Messages are now available for review and labeling")

        return True

    except Exception as e:
        logger.error(f"Gmail sync failed: {e}")
        print(f"❌ Gmail sync failed: {e}")
        return False


def show_sync_stats():
    """Show statistics about synced messages."""
    try:
        from data_store import fetch_for_training, get_messages_to_review

        # Get pending reviews
        pending = get_messages_to_review(limit=100)

        # Get already reviewed
        texts, labels = fetch_for_training()

        print(f"\n📊 Current Status:")
        print(f"   📝 Messages needing review: {len(pending)}")
        print(f"   ✅ Already reviewed: {len(texts)}")

        if texts:
            from collections import Counter

            label_counts = Counter(labels)
            print(f"   🏷️  Label distribution:")
            for label, count in label_counts.items():
                print(f"      {label}: {count}")

    except Exception as e:
        print(f"❌ Could not get sync stats: {e}")


if __name__ == "__main__":
    print("🚀 Gmail ML Client - Email Sync")
    print("=" * 50)

    # Sync emails
    success = sync_gmail_emails(limit=50)

    if success:
        # Show stats
        show_sync_stats()

        print(f"\n🎯 Next Steps:")
        print(f"   1. Review emails: Use API at http://localhost:8000/docs")
        print(f"   2. Label emails as: Work, Personal, SPAM, Newsletter")
        print(f"   3. Retrain model: python simple_train.py")
    else:
        print(f"\n❌ Sync failed. Check your Gmail authentication.")
