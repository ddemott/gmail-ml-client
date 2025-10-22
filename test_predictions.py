#!/usr/bin/env python3
"""
Test the trained model on real Gmail messages to see how well it predicts.
"""

import sys
import os

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from gmail_client import list_messages, get_message, get_labels
from preprocessor import extract_text
from model import load, predict
import random

def main():
    try:
        print("🧪 Testing Your Trained Model on Real Emails")
        print("=" * 60)
        
        # Load the trained model
        print("🤖 Loading your trained model...")
        try:
            vectorizer, label_encoder, model = load()
            classes = label_encoder.classes_
            print(f"✅ Model loaded! Trained on {len(classes)} categories:")
            for i, category in enumerate(classes, 1):
                print(f"   {i:2d}. {category}")
        except Exception as e:
            print(f"❌ Error loading model: {e}")
            print("Make sure you've trained the model first with: python train_from_folders.py")
            return
        
        print(f"\n🔍 Getting recent emails from your inbox...")
        
        # Get some recent messages from inbox
        messages = list_messages(max_results=20)
        if not messages:
            print("❌ No messages found")
            return
        
        print(f"📧 Found {len(messages)} recent messages. Testing predictions...\n")
        
        # Test predictions on a sample of messages
        test_messages = random.sample(messages, min(10, len(messages)))
        
        for i, msg in enumerate(test_messages, 1):
            try:
                # Get message details
                full_msg = get_message(msg['id'])
                text = extract_text(full_msg)
                
                # Get subject and sender
                headers = full_msg.get('payload', {}).get('headers', [])
                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
                sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
                
                # Make prediction
                predictions, confidences, spam_scores = predict([text])
                prediction = predictions[0]
                confidence = confidences[0]
                
                print(f"📧 Email {i}:")
                print(f"   From: {sender[:60]}...")
                print(f"   Subject: {subject[:60]}...")
                print(f"   🎯 Predicted: {prediction} (confidence: {confidence:.1%})")
                
                # Show snippet of email content
                snippet = text[:100].replace('\n', ' ').strip()
                print(f"   📝 Content preview: {snippet}...")
                print()
                
            except Exception as e:
                print(f"❌ Error processing message {i}: {e}")
        
        print("\n💡 How to improve predictions:")
        print("• Add more emails to folders with low confidence predictions")
        print("• Create new folders for email types the model doesn't recognize")
        print("• Re-train after organizing more emails")
        print("• Use the check_folders.py script to see which categories need more emails")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()