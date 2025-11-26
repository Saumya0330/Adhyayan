# auth.py - Fixed with better error handling
import os
import json
from google.oauth2 import id_token
from google.auth.transport import requests
from google_auth_oauthlib.flow import Flow
import secrets
from dotenv import load_dotenv

# Load environment variables FIRST
load_dotenv()

# Load credentials from environment
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

# Dynamic redirect URI based on environment
IS_PRODUCTION = os.getenv("RENDER") is not None
if IS_PRODUCTION:
    BASE_URL = os.getenv("RENDER_EXTERNAL_URL", "https://your-app.onrender.com")
    REDIRECT_URI = f"{BASE_URL}/callback"
else:
    REDIRECT_URI = "http://localhost:7860/callback"

# Validate credentials are loaded
if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
    print("❌ ERROR: Google OAuth credentials not found in .env file!")
    print("Please set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET")
    print(f"Current GOOGLE_CLIENT_ID: {GOOGLE_CLIENT_ID}")
    print(f"Current GOOGLE_CLIENT_SECRET: {GOOGLE_CLIENT_SECRET}")
    exit(1)

print(f"✅ Google Client ID loaded: {GOOGLE_CLIENT_ID[:20]}...")
print(f"✅ Redirect URI: {REDIRECT_URI}")

# In-memory session storage
sessions = {}

def create_oauth_flow():
    """
    Creates Google OAuth flow with proper error handling.
    """
    try:
        client_config = {
            "web": {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [REDIRECT_URI],
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs"
            }
        }
        
        flow = Flow.from_client_config(
            client_config,
            scopes=[
                'https://www.googleapis.com/auth/userinfo.email',
                'https://www.googleapis.com/auth/userinfo.profile',
                'openid'
            ],
            redirect_uri=REDIRECT_URI
        )
        
        return flow
    
    except Exception as e:
        print(f"❌ Error creating OAuth flow: {e}")
        raise


def get_google_login_url():
    """
    Generates the Google login URL.
    """
    try:
        flow = create_oauth_flow()
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='select_account'  # Always show account selector
        )
        
        print(f"✅ Generated auth URL: {authorization_url[:80]}...")
        return authorization_url, state
    
    except Exception as e:
        print(f"❌ Error generating login URL: {e}")
        raise


def verify_google_token(code):
    """
    Exchanges authorization code for user info.
    """
    try:
        print(f"🔄 Attempting to verify token with code: {code[:20]}...")
        
        flow = create_oauth_flow()
        
        # Fetch token using the authorization code
        flow.fetch_token(code=code)
        
        credentials = flow.credentials
        
        # Get user info from Google
        request = requests.Request()
        user_info = id_token.verify_oauth2_token(
            credentials.id_token,
            request,
            GOOGLE_CLIENT_ID
        )
        
        print(f"✅ Successfully authenticated: {user_info.get('email')}")
        
        return {
            'email': user_info.get('email'),
            'name': user_info.get('name'),
            'picture': user_info.get('picture'),
            'email_verified': user_info.get('email_verified')
        }
    
    except Exception as e:
        print(f"❌ Error verifying token: {e}")
        print(f"❌ Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return None


def create_session(user_info):
    """
    Creates a session for logged-in user.
    """
    session_id = secrets.token_urlsafe(32)
    sessions[session_id] = {
        'user': user_info,
        'authenticated': True
    }
    print(f"✅ Session created for {user_info['email']}")
    return session_id


def get_session(session_id):
    """
    Retrieves user session.
    """
    return sessions.get(session_id)


def is_authenticated(session_id):
    """
    Checks if user is logged in.
    """
    session = get_session(session_id)
    return session and session.get('authenticated', False)


def logout(session_id):
    """
    Logs out user by removing their session.
    """
    if session_id in sessions:
        del sessions[session_id]
        print(f"✅ Session {session_id[:10]}... logged out")