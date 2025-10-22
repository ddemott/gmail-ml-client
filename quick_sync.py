#!/usr/bin/env python3
"""
Quick email sync to get emails for manual labeling
"""

from gmail_client import list_messages, get_message
from data_store import init_db, upsert_message, fetch_for_training
from preprocessor import extract_text

def quick_sync():
    """Quick sync of recent emails."""
    
    print("📧 Quick Gmail Sync")
    print("=" * 30)
    
    init_db()
    
    # Get current status
    texts, labels = fetch_for_training()
    print(f"✅ Already reviewed: {len(texts)} emails")
    
    if texts:
        from collections import Counter
        label_counts = Counter(labels)
        print(f"🏷️  Current labels:")
        for label, count in label_counts.most_common():
            print(f"   {label}: {count}")
    
    print(f"\n📧 Syncing 20 recent emails...")
    
    try:
        # Get recent messages
        message_ids = list_messages(max_results=20)
        
        synced = 0
        for msg_info in message_ids:
            msg_id = msg_info['id']
            
            try:
                message = get_message(msg_id)
                if message:
                    text = extract_text(message)
                    snippet = message.get('snippet', '')[:100]
                    upsert_message(msg_id, snippet, text)
                    synced += 1
                    print(f"✅ {synced}: {snippet[:50]}...")
            except:
                continue
        
        print(f"\n🎉 Synced {synced} new emails!")
        print(f"\n💡 Next: Label these emails via the web interface:")
        print(f"   1. python -m uvicorn api:app --host localhost --port 8000")
        print(f"   2. Visit: http://localhost:8000/docs")
        print(f"   3. Use your labels like: [Gmail]/Amazon, [Gmail]/Family")
        print(f"   4. Then run: python simple_train.py")
        
    except Exception as e:
        print(f"❌ Sync failed: {e}")

if __name__ == "__main__":
    quick_sync()