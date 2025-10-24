#!/usr/bin/env python3
"""
Show available message IDs for labeling
"""

import sqlite3

from data_store import init_db


def show_available_messages():
    """Show messages available for labeling."""

    print("📧 Available Messages for Labeling")
    print("=" * 50)

    init_db()

    # Connect to database
    conn = sqlite3.connect("state.db")
    cursor = conn.cursor()

    # Get messages that haven't been reviewed yet
    cursor.execute(
        """
        SELECT msg_id, snippet
        FROM messages
        WHERE msg_id NOT IN (SELECT DISTINCT msg_id FROM reviews)
        LIMIT 10
    """
    )

    unreviewed = cursor.fetchall()

    print(f"📝 Unreviewed messages: {len(unreviewed)}")
    print()

    for i, (msg_id, snippet) in enumerate(unreviewed, 1):
        print(f"{i:2d}. ID: {msg_id}")
        print(f"    📧 {snippet[:70]}...")
        print()

    # Show already reviewed
    cursor.execute(
        """
        SELECT r.msg_id, r.label, m.snippet
        FROM reviews r
        JOIN messages m ON r.msg_id = m.msg_id
        LIMIT 5
    """
    )

    reviewed = cursor.fetchall()

    print(f"✅ Already reviewed: {len(reviewed)} (showing first 5)")
    for msg_id, label, snippet in reviewed:
        print(f"   {msg_id} → {label}: {snippet[:50]}...")

    conn.close()

    if unreviewed:
        print(f"\n💡 Copy one of the message IDs above to use in /api/review")
        print(f"Example for first message:")
        print(f"{{")
        print(f'  "message_id": "{unreviewed[0][0]}",')
        print(f'  "label": "[Gmail]/Amazon"')
        print(f"}}")


if __name__ == "__main__":
    show_available_messages()
