# app.py - Working Flask + Gradio for Render
import os
from flask import Flask, redirect, request, session, render_template_string
from dotenv import load_dotenv
from auth import get_google_login_url, verify_google_token, create_session
import secrets
import gradio as gr

load_dotenv()

# Configuration
PORT = int(os.getenv("PORT", 7860))
IS_PRODUCTION = os.getenv("RENDER") is not None
BASE_URL = os.getenv("RENDER_EXTERNAL_URL", f"http://localhost:{PORT}") if IS_PRODUCTION else f"http://localhost:{PORT}"

print(f"🌍 Mode: {'PRODUCTION' if IS_PRODUCTION else 'LOCAL'}")
print(f"🔗 URL: {BASE_URL}")

# Flask app
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", secrets.token_hex(32))
authenticated_sessions = {}

# Login page HTML
LOGIN_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>Adhyayan - Login</title>
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
        .login-container {
            background: rgba(30, 30, 30, 0.9);
            padding: 50px;
            border-radius: 20px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.5);
            text-align: center;
            max-width: 400px;
        }
        h1 { color: #e6d8b9; font-size: 36px; margin-bottom: 10px; }
        .subtitle { color: #b0b0b0; margin-bottom: 40px; }
        .login-btn {
            background: linear-gradient(135deg, #6b4e71, #8e6a9f);
            color: white;
            padding: 15px 40px;
            font-size: 18px;
            border-radius: 12px;
            text-decoration: none;
            display: inline-block;
            transition: all 0.3s ease;
        }
        .login-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 20px rgba(142, 106, 159, 0.4);
        }
        .feature-list {
            text-align: left;
            margin: 30px 0;
            color: #d0d0d0;
            list-style: none;
            padding: 0;
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
            <li>AI-powered Q&A</li>
            <li>Discover related research</li>
            <li>Semantic search</li>
        </ul>
        <a href="/login" class="login-btn">🔐 Login with Google</a>
    </div>
</body>
</html>
"""

@app.route('/')
def index():
    if 'session_id' in session and session['session_id'] in authenticated_sessions:
        return redirect('/app')
    return render_template_string(LOGIN_PAGE)

@app.route('/login')
def login():
    auth_url, state = get_google_login_url()
    session['oauth_state'] = state
    return redirect(auth_url)

@app.route('/callback')
def callback():
    code = request.args.get('code')
    if not code:
        return "❌ Authentication failed", 400
    
    user_info = verify_google_token(code)
    if not user_info:
        return "❌ Invalid token", 400
    
    session_id = create_session(user_info)
    authenticated_sessions[session_id] = user_info
    session['session_id'] = session_id
    session['user_info'] = user_info
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Success</title>
        <style>
            body {{
                font-family: 'Inter', sans-serif;
                background: linear-gradient(135deg, #0f0f0f 0%, #1a1a2e 100%);
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                margin: 0;
                color: #f2f2f2;
            }}
            .container {{
                background: rgba(30, 30, 30, 0.9);
                padding: 50px;
                border-radius: 20px;
                text-align: center;
            }}
            h1 {{ color: #8e6a9f; }}
            a {{
                background: linear-gradient(135deg, #6b4e71, #8e6a9f);
                color: white;
                padding: 15px 40px;
                border-radius: 12px;
                text-decoration: none;
                display: inline-block;
                margin-top: 20px;
            }}
        </style>
        <script>setTimeout(function(){{window.location.href='/app';}}, 2000);</script>
    </head>
    <body>
        <div class="container">
            <h1>✅ Login Successful!</h1>
            <p>Welcome, <strong>{user_info['name']}</strong></p>
            <p>Redirecting...</p>
            <a href="/app">Continue to App →</a>
        </div>
    </body>
    </html>
    """

@app.route('/logout')
def logout_route():
    session_id = session.get('session_id')
    if session_id and session_id in authenticated_sessions:
        del authenticated_sessions[session_id]
    session.clear()
    return redirect('/')

# Create Gradio app
from main_gradio import create_gradio_interface
gradio_app = create_gradio_interface(authenticated_sessions)

# Mount Gradio to Flask at /app
app = gr.mount_gradio_app(app, gradio_app, path="/app")

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 Adhyayan Research Paper Analyzer")
    print("=" * 60)
    print(f"📍 {BASE_URL}")
    print("=" * 60)
    app.run(host='0.0.0.0', port=PORT, debug=False)