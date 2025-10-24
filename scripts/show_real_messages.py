#!/usr/bin/env python3
"""
Show real Gmail message IDs that were just synced
"""

import sqlite3

from data_store import init_db


def show_real_gmail_messages():
    """Show the real Gmail messages that were just synced."""

    print("📧 Your Real Gmail Messages (Just Synced)")
    print("=" * 60)

    init_db()

    # Connect to database
    conn = sqlite3.connect("state.db")
    cursor = conn.cursor()

    # Get the most recent 10 messages (from the sync)
    cursor.execute(
        """
        SELECT id, snippet
        FROM messages
        WHERE id LIKE '19a%'
        ORDER BY created_at DESC
        LIMIT 10
    """
    )

    real_messages = cursor.fetchall()

    print(f"📊 Found {len(real_messages)} real Gmail messages:")
    print()

    for i, (msg_id, snippet) in enumerate(real_messages, 1):
        print(f"{i:2d}. ID: {msg_id}")
        print(f"    📧 {snippet[:80]}...")
        print()

    conn.close()

    if real_messages:
        print("🎯 Use these REAL message IDs in the API:")
        print("Go to: http://localhost:8000/docs")
        print("Use POST /api/review with:")
        print("{")
        print(f'  "message_id": "{real_messages[0][0]}",')
        print('  "label": "[Gmail]/Amazon"')
        print("}")
        print()
        print("📝 Available labels to use:")
        print("   • [Gmail]/Amazon")
        print("   • [Gmail]/Family")
        print("   • [Gmail]/Bills")
        print("   • [Gmail]/Computer Related")
        print("   • [Gmail]/Job")
        print("   • [Gmail]/Finance")
        print("   • [Gmail]/Health")
        print("   • [Gmail]/Auto Related")


if __name__ == "__main__":
    show_real_gmail_messages()
