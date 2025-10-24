#!/usr/bin/env python3
"""
Test Gmail authentication setup.
Run this after placing credentials.json in the project root.
"""


def test_gmail_auth():
    """Test Gmail authentication."""
    try:
        from src.gmail_ml_client.gmail_client import get_labels, get_service

        print("🔐 Testing Gmail authentication...")

        # This will trigger the OAuth flow if needed
        service = get_service()
        print("✅ Gmail service authenticated successfully!")

        # Test getting labels to verify API access
        labels = get_labels()
        print(f"✅ Gmail API access confirmed! Found {len(labels)} labels")

        # Show some basic account info
        system_labels = [l for l in labels if l["type"] == "system"]
        user_labels = [l for l in labels if l["type"] == "user"]

        print(f"📧 System labels: {len(system_labels)}")
        print(f"🏷️  User labels: {len(user_labels)}")

        # Test passed successfully
        print("✅ Test completed successfully!")

    except FileNotFoundError as e:
        print(f"❌ Missing credentials.json file: {e}")
        print("\n📋 Setup steps:")
        print("1. Go to https://console.cloud.google.com/")
        print("2. Enable Gmail API")
        print("3. Create OAuth credentials")
        print("4. Download as 'credentials.json' in project root")
        assert False, f"Missing credentials.json file: {e}"

    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        assert False, f"Authentication failed: {e}"


if __name__ == "__main__":
    try:
        test_gmail_auth()
        print("\n🎉 Gmail authentication is working!")
        print("You can now use the Gmail ML Client commands.")
    except AssertionError:
        print("\n⚠️  Please complete the authentication setup first.")
