# app.py - Pure Gradio app with authentication for Render
import os
import gradio as gr
from dotenv import load_dotenv
import requests
from paper_search import search_papers
from utils import save_uploaded_file
from ingest import ingest_pdf
from retrieval import retrieve_chunks
from llm_agent import answer_with_context

load_dotenv()

# Configuration
PORT = int(os.getenv("PORT", 7860))
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("RENDER_EXTERNAL_URL", f"http://localhost:{PORT}") + "/callback"

# Global state per session
uploaded_files_state = {}
doc_stats = {}
user_sessions = {}

def get_google_login_url():
    """Generate Google OAuth URL"""
    base_url = "https://accounts.google.com/o/oauth2/v2/auth"
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent"
    }
    query_string = "&".join([f"{k}={v}" for k, v in params.items()])
    return f"{base_url}?{query_string}"

def verify_google_token(code):
    """Verify Google OAuth token and get user info"""
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": GOOGLE_REDIRECT_URI
    }
    
    response = requests.post(token_url, data=data)
    if response.status_code != 200:
        return None
    
    tokens = response.json()
    access_token = tokens.get("access_token")
    
    # Get user info
    user_info_response = requests.get(
        "https://www.googleapis.com/oauth2/v3/userinfo",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    
    if user_info_response.status_code == 200:
        return user_info_response.json()
    return None

def create_login_interface():
    """Create the login interface"""
    with gr.Blocks(title="Adhyayan - Login", theme=gr.themes.Soft()) as login_interface:
        gr.Markdown(
            """
            # 📚 Adhyayan
            ### Research Paper Analyzer
            
            **Features:**
            - 📄 Upload and analyze research papers
            - 🤖 AI-powered Q&A  
            - 🔍 Discover related research
            - 🎯 Semantic search
            """
        )
        
        login_btn = gr.Button("🔐 Login with Google", size="lg")
        login_output = gr.Markdown()
        
        def handle_login():
            login_url = get_google_login_url()
            return f"""
            <div style='text-align: center; padding: 20px;'>
                <p>Redirecting to Google...</p>
                <a href='{login_url}' target='_blank'>
                    <button style='padding: 15px 30px; font-size: 16px;'>
                        Click here if not redirected automatically
                    </button>
                </a>
                <script>window.open('{login_url}', '_blank');</script>
            </div>
            """
        
        login_btn.click(handle_login, outputs=login_output)
    
    return login_interface

def create_main_interface():
    """Create the main application interface"""
    # Your existing main_gradio.py code here
    # ... [copy all the functions and UI code from main_gradio.py]
    
    # Enhanced CSS (same as before)
    css = """
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;900&display=swap');
    * { font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; }
    body, .gradio-container {
        background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 50%, #16213e 100%) !important;
        color: #f2f2f2 !important;
    }
    /* ... rest of your CSS ... */
    """
    
    with gr.Blocks(css=css, theme=gr.themes.Base()) as main_interface:
        # Hidden state for session management
        session_state = gr.State(value=None)
        
        # Hero Section
        gr.Markdown(
            """
            <div style="text-align: center; padding: 20px 0;">
                <h1 id='title'>📚 Adhyayan</h1>
                <p style="color: #b0b0b0; font-size: 18px; margin-top: -10px;">
                    AI-Powered Research Paper Analyzer
                </p>
            </div>
            """,
            elem_classes="hero"
        )
        
        # ... [rest of your main interface code from main_gradio.py]
        
        # Add logout button that clears session
        logout_btn = gr.Button("🚪 Logout", size="sm", variant="secondary")
        
        def handle_logout():
            # Clear session data
            return gr.update(visible=False), gr.update(visible=True)
        
        logout_btn.click(
            handle_logout,
            outputs=[main_interface, login_interface]  # You'll need to manage this with tabs
        )
    
    return main_interface

def create_app():
    """Create the main app with authentication flow"""
    with gr.Blocks(title="Adhyayan", theme=gr.themes.Soft()) as app:
        # Check for OAuth callback
        current_path = gr.Textbox(visible=False, value="")
        
        with gr.Tab("Login", id=0) as login_tab:
            login_interface = create_login_interface()
        
        with gr.Tab("App", id=1, visible=False) as app_tab:
            main_interface = create_main_interface()
        
        # Handle OAuth callback
        def check_auth(path):
            if "code=" in path:
                # Extract code from URL
                code = path.split("code=")[1].split("&")[0]
                user_info = verify_google_token(code)
                if user_info:
                    return gr.update(visible=False), gr.update(visible=True)
            return gr.update(visible=True), gr.update(visible=False)
        
        current_path.change(
            check_auth,
            inputs=current_path,
            outputs=[login_tab, app_tab]
        )
    
    return app

# Create and launch the app
app = create_app()

if __name__ == "__main__":
    print(f"🚀 Starting Adhyayan on port {PORT}")
    app.launch(
        server_name="0.0.0.0",
        server_port=PORT,
        share=False,
        debug=False
    )
