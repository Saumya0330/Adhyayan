# test_credentials.py - Run this to test your Google OAuth setup
import os
from dotenv import load_dotenv

load_dotenv()

print("=" * 60)
print("🔍 TESTING GOOGLE OAUTH CREDENTIALS")
print("=" * 60)

# Check if credentials exist
client_id = os.getenv("GOOGLE_CLIENT_ID")
client_secret = os.getenv("GOOGLE_CLIENT_SECRET")

print("\n1. Checking .env file...")
if not client_id:
    print("❌ GOOGLE_CLIENT_ID is missing from .env!")
else:
    print(f"✅ GOOGLE_CLIENT_ID found: {client_id[:30]}...")

if not client_secret:
    print("❌ GOOGLE_CLIENT_SECRET is missing from .env!")
else:
    print(f"✅ GOOGLE_CLIENT_SECRET found: {client_secret[:20]}...")

print("\n2. Checking credential format...")
if client_id:
    if ".apps.googleusercontent.com" in client_id:
        print("✅ Client ID format looks correct")
    else:
        print("⚠️  Client ID might be incorrect - should end with .apps.googleusercontent.com")

if client_secret:
    if client_secret.startswith("GOCSPX-"):
        print("✅ Client Secret format looks correct")
    else:
        print("⚠️  Client Secret might be incorrect - should start with GOCSPX-")

print("\n3. Testing OAuth flow creation...")
try:
    from auth import create_oauth_flow, get_google_login_url
    
    flow = create_oauth_flow()
    print("✅ OAuth flow created successfully")
    
    auth_url, state = get_google_login_url()
    print("✅ Authorization URL generated successfully")
    print(f"\n🔗 Test URL: {auth_url[:100]}...")
    
except Exception as e:
    print(f"❌ Error creating OAuth flow: {e}")
    print("\nPossible issues:")
    print("- Client ID or Secret might be incorrect")
    print("- Credentials might not be from Google Cloud Console")
    print("- Check if you copied the credentials correctly")

print("\n" + "=" * 60)
print("📋 NEXT STEPS IF ERRORS FOUND:")
print("=" * 60)
print("1. Go to https://console.cloud.google.com/")
print("2. Select your project")
print("3. Go to 'APIs & Services' → 'Credentials'")
print("4. Find your OAuth 2.0 Client ID")
print("5. Make sure 'Authorized redirect URIs' has:")
print("   http://localhost:7860/callback")
print("6. Copy the Client ID and Client Secret")
print("7. Update your .env file")
print("8. Restart the application")
print("=" * 60)