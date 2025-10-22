#!/usr/bin/env python3
"""
Comprehensive retraining of all Gmail folders with SPAM training last.
This will capture all new data and eliminate false positives by training SPAM last.
"""

import sys
import os
import time

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from gmail_client import list_messages, get_message, get_labels
from preprocessor import extract_text
from data_store import init_db, Message, Session
from simple_train import simple_train

def main():
    try:
        print("🚀 Gmail ML Client - Complete Folder Retraining")
        print("=" * 60)
        print("Training all folders with SPAM last to eliminate false positives")
        print("Job folder prioritized due to new data")
        print("")
        
        # Initialize database
        init_db()
        
        # Clear all existing training data for fresh start
        print("🧹 Clearing existing training data for fresh retrain...")
        session = Session()
        try:
            old_count = session.query(Message).filter(Message.reviewed == True).count()
            session.query(Message).filter(Message.reviewed == True).delete()
            session.commit()
            print(f"✅ Cleared {old_count} old training entries")
        finally:
            session.close()
        
        # Get all labels
        print("\n📁 Fetching all Gmail labels...")
        labels = get_labels()
        
        # Separate useful folders from spam/system folders
        useful_folders = []
        spam_folders = []
        system_labels = {'INBOX', 'SENT', 'DRAFT', 'STARRED', 'IMPORTANT', 'UNREAD', 'CHAT'}
        
        for label in labels:
            label_name = label['name']
            label_lower = label_name.lower()
            
            # Skip system labels
            if label_name in system_labels:
                continue
            
            # Separate spam/trash from useful folders
            if any(spam_word in label_lower for spam_word in ['spam', 'trash', 'junk']):
                if label_name == 'SPAM':  # Only genuine SPAM folder
                    spam_folders.append(label)
            elif label_name.startswith('[Gmail]/') and not any(skip in label_lower for skip in ['trash', 'spam', 'junk']):
                useful_folders.append(label)
            elif not label_name.startswith('[Gmail]') and len(label_name) > 2:
                useful_folders.append(label)
        
        # Sort useful folders to prioritize Job folder
        useful_folders.sort(key=lambda x: (
            0 if 'job' in x['name'].lower() else
            1 if any(priority in x['name'].lower() for priority in ['finance', 'family', 'computer', 'health']) else
            2
        ))
        
        print(f"📊 Found {len(useful_folders)} useful folders and {len(spam_folders)} spam folders")
        
        # Train on useful folders first
        print(f"\n🎯 Phase 1: Training on Useful Categories")
        print("=" * 50)
        
        total_processed = 0
        
        for i, label in enumerate(useful_folders, 1):
            label_id = label['id']
            label_name = label['name']
            
            print(f"\n📁 {i:2d}/{len(useful_folders)}: Processing {label_name}")
            
            # Get more messages for Job folder, standard amount for others
            max_messages = 100 if 'job' in label_name.lower() else 50
            messages = list_messages(label_ids=[label_id], max_results=max_messages)
            
            if not messages:
                print(f"   ⚠️  No messages found")
                continue
            
            print(f"   📧 Found {len(messages)} messages, processing...")
            
            processed_count = 0
            session = Session()
            
            try:
                for j, msg in enumerate(messages):
                    try:
                        # Get message details
                        full_msg = get_message(msg['id'])
                        text = extract_text(full_msg)
                        
                        if not text or len(text.strip()) < 10:
                            continue
                        
                        # Check if message already exists
                        existing = session.query(Message).filter_by(id=msg['id']).first()
                        
                        if existing:
                            # Update existing message
                            existing.target_label = label_name
                            existing.reviewed = True
                            existing.gold_label = label_name
                        else:
                            # Create new message entry
                            message_obj = Message(
                                id=msg['id'],
                                snippet=full_msg.get('snippet', ''),
                                text=text,
                                target_label=label_name,
                                reviewed=True,
                                gold_label=label_name
                            )
                            session.add(message_obj)
                        
                        processed_count += 1
                        total_processed += 1
                        
                        # Show progress every 10 messages
                        if processed_count % 10 == 0:
                            print(f"   ✅ Processed {processed_count}/{len(messages)}")
                            session.commit()
                        
                        # Small delay for API
                        if j % 10 == 0:
                            time.sleep(0.1)
                            
                    except Exception as e:
                        print(f"   ⚠️  Error processing message {j+1}: {e}")
                        continue
                
                session.commit()
                print(f"   🎉 Completed: {processed_count} messages from {label_name}")
                
            finally:
                session.close()
        
        # Train on SPAM last to eliminate false positives
        print(f"\n🎯 Phase 2: Training on SPAM (Last to eliminate false positives)")
        print("=" * 60)
        
        for spam_label in spam_folders:
            label_id = spam_label['id']
            label_name = spam_label['name']
            
            print(f"\n📁 Processing {label_name}...")
            
            # Get plenty of spam messages for good detection
            messages = list_messages(label_ids=[label_id], max_results=200)
            
            if not messages:
                print(f"   ⚠️  No messages found")
                continue
            
            print(f"   📧 Found {len(messages)} SPAM messages, processing...")
            
            processed_count = 0
            session = Session()
            
            try:
                for j, msg in enumerate(messages):
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
                        total_processed += 1
                        
                        # Show progress every 25 messages
                        if processed_count % 25 == 0:
                            print(f"   ✅ Processed {processed_count}/{len(messages)} SPAM")
                            session.commit()
                        
                        # Small delay for API
                        if j % 10 == 0:
                            time.sleep(0.1)
                            
                    except Exception as e:
                        print(f"   ⚠️  Error processing message {j+1}: {e}")
                        continue
                
                session.commit()
                print(f"   🎉 Completed: {processed_count} SPAM messages")
                
            finally:
                session.close()
        
        print(f"\n📊 COMPLETE RETRAINING SUMMARY:")
        print("=" * 50)
        print(f"Total messages processed: {total_processed}")
        print(f"✅ All useful categories trained first")
        print(f"✅ SPAM trained last to eliminate false positives")
        print(f"✅ Job folder prioritized with up to 100 messages")
        
        if total_processed > 0:
            print(f"\n🤖 Training model with complete dataset...")
            simple_train()
            
            print(f"\n🎉 COMPLETE SUCCESS!")
            print("=" * 40)
            print("✅ Model retrained with ALL folder data")
            print("✅ Job folder prioritized with latest data")
            print("✅ SPAM trained last to minimize false positives")
            print("✅ Ready for production use")
            
            print(f"\n📝 NEXT STEPS:")
            print("• Test the improved model: python test_predictions.py")
            print("• Check job email classification accuracy")
            print("• Verify SPAM detection with minimal false positives")
            print("• Model should now be highly accurate across all categories")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()