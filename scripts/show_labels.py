#!/usr/bin/env python3
"""
Get Gmail labels and show training strategy
"""

from gmail_client import get_labels


def show_labels_and_strategy():
    """Show current labels and explain training strategy."""

    print("🎯 Gmail ML Client - Custom Label Training Strategy")
    print("=" * 60)

    try:
        labels = get_labels()
        user_labels = []
        system_labels = []

        for label in labels:
            label_name = label.get("name", "Unknown")
            if label.get("type") == "user":
                user_labels.append(label_name)
            else:
                system_labels.append(label_name)

        print("📋 Your Gmail Labels:")
        print(f"   🏷️  User Labels: {len(user_labels)}")
        print(f"   🔧 System Labels: {len(system_labels)}")

        if user_labels:
            print("\n🏷️  Your Custom Labels:")
            for i, label in enumerate(sorted(user_labels), 1):
                print(f"   {i:2d}. {label}")

        print("\n🚀 Training Strategy for Your Labels:")
        print("   1. 📧 Sync emails with existing labels")
        print("   2. 🏷️  Use emails already in your folders as training data")
        print("   3. 🤖 Train model to recognize patterns")
        print("   4. 📨 Auto-classify new incoming emails")

        print("\n💡 Recommendations:")
        print("   • Use 10-20 examples per label for good accuracy")
        print("   • Start with your most used labels")
        print("   • Review and correct predictions to improve")

        return user_labels

    except Exception as e:
        print(f"❌ Could not get labels: {e}")
        return []


if __name__ == "__main__":
    labels = show_labels_and_strategy()
