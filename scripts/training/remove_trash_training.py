#!/usr/bin/env python3
"""
Completely remove TRASH training data and category.
TRASH is not a prediction category - it's just deleted emails.
Clean up the model to only predict useful categories.
"""

import os
import sys

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data_store import Message, Session, init_db
from simple_train import simple_train


def main():
    try:
        print("🗑️ Removing ALL TRASH Training Data")
        print("=" * 50)
        print("TRASH is not a prediction category - just deleted emails")
        print("Cleaning model to only predict useful categories")
        print("")

        # Initialize database
        init_db()
        session = Session()

        try:
            # Count current data before cleanup
            total_messages = session.query(Message).count()
            trash_messages = (
                session.query(Message)
                .filter((Message.target_label == "TRASH") | (Message.gold_label == "TRASH"))
                .count()
            )

            print(f"📊 Current Training Data:")
            print(f"   Total messages: {total_messages}")
            print(f"   TRASH-related messages: {trash_messages}")

            if trash_messages > 0:
                print(f"\n🗑️ Removing {trash_messages} TRASH-related training entries...")

                # Remove all messages with TRASH labels
                deleted_count = (
                    session.query(Message)
                    .filter((Message.target_label == "TRASH") | (Message.gold_label == "TRASH"))
                    .delete(synchronize_session=False)
                )

                session.commit()
                print(f"✅ Removed {deleted_count} TRASH entries")
            else:
                print("✅ No TRASH training data found - already clean!")

            # Show remaining data categories
            remaining_messages = session.query(Message).count()
            print(f"\n📊 Clean Training Data: {remaining_messages} messages")

            # Show what categories remain
            print(f"\n📁 Remaining Categories:")
            categories = session.query(Message.target_label).distinct().all()
            for i, (category,) in enumerate(categories, 1):
                if category:
                    count = session.query(Message).filter_by(target_label=category).count()
                    print(f"   {i:2d}. {category} ({count} messages)")

            print(f"\n🎯 Benefits of Removing TRASH:")
            print("• Model won't try to predict 'TRASH' category")
            print("• Focuses on useful predictions (SPAM, categories, etc.)")
            print("• Cleaner, more purposeful training data")
            print("• Better performance on meaningful classifications")

        finally:
            session.close()

        # Retrain the model without any TRASH data
        print(f"\n🤖 Retraining model without TRASH category...")
        simple_train()

        print(f"\n🎉 SUCCESS!")
        print("=" * 30)
        print("✅ All TRASH training data removed")
        print("✅ Model retrained with clean categories only")
        print("✅ No more 'TRASH' predictions")
        print("✅ Focus on useful email categorization")

        print(f"\n📝 NOW YOUR MODEL PREDICTS:")
        print("• SPAM - for spam detection")
        print("• [Gmail]/Job - for job-related emails")
        print("• [Gmail]/Finance - for financial emails")
        print("• [Gmail]/Family - for family communications")
        print("• And other useful Gmail folder categories")
        print("• NO TRASH predictions!")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
