#!/usr/bin/env python3
"""
Detailed misclassification analysis tool.
Shows exactly which emails were classified incorrectly and why.
"""

import os
import sys

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


from data_store import Message, Session, init_db
from model import predict


def analyze_misclassifications():
    print("🔍 Gmail ML Client - Misclassification Analysis")
    print("=" * 70)
    print("Analyzing exactly which emails were classified incorrectly")
    print("")

    # Initialize database
    init_db()
    session = Session()

    try:
        # Get all reviewed messages for analysis
        all_messages = (
            session.query(Message)
            .filter(
                Message.reviewed == True, Message.text.isnot(None), Message.gold_label.isnot(None)
            )
            .all()
        )

        print(f"📊 Analyzing {len(all_messages)} trained messages...")
        print("")

        correct_count = 0
        incorrect_count = 0
        misclassifications = []

        # Test each message
        for msg in all_messages:
            if not msg.text or len(msg.text.strip()) < 10:
                continue

            try:
                # Get prediction
                predictions, confidence, spam_scores = predict([msg.text])
                predicted_label = predictions[0] if predictions else "UNKNOWN"
                confidence_score = confidence[0] if confidence else 0.0

                # Check if correct
                is_correct = predicted_label == msg.gold_label

                if is_correct:
                    correct_count += 1
                else:
                    incorrect_count += 1
                    misclassifications.append(
                        {
                            "message_id": msg.id,
                            "text_snippet": msg.text[:150].replace("\n", " ").strip(),
                            "expected": msg.gold_label,
                            "predicted": predicted_label,
                            "confidence": confidence_score,
                            "spam_score": spam_scores[0] if spam_scores else 0.0,
                        }
                    )

            except Exception as e:
                print(f"Error analyzing message {msg.id}: {e}")
                continue

        total_tested = correct_count + incorrect_count
        accuracy = (correct_count / total_tested * 100) if total_tested > 0 else 0

        print("📈 OVERALL RESULTS")
        print("=" * 50)
        print(f"Total messages tested: {total_tested}")
        print(f"Correctly classified: {correct_count}")
        print(f"Incorrectly classified: {incorrect_count}")
        print(f"Overall accuracy: {accuracy:.1f}%")
        print("")

        if misclassifications:
            print("❌ MISCLASSIFIED EMAILS")
            print("=" * 50)
            print(f"Found {len(misclassifications)} misclassified emails:")
            print("")

            # Group misclassifications by expected category
            by_category = {}
            for misc in misclassifications:
                expected = misc["expected"]
                if expected not in by_category:
                    by_category[expected] = []
                by_category[expected].append(misc)

            # Show misclassifications by category
            for category, items in sorted(by_category.items()):
                print(f"📁 Expected Category: {category}")
                print(f"   Misclassified: {len(items)} emails")
                print("-" * 40)

                for i, item in enumerate(items[:3], 1):  # Show up to 3 examples
                    print(f"   {i}. Text: \"{item['text_snippet']}...\"")
                    print(f"      Expected: {item['expected']}")
                    print(f"      Predicted: {item['predicted']}")
                    print(f"      Confidence: {item['confidence']:.2f}")
                    print(f"      Spam Score: {item['spam_score']:.2f}")
                    print()

                if len(items) > 3:
                    print(
                        f"      ... and {len(items) - 3} more misclassified emails in this category"
                    )
                    print()

        # Analyze common confusion patterns
        print("🔄 CONFUSION PATTERNS")
        print("=" * 50)

        confusion_pairs = {}
        for misc in misclassifications:
            pair = (misc["expected"], misc["predicted"])
            if pair not in confusion_pairs:
                confusion_pairs[pair] = 0
            confusion_pairs[pair] += 1

        # Show top confusion pairs
        sorted_pairs = sorted(confusion_pairs.items(), key=lambda x: x[1], reverse=True)

        print("Most common misclassification patterns:")
        for i, ((expected, predicted), count) in enumerate(sorted_pairs[:10], 1):
            print(f"   {i}. {expected} → {predicted} ({count} times)")

        print("")

        # Low confidence predictions
        print("⚠️  LOW CONFIDENCE PREDICTIONS")
        print("=" * 50)

        low_confidence = [m for m in misclassifications if m["confidence"] < 0.7]
        if low_confidence:
            print(f"Found {len(low_confidence)} misclassifications with low confidence (<70%):")
            print("These might be genuinely ambiguous emails:")
            print("")

            for i, item in enumerate(low_confidence[:5], 1):
                print(f"   {i}. \"{item['text_snippet']}...\"")
                print(f"      Expected: {item['expected']}")
                print(
                    f"      Predicted: {item['predicted']} (confidence: {item['confidence']:.1%})"
                )
                print()
        else:
            print("All misclassifications had high confidence - model is decisive but wrong")

        # Recommendations
        print("💡 RECOMMENDATIONS")
        print("=" * 50)

        if accuracy >= 95:
            print("✅ Excellent accuracy! Model is production-ready.")
        elif accuracy >= 90:
            print("✅ Very good accuracy. Consider:")
        elif accuracy >= 85:
            print("👍 Good accuracy. To improve:")
        else:
            print("⚠️  Accuracy could be improved. Consider:")

        if accuracy < 95:
            # Find categories with most misclassifications
            category_errors = {}
            for misc in misclassifications:
                cat = misc["expected"]
                category_errors[cat] = category_errors.get(cat, 0) + 1

            top_error_categories = sorted(
                category_errors.items(), key=lambda x: x[1], reverse=True
            )[:3]

            print(
                f"• Add more training data for: {', '.join([cat for cat, _ in top_error_categories])}"
            )
            print("• Review and correct misclassified emails in these categories")
            print("• Consider merging similar categories that are often confused")

            if len(confusion_pairs) > 0:
                top_confusion = sorted_pairs[0]
                print(f"• Focus on distinguishing {top_confusion[0][0]} from {top_confusion[0][1]}")

        print("• Use the web interface to review and correct misclassifications")
        print("• Retrain after adding corrected examples")

    finally:
        session.close()


def show_category_performance():
    """Show performance breakdown by category"""
    print("\n📊 CATEGORY-BY-CATEGORY PERFORMANCE")
    print("=" * 70)

    session = Session()
    try:
        # Get all categories
        categories = (
            session.query(Message.gold_label)
            .filter(Message.reviewed == True, Message.gold_label.isnot(None))
            .distinct()
            .all()
        )

        category_stats = {}

        for (category,) in categories:
            messages = (
                session.query(Message)
                .filter(
                    Message.gold_label == category,
                    Message.reviewed == True,
                    Message.text.isnot(None),
                )
                .limit(20)
                .all()
            )  # Test up to 20 per category

            if not messages:
                continue

            correct = 0
            total = 0

            for msg in messages:
                if not msg.text or len(msg.text.strip()) < 10:
                    continue

                try:
                    predictions, _, _ = predict([msg.text])
                    predicted = predictions[0] if predictions else "UNKNOWN"

                    total += 1
                    if predicted == category:
                        correct += 1

                except Exception:
                    continue

            if total > 0:
                accuracy = (correct / total) * 100
                category_stats[category] = {
                    "correct": correct,
                    "total": total,
                    "accuracy": accuracy,
                }

        # Sort by accuracy
        sorted_stats = sorted(category_stats.items(), key=lambda x: x[1]["accuracy"], reverse=True)

        print("Category Performance (testing up to 20 emails per category):")
        print("-" * 70)

        for category, stats in sorted_stats:
            accuracy = stats["accuracy"]
            correct = stats["correct"]
            total = stats["total"]

            if accuracy == 100:
                icon = "🎯"
            elif accuracy >= 90:
                icon = "✅"
            elif accuracy >= 75:
                icon = "👍"
            else:
                icon = "⚠️"

            print(f"{icon} {category:<40} {correct:2d}/{total:2d} ({accuracy:5.1f}%)")

    finally:
        session.close()


if __name__ == "__main__":
    analyze_misclassifications()
    show_category_performance()
