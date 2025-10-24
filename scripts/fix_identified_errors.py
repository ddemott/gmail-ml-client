#!/usr/bin/env python3
"""
Quick fix for identified classification errors
"""

import os
import sys

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data_store import Message, Session, init_db


def fix_identified_errors():
    print("🔧 Quick Fix for Identified Errors")
    print("=" * 50)

    init_db()
    session = Session()

    try:
        # Known problematic email IDs from the analysis
        fixes = [
            {
                "id": "19a0741d11eb4648",
                "current": "SPAM",
                "suggested": "[Gmail]/Job",
                "reason": "Built In welcome email - legitimate job site",
            },
            {
                "id": "19a02d3898df7c42",
                "current": "SPAM",
                "suggested": "[Gmail]/Job",
                "reason": "Energy jobline - legitimate job posting",
            },
            {
                "id": "19a06fbe3576d54a",
                "current": "CATEGORY_UPDATES",
                "suggested": "[Gmail]/Job",
                "reason": "IT developer opportunity - should be job category",
            },
            {
                "id": "19a02f65863c3458",
                "current": "[Gmail]/X (Twitter)",
                "suggested": "[Gmail]/Finance",
                "reason": "Tax filing notice - financial content",
            },
            {
                "id": "19a05eb0103d826b",
                "current": "CATEGORY_UPDATES",
                "suggested": "[Gmail]/Finance",
                "reason": "Trading/investment content - financial category",
            },
        ]

        print(f"📧 Fixing {len(fixes)} identified classification errors...\n")

        fixed_count = 0

        for i, fix in enumerate(fixes, 1):
            email = session.query(Message).filter_by(id=fix["id"]).first()

            if email:
                print(f"{i}. Email ID: {fix['id']}")
                print(f"   Current: {fix['current']}")
                print(f"   Suggested: {fix['suggested']}")
                print(f"   Reason: {fix['reason']}")

                # Show email snippet for confirmation
                if email.text:
                    snippet = email.text[:80].replace("\n", " ").strip() + "..."
                    print(f'   Text: "{snippet}"')

                # Ask for confirmation
                confirm = input("   Apply this fix? (y/N): ").strip().lower()

                if confirm == "y":
                    email.target_label = fix["suggested"]
                    email.reviewed = True  # Mark as manually reviewed
                    session.commit()
                    fixed_count += 1
                    print(f"   ✅ Fixed: Changed to {fix['suggested']}")
                else:
                    print("   ⏭️  Skipped")
                print()
            else:
                print(f"{i}. Email ID {fix['id']} not found")
                print()

        print(f"🎉 FIXES APPLIED: {fixed_count}/{len(fixes)}")

        if fixed_count > 0:
            print("\n🤖 Consider retraining the model with these corrections:")
            print("python simple_train.py")
            print("\nThese fixes will help improve future classifications!")

    finally:
        session.close()


if __name__ == "__main__":
    fix_identified_errors()
