#!/usr/bin/env python3
"""
Manual email correction tool - Fix misclassified emails and retrain model
"""

import os
import sys

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data_store import Message, Session, init_db
from model import predict
from simple_train import simple_train


def manual_correction_tool():
    print("🛠️  Gmail ML Client - Manual Correction Tool")
    print("=" * 60)
    print("Find and fix misclassified emails to improve your model")
    print("")

    # Initialize database
    init_db()
    session = Session()

    try:
        while True:
            print("\n📋 CORRECTION MENU")
            print("=" * 30)
            print("1. Find misclassified emails")
            print("2. Search emails by text")
            print("3. Search emails by current label")
            print("4. Retrain model after corrections")
            print("5. Exit")

            choice = input("\nSelect option (1-5): ").strip()

            if choice == "1":
                find_misclassified_emails(session)
            elif choice == "2":
                search_by_text(session)
            elif choice == "3":
                search_by_label(session)
            elif choice == "4":
                retrain_after_corrections()
            elif choice == "5":
                break
            else:
                print("❌ Invalid choice. Please enter 1-5.")

    finally:
        session.close()


def find_misclassified_emails(session, limit=10):
    """Find emails that might be misclassified"""
    print(f"\n🔍 Finding potentially misclassified emails (showing {limit})...")

    # Get some random reviewed messages
    messages = (
        session.query(Message)
        .filter(Message.reviewed == True, Message.text.isnot(None))
        .limit(limit * 2)
        .all()
    )  # Get more than we need

    found_errors = 0

    for msg in messages:
        if found_errors >= limit:
            break

        try:
            # Get current prediction
            predictions, confidence, _ = predict([msg.text])
            predicted = predictions[0] if predictions else "UNKNOWN"
            conf = confidence[0] if confidence else 0.0

            # Check if prediction differs from stored label
            if predicted != msg.gold_label:
                found_errors += 1

                # Show the discrepancy
                text_snippet = msg.text[:100].replace("\n", " ").strip() + "..."

                print(f"\n📧 Email ID: {msg.id}")
                print(f'📝 Text: "{text_snippet}"')
                print(f"🏷️  Current Label: {msg.gold_label}")
                print(f"🤖 Model Predicts: {predicted} (confidence: {conf:.2f})")

                # Ask user what to do
                print("\nOptions:")
                print("1. Keep current label (model is wrong)")
                print("2. Change to predicted label (model is right)")
                print("3. Change to different label")
                print("4. Skip this email")

                user_choice = input("Choose option (1-4): ").strip()

                if user_choice == "1":
                    print(f"✅ Keeping current label: {msg.gold_label}")
                elif user_choice == "2":
                    msg.gold_label = predicted
                    msg.target_label = predicted
                    session.commit()
                    print(f"✅ Changed to: {predicted}")
                elif user_choice == "3":
                    new_label = input("Enter new label: ").strip()
                    if new_label:
                        msg.gold_label = new_label
                        msg.target_label = new_label
                        session.commit()
                        print(f"✅ Changed to: {new_label}")
                elif user_choice == "4":
                    print("⏭️  Skipped")
                else:
                    print("❌ Invalid choice, skipping")

        except Exception as e:
            print(f"⚠️  Error processing email: {e}")
            continue

    if found_errors == 0:
        print("🎉 No misclassifications found! Your model is working well.")


def search_by_text(session):
    """Search for emails containing specific text"""
    search_text = input("\nEnter text to search for: ").strip()
    if not search_text:
        return

    messages = (
        session.query(Message)
        .filter(Message.reviewed == True, Message.text.contains(search_text))
        .limit(5)
        .all()
    )

    if not messages:
        print("❌ No emails found with that text")
        return

    print(f"\n📧 Found {len(messages)} emails:")

    for i, msg in enumerate(messages, 1):
        text_snippet = msg.text[:100].replace("\n", " ").strip() + "..."
        print(f"\n{i}. ID: {msg.id}")
        print(f"   Label: {msg.gold_label}")
        print(f'   Text: "{text_snippet}"')

        # Ask if user wants to change this email's label
        change = input(f"   Change label for email {i}? (y/N): ").strip().lower()
        if change == "y":
            new_label = input("   Enter new label: ").strip()
            if new_label:
                msg.gold_label = new_label
                msg.target_label = new_label
                session.commit()
                print(f"   ✅ Changed to: {new_label}")


def search_by_label(session):
    """Search for emails with specific label"""
    # Show available labels
    labels = session.query(Message.gold_label).filter(Message.reviewed == True).distinct().all()

    unique_labels = sorted([label[0] for label in labels if label[0]])

    print(f"\n🏷️  Available labels ({len(unique_labels)}):")
    for i, label in enumerate(unique_labels[:20], 1):  # Show first 20
        print(f"  {i}. {label}")

    if len(unique_labels) > 20:
        print(f"  ... and {len(unique_labels) - 20} more")

    search_label = input("\nEnter label to search for: ").strip()
    if not search_label:
        return

    messages = (
        session.query(Message)
        .filter(Message.reviewed == True, Message.gold_label == search_label)
        .limit(5)
        .all()
    )

    if not messages:
        print("❌ No emails found with that label")
        return

    print(f"\n📧 Found {len(messages)} emails with label '{search_label}':")

    for i, msg in enumerate(messages, 1):
        text_snippet = msg.text[:100].replace("\n", " ").strip() + "..."
        print(f"\n{i}. ID: {msg.id}")
        print(f'   Text: "{text_snippet}"')

        # Ask if user wants to change this email's label
        change = input(f"   Change label for email {i}? (y/N): ").strip().lower()
        if change == "y":
            new_label = input("   Enter new label: ").strip()
            if new_label:
                msg.gold_label = new_label
                msg.target_label = new_label
                session.commit()
                print(f"   ✅ Changed to: {new_label}")


def retrain_after_corrections():
    """Retrain the model after making corrections"""
    print("\n🤖 Retraining model with corrections...")

    retrain = input("Are you sure you want to retrain? (y/N): ").strip().lower()
    if retrain == "y":
        try:
            success = simple_train()
            if success:
                print("✅ Model retrained successfully!")
                print("📈 Your corrections have been incorporated")
            else:
                print("❌ Retraining failed")
        except Exception as e:
            print(f"❌ Error retraining: {e}")
    else:
        print("❌ Retraining cancelled")


if __name__ == "__main__":
    try:
        manual_correction_tool()
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye! Your corrections have been saved.")
    except Exception as e:
        print(f"❌ Error: {e}")
