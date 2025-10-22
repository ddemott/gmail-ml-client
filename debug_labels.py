#!/usr/bin/env python3
"""
Debug label contents and find messages
"""

from gmail_client import list_messages, get_labels

def debug_labels():
    """Debug what's in your labels."""
    
    print("🔍 Debugging Gmail Label Contents")
    print("=" * 50)
    
    # Get all labels
    all_labels = get_labels()
    user_labels = [l for l in all_labels if l.get('type') == 'user']
    
    # Test a few different label query methods
    test_labels = [
        "[Gmail]/Amazon",
        "[Gmail]/Family", 
        "[Gmail]/Bills",
        "Amazon",  # without [Gmail]/
        "Family",
        "Bills"
    ]
    
    print(f"🧪 Testing different query methods:")
    
    for label_name in test_labels:
        print(f"\n📧 Testing label: '{label_name}'")
        
        # Method 1: Direct label name
        try:
            messages1 = list_messages(query=f'label:"{label_name}"', max_results=5)
            print(f"   Method 1 (label:\"{label_name}\"): {len(messages1)} messages")
        except Exception as e:
            print(f"   Method 1 failed: {e}")
        
        # Method 2: Without quotes
        try:
            messages2 = list_messages(query=f'label:{label_name}', max_results=5)
            print(f"   Method 2 (label:{label_name}): {len(messages2)} messages")
        except Exception as e:
            print(f"   Method 2 failed: {e}")
        
        # Method 3: Find label ID and use that
        try:
            label_info = next((l for l in user_labels if l.get('name') == label_name), None)
            if label_info:
                label_id = label_info.get('id')
                messages3 = list_messages(query=f'label:{label_id}', max_results=5)
                print(f"   Method 3 (label:{label_id}): {len(messages3)} messages")
            else:
                print(f"   Method 3: Label not found in user labels")
        except Exception as e:
            print(f"   Method 3 failed: {e}")
    
    # Show recent messages without any label filter
    print(f"\n📨 Testing recent messages (no label filter):")
    try:
        recent_messages = list_messages(max_results=10)
        print(f"   Found {len(recent_messages)} recent messages")
        
        if recent_messages:
            print(f"   Sample message IDs: {recent_messages[:3]}")
    except Exception as e:
        print(f"   Failed to get recent messages: {e}")

if __name__ == "__main__":
    debug_labels()