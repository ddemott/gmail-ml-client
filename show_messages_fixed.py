#!/usr/bin/env python3
"""
Show available message IDs - fixed version
"""

import sqlite3
from data_store import init_db

def show_available_messages():
    """Show messages available for labeling."""
    
    print("📧 Available Messages for Labeling")
    print("=" * 50)
    
    init_db()
    
    # Connect to database
    conn = sqlite3.connect('state.db')
    cursor = conn.cursor()
    
    # First, let's see what tables exist
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print(f"📋 Database tables: {[table[0] for table in tables]}")
    
    # Check the messages table structure
    cursor.execute("PRAGMA table_info(messages);")
    columns = cursor.fetchall()
    print(f"📊 Messages table columns: {[col[1] for col in columns]}")
    
    # Get all messages
    cursor.execute("SELECT * FROM messages LIMIT 10")
    messages = cursor.fetchall()
    
    print(f"\n📧 Found {len(messages)} messages:")
    print()
    
    for i, message in enumerate(messages, 1):
        print(f"{i:2d}. Message Data: {message}")
        print()
    
    # Get message IDs and snippets if available
    try:
        cursor.execute("SELECT msg_id, snippet FROM messages LIMIT 5")
        simple_messages = cursor.fetchall()
        
        print(f"📝 Ready to use message IDs:")
        for msg_id, snippet in simple_messages:
            print(f"   ID: {msg_id}")
            print(f"   📧 {snippet[:70]}...")
            print()
            
        if simple_messages:
            print(f"💡 Copy one of these IDs to use in /api/review:")
            print(f'{{')
            print(f'  "message_id": "{simple_messages[0][0]}",')
            print(f'  "label": "[Gmail]/Amazon"')
            print(f'}}')
    except Exception as e:
        print(f"Error getting simple messages: {e}")
    
    conn.close()

if __name__ == "__main__":
    show_available_messages()