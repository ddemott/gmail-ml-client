#!/usr/bin/env python3
"""
Check Gmail folders/labels and show email counts to help with organization.
This script will show you all your labels and how many emails are in each.
"""

import sys
import os

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from gmail_client import get_labels, list_messages

def main():
    try:
        print("🔍 Checking Gmail folders and email counts...")
        print("=" * 60)
        
        # Get all labels
        print("📁 Fetching all Gmail labels...")
        labels = get_labels()
        
        # Filter out system labels we don't want to use for training
        system_labels = {
            'INBOX', 'SENT', 'DRAFT', 'SPAM', 'TRASH', 'IMPORTANT', 'STARRED',
            'CHAT', 'CATEGORY_PERSONAL', 'CATEGORY_SOCIAL', 'CATEGORY_PROMOTIONS',
            'CATEGORY_UPDATES', 'CATEGORY_FORUMS', 'UNREAD'
        }
        
        # Separate user labels from system labels
        user_labels = []
        system_only = []
        
        for label in labels:
            if label['name'] in system_labels:
                system_only.append(label)
            else:
                user_labels.append(label)
        
        print(f"\n📊 Found {len(user_labels)} custom labels and {len(system_only)} system labels")
        print("\n🏷️  CUSTOM LABELS (Good for training):")
        print("-" * 50)
        
        # Check email counts for user labels
        for i, label in enumerate(user_labels, 1):
            label_id = label['id']
            label_name = label['name']
            
            try:
                # Get message count for this label
                messages = list_messages(label_ids=[label_id], max_results=1000)
                count = len(messages) if messages else 0
                
                # Show status based on count
                status = ""
                if count >= 50:
                    status = "✅ Excellent"
                elif count >= 20:
                    status = "✔️  Good"
                elif count >= 10:
                    status = "⚠️  Fair"
                elif count > 0:
                    status = "❌ Too few"
                else:
                    status = "❌ Empty"
                
                print(f"{i:2d}. {label_name:<40} ({count:3d} emails) {status}")
                
            except Exception as e:
                print(f"{i:2d}. {label_name:<40} (Error: {str(e)})")
        
        print(f"\n🔧 SYSTEM LABELS:")
        print("-" * 50)
        for label in system_only:
            print(f"    {label['name']}")
        
        print(f"\n💡 RECOMMENDATIONS:")
        print("-" * 50)
        print("• For good training, aim for 20+ emails per category")
        print("• 50+ emails per category is ideal")
        print("• Focus on your most important categories first")
        print("• You can organize emails in Gmail web interface")
        print("• Apply labels to emails by selecting them and choosing a label")
        
        print(f"\n📝 NEXT STEPS:")
        print("-" * 50)
        print("1. Go to Gmail web interface (gmail.com)")
        print("2. Search for emails you want to categorize")
        print("3. Select multiple emails (checkbox)")
        print("4. Click the Labels button and apply appropriate labels")
        print("5. Repeat for each category until you have 20+ emails each")
        print("6. Run this script again to check your progress")
        print("7. When ready, run train_from_folders.py to train the model")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\nMake sure you've authenticated with Gmail first.")
        print("Run: python show_real_messages.py")

if __name__ == "__main__":
    main()