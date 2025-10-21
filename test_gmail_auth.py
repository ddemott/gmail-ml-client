#!/usr/bin/env python3
"""
Test Gmail authentication setup.
Run this after placing credentials.json in the project root.
"""

def test_gmail_auth():
    """Test Gmail authentication."""
    try:
        from gmail_client import get_service, get_labels
        
        print("🔐 Testing Gmail authentication...")
        
        # This will trigger the OAuth flow if needed
        service = get_service()
        print("✅ Gmail service authenticated successfully!")
        
        # Test getting labels to verify API access
        labels = get_labels()
        print(f"✅ Gmail API access confirmed! Found {len(labels)} labels")
        
        # Show some basic account info
        system_labels = [l for l in labels if l['type'] == 'system']
        user_labels = [l for l in labels if l['type'] == 'user']
        
        print(f"📧 System labels: {len(system_labels)}")
        print(f"🏷️  User labels: {len(user_labels)}")
        
        return True
        
    except FileNotFoundError as e:
        print(f"❌ Missing credentials.json file: {e}")
        print("\n📋 Setup steps:")
        print("1. Go to https://console.cloud.google.com/")
        print("2. Enable Gmail API")
        print("3. Create OAuth credentials")
        print("4. Download as 'credentials.json' in project root")
        return False
        
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        return False

if __name__ == "__main__":
    success = test_gmail_auth()
    if success:
        print("\n🎉 Gmail authentication is working!")
        print("You can now use the Gmail ML Client commands.")
    else:
        print("\n⚠️  Please complete the authentication setup first.")