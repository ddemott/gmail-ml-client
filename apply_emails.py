#!/usr/bin/env python3
"""
Safe Email Application Script
Applies ML classifications to move emails in Gmail with dry-run option
"""

import os
import sys
from typing import Any, Dict, List

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from cfg import THRESHOLDS
from gmail_client import ensure_label, modify_labels, trash_message
from sorter import propose


def apply_email_actions(dry_run: bool = True, limit: int = 100) -> None:
    """
    Apply email classification actions to Gmail.

    Args:
        dry_run: If True, only show what would be done
        limit: Maximum number of emails to process
    """
    print("📧 Email Application Tool")
    print("=" * 50)
    print(f"Mode: {'DRY RUN (safe)' if dry_run else 'LIVE (will move emails)'}")
    print(f"Limit: {limit} emails")
    print()

    # Get proposed actions
    actions = propose(limit=limit)

    if not actions:
        print("✅ No emails to process!")
        return

    print(f"📊 Processing {len(actions)} emails...")

    # Count actions
    spam_actions = [a for a in actions if a['action'] == 'trash']
    route_actions = [a for a in actions if a['action'] == 'route']
    review_actions = [a for a in actions if a['action'] == 'review']

    print(f"🚫 Would move to spam: {len(spam_actions)} emails")
    print(f"📧 Would auto-route: {len(route_actions)} emails")
    print(f"👀 Would skip (needs review): {len(review_actions)} emails")
    print()

    if dry_run:
        print("🔍 DRY RUN - Showing what would happen:")
        print("-" * 50)

        # Show spam actions
        if spam_actions:
            print("🚫 SPAM (move to trash):")
            for i, action in enumerate(spam_actions[:5], 1):
                snippet = action['snippet'][:60] + "..." if len(action['snippet']) > 60 else action['snippet']
                print(f"  {i}. {snippet} (spam: {action['spam_score']:.2f})")
            if len(spam_actions) > 5:
                print(f"  ... and {len(spam_actions)-5} more")
            print()

        # Show route actions
        if route_actions:
            print("📧 ROUTE (apply labels):")
            for i, action in enumerate(route_actions[:5], 1):
                snippet = action['snippet'][:60] + "..." if len(action['snippet']) > 60 else action['snippet']
                print(f"  {i}. {snippet} -> {action['target']} (conf: {action['conf']:.2f})")
            if len(route_actions) > 5:
                print(f"  ... and {len(route_actions)-5} more")
            print()

        # Show review actions
        if review_actions:
            print("👀 REVIEW (manual check needed):")
            for i, action in enumerate(review_actions[:3], 1):
                snippet = action['snippet'][:60] + "..." if len(action['snippet']) > 60 else action['snippet']
                print(f"  {i}. {snippet} -> {action['target']} (conf: {action['conf']:.2f})")
            if len(review_actions) > 3:
                print(f"  ... and {len(review_actions)-3} more")
            print()

        print("💡 To actually move emails, run:")
        print("   python apply_emails.py --no-dry-run")

    else:
        print("⚠️  LIVE MODE - Actually moving emails in Gmail!")
        print("This will modify your Gmail organization.")
        confirm = input("Are you sure? Type 'yes' to continue: ")
        if confirm.lower() != 'yes':
            print("❌ Cancelled.")
            return

        applied = 0
        errors = 0

        # Apply spam actions
        for action in spam_actions:
            try:
                if not dry_run:
                    trash_message(action['id'])
                applied += 1
                if applied % 10 == 0:
                    print(f"  Moved {applied} emails to spam...")
            except Exception as e:
                print(f"  ❌ Error moving spam {action['id']}: {e}")
                errors += 1

        # Apply route actions
        for action in route_actions:
            try:
                if action['target']:
                    lid = ensure_label(action['target'])
                    modify_labels(action['id'], add=[lid], remove=['INBOX'])
                applied += 1
                if applied % 10 == 0:
                    print(f"  Applied {applied} email moves...")
            except Exception as e:
                print(f"  ❌ Error routing {action['id']}: {e}")
                errors += 1

        print("\n🎉 APPLICATION COMPLETE!")
        print(f"✅ Successfully applied: {applied} actions")
        if errors > 0:
            print(f"❌ Errors: {errors}")
        print("\n📧 Check your Gmail to see the changes!")
        print("   - Spam emails moved to Trash")
        print("   - Categorized emails moved to appropriate labels")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Apply email classifications to Gmail")
    parser.add_argument("--no-dry-run", action="store_true",
                       help="Actually move emails (default is dry-run)")
    parser.add_argument("--limit", type=int, default=100,
                       help="Maximum emails to process (default: 100)")

    args = parser.parse_args()
    apply_email_actions(dry_run=not args.no_dry_run, limit=args.limit)
