# app.py - Flask + Gradio with proper integration
import os
import threading
from flask import Flask, redirect, request, session, render_template_string
from dotenv import load_dotenv
from auth import get_google_login_url, verify_google_token, create_session
import secrets

load_dotenv()

# Get port from environment (Render sets this)
FLASK_PORT = int(os.getenv("PORT", 7860))
GRADIO_PORT = FLASK_PORT + 1

# Determine if running on Render or locally
IS_PRODUCTION = os.getenv("RENDER") is not None

# Set URLs based on environment
if IS_PRODUCTION:
    BASE_URL = os.getenv("RENDER_EXTERNAL_URL", "https://your-app.onrender.com")
    REDIRECT_URI = f"{BASE_URL}/callback"
else:
    BASE_URL = f"http://localhost:{FLASK_PORT}"
    REDIRECT_URI = f"{BASE_URL}/callback"

print(f"🌍 Environment: {'PRODUCTION (Render)' if IS_PRODUCTION else 'LOCAL'}")
print(f"🔗 Base URL: {BASE_URL}")
print(f"🔗 Redirect URI: {REDIRECT_URI}")

# Flask app for handling authentication
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", secrets.token_hex(32))

# Store authenticated sessions
authenticated_sessions = {}

# HTML template for login page
LOGIN_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>Adhyayan - Login</title>
    <style>
        body {
            font-family: 'Inter', -apple-system, sans-serif;
            background: linear-gradient(135deg, #0f0f0f 0%, #1a1a2e 100%);
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
            color: #f2f2f2;
        }
        .login-container {
            background: rgba(30, 30, 30, 0.9);
            padding: 50px;
            border-radius: 20px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.5);
            text-align: center;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(90, 90, 90, 0.4);
            max-width: 400px;
        }
        h1 {
            color: #e6d8b9;
            font-size: 36px;
            margin-bottom: 10px;
            font-weight: 900;
        }
        .subtitle {
            color: #b0b0b0;
            margin-bottom: 40px;
            font-size: 16px;
        }
        .login-btn {
            background: linear-gradient(135deg, #6b4e71, #8e6a9f);
            color: white;
            border: none;
            padding: 15px 40px;
            font-size: 18px;
            border-radius: 12px;
            cursor: pointer;
            text-decoration: none;
            display: inline-block;
            transition: all 0.3s ease;
            font-weight: 600;
        }
        .login-btn:hover {
            background: linear-gradient(135deg, #7d5b85, #a784c0);
            transform: translateY(-2px);
            box-shadow: 0 5px 20px rgba(142, 106, 159, 0.4);
        }
        .feature-list {
            text-align: left;
            margin: 30px 0;
            color: #d0d0d0;
        }
        .feature-list li {
            margin: 10px 0;
            padding-left: 25px;
            position: relative;
        }
        .feature-list li:before {
            content: "✓";
            position: absolute;
            left: 0;
            color: #8e6a9f;
            font-weight: bold;
        }
    </style>
</head>
<body>
    <div class="login-container">
        <h1>📚 Adhyayan</h1>
        <p class="subtitle">Research Paper Analyzer</p>
        
        <ul class="feature-list">
            <li>Upload and analyze research papers</li>
            <li>AI-powered Q&A on your documents</li>
            <li>Discover related research</li>
            <li>Semantic search across papers</li>
        </ul>
        
        <a href="/login" class="login-btn">
            🔐 Login with Google
        </a>
    </div>
</body>
</html>
"""

SUCCESS_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>Login Successful</title>
    <style>
        body {
            font-family: 'Inter', sans-serif;
            background: linear-gradient(135deg, #0f0f0f 0%, #1a1a2e 100%);
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
            color: #f2f2f2;
        }
        .success-container {
            background: rgba(30, 30, 30, 0.9);
            padding: 50px;
            border-radius: 20px;
            text-align: center;
            border: 1px solid rgba(90, 90, 90, 0.4);
        }
        h1 { color: #8e6a9f; }
        .continue-btn {
            background: linear-gradient(135deg, #6b4e71, #8e6a9f);
            color: white;
            border: none;
            padding: 15px 40px;
            font-size: 18px;
            border-radius: 12px;
            cursor: pointer;
            text-decoration: none;
            display: inline-block;
            margin-top: 20px;
        }
    </style>
    <script>
        // Auto-redirect after 2 seconds
        setTimeout(function() {
            window.location.href = '{{ gradio_url }}';
        }, 2000);
    </script>
</head>
<body>
    <div class="success-container">
        <h1>✅ Login Successful!</h1>
        <p>Welcome, <strong>{{ user_name }}</strong></p>
        <p>{{ user_email }}</p>
        <p style="color: #b0b0b0; margin-top: 20px;">Redirecting to app...</p>
        <a href="{{ gradio_url }}" class="continue-btn">Continue to App →</a>
    </div>
</body>
</html>
"""


@app.route('/')
def index():
    """
    Landing page - shows login if not authenticated.
    """
    if 'session_id' in session and session['session_id'] in authenticated_sessions:
        gradio_url = f"{BASE_URL.replace(str(FLASK_PORT), str(GRADIO_PORT))}" if not IS_PRODUCTION else f"{BASE_URL}/gradio"
        return redirect(gradio_url)
    return render_template_string(LOGIN_PAGE)


@app.route('/login')
def login():
    """
    Initiates Google OAuth flow.
    """
    auth_url, state = get_google_login_url()
    session['oauth_state'] = state
    return redirect(auth_url)


@app.route('/callback')
def callback():
    """
    Handles the OAuth callback from Google.
    """
    code = request.args.get('code')
    
    if not code:
        return "❌ Authentication failed. No code received.", 400
    
    user_info = verify_google_token(code)
    
    if not user_info:
        return "❌ Authentication failed. Invalid token.", 400
    
    # Create a session for this user
    session_id = create_session(user_info)
    authenticated_sessions[session_id] = user_info
    
    # Store session_id in Flask session
    session['session_id'] = session_id
    session['user_info'] = user_info
    
    gradio_url = f"{BASE_URL.replace(str(FLASK_PORT), str(GRADIO_PORT))}" if not IS_PRODUCTION else f"{BASE_URL}/gradio"
    
    return render_template_string(
        SUCCESS_PAGE, 
        user_name=user_info['name'],
        user_email=user_info['email'],
        gradio_url=gradio_url
    )


@app.route('/logout')
def logout_route():
    """
    Logs out the user.
    """
    session_id = session.get('session_id')
    if session_id and session_id in authenticated_sessions:
        del authenticated_sessions[session_id]
    
    session.clear()
    return redirect('/')


@app.route('/check_auth')
def check_auth():
    """
    API endpoint to check if user is authenticated.
    Gradio will call this.
    """
    session_id = session.get('session_id')
    
    if session_id and session_id in authenticated_sessions:
        return {
            'authenticated': True,
            'user': authenticated_sessions[session_id]
        }
    return {'authenticated': False}


def run_flask():
    """Run Flask app"""
    app.run(host='0.0.0.0', port=FLASK_PORT, debug=False, use_reloader=False)


def run_gradio():
    """Run Gradio app"""
    from main_gradio import create_gradio_interface
    
    # Pass the authenticated_sessions to Gradio
    gradio_app = create_gradio_interface(authenticated_sessions)
    
    # Launch Gradio
    if IS_PRODUCTION:
        # On Render, mount Gradio to Flask at /gradio path
        # This is a simpler approach for production
        print("⚠️ Production mode: Gradio will be accessible at /gradio")
        gradio_app.launch(
            server_name="0.0.0.0",
            server_port=GRADIO_PORT,
            share=False,
            show_error=True
        )
    else:
        # Local development: separate ports
        gradio_app.launch(
            server_name="0.0.0.0",
            server_port=GRADIO_PORT,
            share=False
        )


if __name__ == '__main__':
    print("=" * 60)
    print("🚀 Starting Adhyayan Research Paper Analyzer...")
    print("=" * 60)
    print(f"🔐 Authentication Server: {BASE_URL}")
    if not IS_PRODUCTION:
        print(f"📱 Main Application: http://localhost:{GRADIO_PORT}")
    print("=" * 60)
    print("\n📋 Instructions:")
    print(f"1. Open {BASE_URL} in your browser")
    print("2. Click 'Login with Google'")
    print("3. After login, you'll be redirected to the app")
    print("=" * 60)
    
    if IS_PRODUCTION:
        # On Render, just run Flask (simpler deployment)
        print("🌐 Running in PRODUCTION mode on Render")
        app.run(host='0.0.0.0', port=FLASK_PORT, debug=False)
    else:
        # Local: Run both Flask and Gradio
        flask_thread = threading.Thread(target=run_flask, daemon=True)
        flask_thread.start()
        run_gradio()