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
        print(f"🎯 Use these REAL message IDs in the API:")
        print(f"Go to: http://localhost:8000/docs")
        print(f"Use POST /api/review with:")
        print(f"{{")
        print(f'  "message_id": "{real_messages[0][0]}",')
        print(f'  "label": "[Gmail]/Amazon"')
        print(f"}}")
        print()
        print(f"📝 Available labels to use:")
        print(f"   • [Gmail]/Amazon")
        print(f"   • [Gmail]/Family")
        print(f"   • [Gmail]/Bills")
        print(f"   • [Gmail]/Computer Related")
        print(f"   • [Gmail]/Job")
        print(f"   • [Gmail]/Finance")
        print(f"   • [Gmail]/Health")
        print(f"   • [Gmail]/Auto Related")


if __name__ == "__main__":
    show_real_gmail_messages()
