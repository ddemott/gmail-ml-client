#!/usr/bin/env python3
"""
Clean up training data by removing TRASH emails and keeping only genuine SPAM.
TRASH = emails user deleted (may not be spam)
SPAM = emails specifically identified as spam
"""

import sys
import os

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data_store import init_db, Message, Session
from simple_train import simple_train

def main():
    try:
        print("🧹 Cleaning Training Data - Removing TRASH, Keeping Only SPAM")
        print("=" * 70)
        print("TRASH folder = emails you deleted (not necessarily spam)")
        print("SPAM folder = emails specifically identified as spam")
        print("")
        
        # Initialize database
        init_db()
        session = Session()
        
        try:
            # Count current data
            total_messages = session.query(Message).count()
            spam_messages = session.query(Message).filter_by(gold_label='SPAM').count()
            trash_messages = session.query(Message).filter(
                Message.gold_label == 'SPAM',
                Message.target_label == 'SPAM'
            ).count()
            
            print(f"📊 Current Training Data:")
            print(f"   Total messages: {total_messages}")
            print(f"   SPAM labeled messages: {spam_messages}")
            
            # Find messages that came from TRASH folder
            # We need to identify these by looking at the text patterns or other indicators
            # Since we can't easily distinguish TRASH vs SPAM messages after they're in DB,
            # let's remove ALL current SPAM entries and re-add only from SPAM folder
            
            print(f"\n🗑️  Removing all current SPAM training data...")
            deleted_count = session.query(Message).filter_by(gold_label='SPAM').delete()
            session.commit()
            
            print(f"✅ Removed {deleted_count} SPAM entries from training data")
            
            # Show remaining data
            remaining_messages = session.query(Message).count()
            print(f"📊 Remaining training data: {remaining_messages} messages")
            
            print(f"\n🎯 Now we'll retrain with ONLY genuine SPAM folder data...")
            
        finally:
            session.close()
        
        # Now retrain with only SPAM folder data
        print(f"\n🔄 Retraining with SPAM folder only...")
        retrain_spam_only()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

def retrain_spam_only():
    """Retrain with only genuine SPAM folder data"""
    try:
        from gmail_client import list_messages, get_message, get_labels
        from preprocessor import extract_text
        
        print("🎯 Processing ONLY genuine SPAM folder...")
        
        # Get labels
        labels = get_labels()
        spam_label = None
        
        for label in labels:
            if label['name'] == 'SPAM':  # Only genuine SPAM folder
                spam_label = label
                break
        
        if not spam_label:
            print("❌ SPAM folder not found!")
            return
        
        print(f"📁 Processing genuine SPAM folder only...")
        
        # Get messages from SPAM folder only
        messages = list_messages(label_ids=[spam_label['id']], max_results=500)
        
        if not messages:
            print("❌ No messages found in SPAM folder!")
            return
        
        print(f"📧 Found {len(messages)} genuine SPAM messages")
        
        session = Session()
        processed_count = 0
        
        try:
            for i, msg in enumerate(messages):
                try:
                    # Get message details
                    full_msg = get_message(msg['id'])
                    text = extract_text(full_msg)
                    
                    if not text or len(text.strip()) < 10:
                        continue
                    
                    # Check if message already exists
                    existing = session.query(Message).filter_by(id=msg['id']).first()
                    
                    if existing:
                        # Update existing message to mark as spam
                        existing.target_label = 'SPAM'
                        existing.reviewed = True
                        existing.gold_label = 'SPAM'
                    else:
                        # Create new message entry
                        message_obj = Message(
                            id=msg['id'],
                            snippet=full_msg.get('snippet', ''),
                            text=text,
                            target_label='SPAM',
                            reviewed=True,
                            gold_label='SPAM'
                        )
                        session.add(message_obj)
                    
                    processed_count += 1
                    
                    # Show progress every 25 messages
                    if processed_count % 25 == 0:
                        print(f"   ✅ Processed {processed_count}/{len(messages)} genuine SPAM messages")
                        session.commit()
                    
                    # Small delay for API
                    if i % 10 == 0:
                        import time
                        time.sleep(0.1)
                        
                except Exception as e:
                    print(f"   ⚠️  Error processing message {i+1}: {e}")
                    continue
            
            session.commit()
            print(f"🎉 Processed {processed_count} genuine SPAM messages")
            
        finally:
            session.close()
        
        if processed_count > 0:
            print(f"\n🤖 Retraining model with clean SPAM data only...")
            simple_train()
            
            print(f"\n🎉 SUCCESS!")
            print("=" * 50)
            print("✅ Model retrained with ONLY genuine SPAM data")
            print("✅ No more TRASH data contaminating spam detection")
            print("✅ Model should now be more accurate at identifying real spam")
            
            print(f"\n📝 WHAT CHANGED:")
            print("• Removed all TRASH folder emails from training")
            print("• Kept only emails from Gmail's SPAM folder")
            print("• Model now learns from confirmed spam patterns only")
            print("• Should reduce false positives on legitimate deleted emails")
        
    except Exception as e:
        print(f"❌ Error retraining: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()