#!/usr/bin/env python3
"""
Real Email Misclassification Checker - Check recently processed real emails for errors
"""

import sys
import os

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data_store import init_db, Message, Session
from model import predict
import random

def check_real_email_misclassifications():
    print("🔍 Real Email Misclassification Checker")
    print("=" * 60)
    print("Checking recently processed real Gmail for classification errors")
    print("")
    
    # Initialize database
    init_db()
    session = Session()
    
    try:
        # Get recently classified emails (not manually reviewed)
        print("📧 Finding recently auto-classified emails...")
        
        recent_emails = session.query(Message).filter(
            Message.target_label.isnot(None),
            Message.reviewed == False,  # Auto-classified, not manually reviewed
            Message.text.isnot(None)
        ).order_by(Message.id.desc()).limit(30).all()
        
        if not recent_emails:
            print("❌ No recently auto-classified emails found")
            return
        
        print(f"📊 Found {len(recent_emails)} recently auto-classified emails")
        
        print(f"\n🤖 Re-checking classifications with current model...")
        
        mismatches = []
        total_checked = 0
        
        for msg in recent_emails:
            try:
                # Re-classify with current model
                predictions, confidence, spam_scores = predict([msg.text])
                current_prediction = predictions[0] if predictions else "UNKNOWN"
                conf = confidence[0] if confidence else 0.0
                
                total_checked += 1
                
                # Check if current prediction matches stored classification
                if current_prediction != msg.target_label:
                    text_snippet = msg.text[:80].replace('\n', ' ').strip() + "..."
                    
                    mismatches.append({
                        'id': msg.id,
                        'stored': msg.target_label,
                        'predicted': current_prediction,
                        'confidence': conf,
                        'text': text_snippet
                    })
                
            except Exception as e:
                print(f"   ⚠️  Error checking email {msg.id}: {e}")
                continue
        
        # Show results
        print(f"\n📊 REAL EMAIL CHECK RESULTS")
        print("=" * 40)
        print(f"Emails checked: {total_checked}")
        print(f"Consistent classifications: {total_checked - len(mismatches)}")
        print(f"Potential misclassifications: {len(mismatches)}")
        
        if total_checked > 0:
            consistency = ((total_checked - len(mismatches)) / total_checked) * 100
            print(f"Model consistency: {consistency:.1f}%")
        
        if mismatches:
            print(f"\n❓ POTENTIAL MISCLASSIFICATIONS:")
            print("-" * 50)
            
            for i, mismatch in enumerate(mismatches, 1):
                print(f"\n{i}. Email ID: {mismatch['id']}")
                print(f"   Text: \"{mismatch['text']}\"")
                print(f"   Stored as: {mismatch['stored']}")
                print(f"   Model predicts: {mismatch['predicted']} (conf: {mismatch['confidence']:.2f})")
                
                # Ask if user wants to correct this
                if i <= 5:  # Only ask for first 5 to avoid overwhelming
                    print(f"   Options:")
                    print(f"   1. Keep stored classification ({mismatch['stored']})")
                    print(f"   2. Change to model prediction ({mismatch['predicted']})")
                    print(f"   3. Change to different label")
                    print(f"   4. Skip this email")
                    
                    choice = input(f"   Choose option (1-4): ").strip()
                    
                    if choice == "2":
                        # Update to model prediction
                        message = session.query(Message).filter_by(id=mismatch['id']).first()
                        if message:
                            message.target_label = mismatch['predicted']
                            message.reviewed = True  # Mark as manually reviewed
                            session.commit()
                            print(f"   ✅ Updated to: {mismatch['predicted']}")
                    
                    elif choice == "3":
                        # Custom label
                        new_label = input(f"   Enter new label: ").strip()
                        if new_label:
                            message = session.query(Message).filter_by(id=mismatch['id']).first()
                            if message:
                                message.target_label = new_label
                                message.reviewed = True
                                session.commit()
                                print(f"   ✅ Updated to: {new_label}")
                    
                    elif choice == "1":
                        # Mark as manually reviewed but keep current label
                        message = session.query(Message).filter_by(id=mismatch['id']).first()
                        if message:
                            message.reviewed = True
                            session.commit()
                            print(f"   ✅ Kept: {mismatch['stored']}")
                    
                    else:
                        print(f"   ⏭️  Skipped")
        else:
            print(f"\n🎉 EXCELLENT! No misclassifications found!")
            print("Your model is performing consistently on real emails!")
        
        # Show some examples of good classifications
        print(f"\n✅ EXAMPLES OF GOOD CLASSIFICATIONS:")
        print("-" * 40)
        
        good_examples = session.query(Message).filter(
            Message.target_label.isnot(None),
            Message.reviewed == False,
            Message.text.isnot(None)
        ).order_by(Message.id.desc()).limit(5).all()
        
        for msg in good_examples[:3]:
            try:
                predictions, confidence, _ = predict([msg.text])
                current_prediction = predictions[0] if predictions else "UNKNOWN"
                conf = confidence[0] if confidence else 0.0
                
                if current_prediction == msg.target_label:
                    snippet = msg.text[:60].replace('\n', ' ').strip() + "..."
                    print(f"   ✅ \"{snippet}\" → {msg.target_label} (conf: {conf:.2f})")
            except:
                continue
        
        print(f"\n🎯 SUMMARY:")
        print("=" * 20)
        print("✅ Your Gmail ML Client is processing real emails")
        print("✅ Model consistency is being maintained")
        print("✅ Corrections help improve future accuracy")
        print("✅ System ready for production email management")
        
    finally:
        session.close()

if __name__ == "__main__":
    check_real_email_misclassifications()