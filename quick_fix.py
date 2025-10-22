#!/usr/bin/env python3
"""
Quick correction script - Fix specific emails by ID
"""

import sys
import os

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data_store import init_db, Message, Session

def quick_fix():
    """Quick fix for specific email IDs"""
    print("⚡ Quick Email Fix Tool")
    print("=" * 30)
    
    init_db()
    session = Session()
    
    try:
        # Example of how to fix specific emails
        email_id = input("Enter email ID to fix (or 'search' to find): ").strip()
        
        if email_id.lower() == 'search':
            # Search by text snippet
            search_text = input("Enter text to search for: ").strip()
            
            messages = session.query(Message).filter(
                Message.text.contains(search_text)
            ).limit(5).all()
            
            if messages:
                print(f"\nFound {len(messages)} matching emails:")
                for i, msg in enumerate(messages, 1):
                    snippet = msg.text[:80].replace('\n', ' ') + "..."
                    print(f"{i}. ID: {msg.id} | Label: {msg.gold_label}")
                    print(f"   Text: {snippet}")
                
                choice = input(f"\nSelect email to fix (1-{len(messages)}): ").strip()
                try:
                    idx = int(choice) - 1
                    if 0 <= idx < len(messages):
                        selected_msg = messages[idx]
                        new_label = input(f"Enter new label for this email: ").strip()
                        
                        if new_label:
                            selected_msg.gold_label = new_label
                            selected_msg.target_label = new_label
                            session.commit()
                            print(f"✅ Updated email {selected_msg.id} to label: {new_label}")
                except ValueError:
                    print("❌ Invalid selection")
        else:
            # Direct ID fix
            message = session.query(Message).filter_by(id=email_id).first()
            
            if message:
                snippet = message.text[:100].replace('\n', ' ') + "..."
                print(f"\nFound email:")
                print(f"ID: {message.id}")
                print(f"Current label: {message.gold_label}")
                print(f"Text: {snippet}")
                
                new_label = input(f"\nEnter new label: ").strip()
                
                if new_label:
                    message.gold_label = new_label
                    message.target_label = new_label
                    session.commit()
                    print(f"✅ Updated to label: {new_label}")
                else:
                    print("❌ No changes made")
            else:
                print(f"❌ Email with ID '{email_id}' not found")
    
    finally:
        session.close()

if __name__ == "__main__":
    quick_fix()