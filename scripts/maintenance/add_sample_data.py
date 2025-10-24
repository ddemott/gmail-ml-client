#!/usr/bin/env python3
"""
Add sample training data for testing
"""

from datetime import datetime

from src.gmail_ml_client.data_store import init_db, mark_review, upsert_message


def add_sample_training_data():
    """Add sample emails for each category to test training."""

    init_db()

    # Sample emails for each category
    sample_emails = [
        # Work emails
        (
            "work_1",
            "Meeting Tomorrow",
            "john@company.com",
            "Team meeting scheduled for 2pm tomorrow in conference room A",
            ["Work"],
        ),
        (
            "work_2",
            "Project Update",
            "manager@company.com",
            "Please provide status update on the Q4 project deliverables",
            ["Work"],
        ),
        (
            "work_3",
            "Code Review",
            "dev@company.com",
            "Your pull request needs review before we can merge to main branch",
            ["Work"],
        ),
        # Personal emails
        (
            "personal_1",
            "Weekend Plans",
            "friend@email.com",
            "Hey! Want to grab dinner this weekend? I found a great new restaurant",
            ["Personal"],
        ),
        (
            "personal_2",
            "Family BBQ",
            "mom@email.com",
            "Don't forget about the family BBQ on Sunday at 3pm. Bring the potato salad!",
            ["Personal"],
        ),
        (
            "personal_3",
            "Birthday Party",
            "sister@email.com",
            "Sarah's birthday party is next Saturday. Can you help with decorations?",
            ["Personal"],
        ),
        # SPAM emails
        (
            "spam_1",
            "URGENT: You've Won $1,000,000!",
            "noreply@scam.com",
            "Congratulations! You've won our lottery! Send your bank details immediately!",
            ["SPAM"],
        ),
        (
            "spam_2",
            "Hot Singles in Your Area",
            "fake@spam.com",
            "Meet local singles tonight! Click here for instant access! Limited time offer!",
            ["SPAM"],
        ),
        (
            "spam_3",
            "Miracle Weight Loss",
            "diet@fake.com",
            "Lose 30 pounds in 30 days with this ONE WEIRD TRICK doctors hate!",
            ["SPAM"],
        ),
        # Newsletter emails
        (
            "news_1",
            "Tech Weekly Newsletter",
            "newsletter@techsite.com",
            "This week in technology: AI breakthroughs, new smartphone releases, and coding tutorials",
            ["Newsletter"],
        ),
        (
            "news_2",
            "Monthly Product Updates",
            "updates@software.com",
            "New features this month: dark mode, improved search, and mobile app updates",
            ["Newsletter"],
        ),
        (
            "news_3",
            "Industry News Digest",
            "news@industry.com",
            "Top stories this week: market trends, company acquisitions, and upcoming conferences",
            ["Newsletter"],
        ),
    ]

    print("📧 Adding sample training data...")

    for msg_id, subject, sender, body, labels in sample_emails:
        # Add message to database (using correct parameters)
        full_text = f"From: {sender}\nSubject: {subject}\n\n{body}"
        upsert_message(msg_id, body[:100], full_text)

        # Mark as reviewed with the primary label
        mark_review(msg_id, labels[0])
        print(f"✅ Added: {subject} -> {labels[0]}")

    print(f"\n🎉 Added {len(sample_emails)} sample emails!")
    print("📊 Label distribution:")
    label_counts = {}
    for _, _, _, _, labels in sample_emails:
        label = labels[0]
        label_counts[label] = label_counts.get(label, 0) + 1

    for label, count in label_counts.items():
        print(f"   {label}: {count} emails")

    print(f"\n🚀 Now you can retrain with: python simple_train.py")


if __name__ == "__main__":
    add_sample_training_data()
