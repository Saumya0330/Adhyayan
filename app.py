# app.py - Complete Pure Gradio app for Render
import os
import gradio as gr
from dotenv import load_dotenv
import requests
import json
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
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL", f"http://localhost:{PORT}")

# Global state (simplified for demo)
uploaded_files_state = {}
doc_stats = {}

# Authentication functions
def get_google_login_url():
    """Generate Google OAuth URL"""
    base_url = "https://accounts.google.com/o/oauth2/v2/auth"
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": f"{RENDER_EXTERNAL_URL}/",
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent"
    }
    query_string = "&".join([f"{k}={v}" for k, v in params.items()])
    return f"{base_url}?{query_string}"

def verify_google_token(code):
    """Verify Google OAuth token and get user info"""
    try:
        token_url = "https://oauth2.googleapis.com/token"
        data = {
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": f"{RENDER_EXTERNAL_URL}/"
        }
        
        response = requests.post(token_url, data=data, timeout=30)
        if response.status_code != 200:
            print(f"Token error: {response.status_code} - {response.text}")
            return None
        
        tokens = response.json()
        access_token = tokens.get("access_token")
        
        # Get user info
        user_info_response = requests.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=30
        )
        
        if user_info_response.status_code == 200:
            return user_info_response.json()
        return None
    except Exception as e:
        print(f"OAuth error: {e}")
        return None

# Main application functions
def get_session_id():
    return "user_session"

def ingest_files(files):
    """Ingest files for current user session"""
    session_id = get_session_id()
    
    if session_id not in uploaded_files_state:
        uploaded_files_state[session_id] = []
    if session_id not in doc_stats:
        doc_stats[session_id] = {}
    
    info = "### 📚 Ingestion Complete\n\n"
    for f in files:
        path = save_uploaded_file(f)
        n, pages, doc_summary, pdf_name = ingest_pdf(path)

        col_name = os.path.splitext(os.path.basename(path))[0]
        uploaded_files_state[session_id].append(col_name)

        doc_stats[session_id][col_name] = {
            "pages": pages,
            "chunks": n,
            "path": path,
            "topic_summary": doc_summary,
            "pdf": pdf_name
        }

        info += f"""
<div style="background: linear-gradient(135deg, rgba(107, 78, 113, 0.2), rgba(142, 106, 159, 0.2)); 
            padding: 15px; border-radius: 12px; margin: 10px 0; border-left: 4px solid #8e6a9f;">
    <h4 style="margin: 0 0 8px 0; color: #e6d8b9;">📄 {col_name}</h4>
    <p style="margin: 5px 0; color: #d0d0d0;">✅ {n} chunks extracted from {pages} pages</p>
</div>
"""

    return info, format_stats()

def format_stats():
    """Format stats for specific user with beautiful cards"""
    session_id = get_session_id()
    
    if session_id not in doc_stats or not doc_stats[session_id]:
        return """
<div style="text-align: center; padding: 40px; color: #b0b0b0;">
    <p style="font-size: 18px;">📂 No documents uploaded yet</p>
    <p style="font-size: 14px; margin-top: 10px;">Upload PDFs to get started</p>
</div>
"""

    txt = """
<div style="background: linear-gradient(135deg, rgba(15, 15, 15, 0.8), rgba(26, 26, 46, 0.8)); 
            padding: 20px; border-radius: 16px; border: 1px solid rgba(142, 106, 159, 0.3);">
    <h3 style="color: #e6d8b9; margin-bottom: 20px; font-size: 20px;">📊 Document Library</h3>
"""
    
    for name, st in doc_stats[session_id].items():
        txt += f"""
<div style="background: rgba(30, 30, 30, 0.6); padding: 15px; border-radius: 12px; 
            margin: 10px 0; border: 1px solid rgba(90, 90, 90, 0.4);">
    <h4 style="color: #8e6a9f; margin: 0 0 10px 0;">{name}</h4>
    <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-top: 10px;">
        <div style="background: rgba(142, 106, 159, 0.1); padding: 8px; border-radius: 8px; text-align: center;">
            <div style="color: #e6d8b9; font-size: 24px; font-weight: bold;">{st['pages']}</div>
            <div style="color: #b0b0b0; font-size: 12px;">Pages</div>
        </div>
        <div style="background: rgba(142, 106, 159, 0.1); padding: 8px; border-radius: 8px; text-align: center;">
            <div style="color: #e6d8b9; font-size: 24px; font-weight: bold;">{st['chunks']}</div>
            <div style="color: #b0b0b0; font-size: 12px;">Chunks</div>
        </div>
        <div style="background: rgba(142, 106, 159, 0.1); padding: 8px; border-radius: 8px; text-align: center;">
            <div style="color: #8e6a9f; font-size: 20px;">✓</div>
            <div style="color: #b0b0b0; font-size: 12px;">Ready</div>
        </div>
    </div>
</div>
"""
    
    txt += "</div>"
    return txt

def ask_question(question):
    """Answer question for current user session"""
    session_id = get_session_id()
    
    if session_id not in uploaded_files_state or not uploaded_files_state[session_id]:
        return """
<div style="background: rgba(180, 50, 50, 0.2); padding: 20px; border-radius: 12px; 
            border-left: 4px solid #ff6b6b; color: #ffcccc;">
    <h4>⚠️ No Documents Uploaded</h4>
    <p>Please upload PDF documents first before asking questions.</p>
</div>
""", ""

    col = uploaded_files_state[session_id][0]
    chunks = retrieve_chunks(question, col)
    ans = answer_with_context(question, chunks)

    # Format answer beautifully
    formatted_answer = f"""
<div style="background: linear-gradient(135deg, rgba(30, 30, 30, 0.9), rgba(26, 26, 46, 0.9)); 
            padding: 25px; border-radius: 16px; border: 1px solid rgba(142, 106, 159, 0.4);
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);">
    <h3 style="color: #e6d8b9; margin-bottom: 15px; font-size: 20px;">💡 Answer</h3>
    <div style="color: #f2f2f2; line-height: 1.8; font-size: 15px;">
        {ans}
    </div>
</div>
"""

    # External research search
    topic = doc_stats[session_id][col]["pdf"]
    papers = search_papers(topic)

    pretty = """
<div style="background: linear-gradient(135deg, rgba(15, 15, 15, 0.9), rgba(26, 26, 46, 0.9)); 
            padding: 25px; border-radius: 16px; border: 1px solid rgba(142, 106, 159, 0.3);
            margin-top: 20px;">
    <h3 style="color: #e6d8b9; margin-bottom: 20px; font-size: 22px;">🔬 Related Research Papers</h3>
"""
    
    if not papers:
        pretty += '<p style="color: #b0b0b0; text-align: center; padding: 20px;">No related papers found.</p>'
    else:
        for i, p in enumerate(papers):
            summary = p.get('summary') or "No abstract available"
            summary_preview = summary[:300] if len(summary) > 300 else summary
            
            pretty += f"""
<div style="background: rgba(30, 30, 30, 0.7); padding: 20px; border-radius: 12px; 
            margin: 15px 0; border-left: 4px solid #8e6a9f;">
    <h4 style="color: #e6d8b9; margin: 0 0 12px 0; font-size: 16px;">
        {i+1}. {p['title']}
    </h4>
    <a href="{p['link']}" target="_blank" 
       style="color: #a784c0; text-decoration: none; font-size: 14px; 
              display: inline-block; margin-bottom: 10px;">
        🔗 View Paper →
    </a>
    <p style="color: #d0d0d0; line-height: 1.6; font-size: 14px; margin: 10px 0 0 0;">
        {summary_preview}...
    </p>
</div>
"""
    
    pretty += "</div>"
    return formatted_answer, pretty

def create_main_interface():
    """Create the main application interface"""
    
    css = """
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;900&display=swap');
    * { font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; }
    body, .gradio-container {
        background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 50%, #16213e 100%) !important;
        color: #f2f2f2 !important;
    }
    .gradio-container::before {
        content: '';
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: radial-gradient(circle at 20% 50%, rgba(142, 106, 159, 0.1) 0%, transparent 50%),
                    radial-gradient(circle at 80% 80%, rgba(107, 78, 113, 0.1) 0%, transparent 50%);
        pointer-events: none;
        z-index: 0;
    }
    .card {
        background: rgba(30, 30, 30, 0.8) !important;
        padding: 25px !important;
        border-radius: 20px !important;
        backdrop-filter: blur(20px) !important;
        border: 1px solid rgba(142, 106, 159, 0.3) !important;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4) !important;
    }
    button {
        background: linear-gradient(135deg, #6b4e71 0%, #8e6a9f 100%) !important;
        color: #fff !important;
        border-radius: 14px !important;
        border: none !important;
        padding: 12px 28px !important;
    }
    """
    
    with gr.Blocks(css=css) as interface:
        gr.Markdown(
            """
            <div style="text-align: center; padding: 20px 0;">
                <h1 style="color: #e6d8b9; font-size: 42px; margin-bottom: 10px;">📚 Adhyayan</h1>
                <p style="color: #b0b0b0; font-size: 18px; margin-top: -10px;">
                    AI-Powered Research Paper Analyzer
                </p>
            </div>
            """
        )
        
        # Info Banner
        gr.Markdown(
            """
            <div style="background: rgba(142, 106, 159, 0.2); padding: 16px 24px; border-radius: 14px; 
                        border-left: 4px solid #8e6a9f; margin: 20px 0; color: #e8e8e8;">
                💡 <strong>Pro Tip:</strong> Upload your research papers in PDF format, then ask questions to get instant insights!
            </div>
            """
        )
        
        # Main Content Area
        with gr.Row():
            # Left Column - Upload
            with gr.Column(scale=1, elem_classes="card"):
                gr.Markdown("### 📤 Upload Documents")
                file_input = gr.File(
                    file_types=[".pdf"], 
                    file_count="multiple", 
                    label="Select PDF Files"
                )
                upload_btn = gr.Button("🚀 Ingest Documents", variant="primary", size="lg")
                ingest_output = gr.Markdown("")
            
            # Right Column - Stats
            with gr.Column(scale=1, elem_classes="card"):
                gr.Markdown("### 📊 Document Library")
                stats_box = gr.Markdown(
                    """
                    <div style="text-align: center; padding: 40px; color: #b0b0b0;">
                        <p style="font-size: 18px;">📂 No documents yet</p>
                        <p style="font-size: 14px; margin-top: 10px;">Upload PDFs to get started</p>
                    </div>
                    """
                )
        
        # Q&A Section
        with gr.Column(elem_classes="card"):
            gr.Markdown("### 💬 Ask Questions")
            question = gr.Textbox(
                label="Your Question",
                placeholder="What is this paper about? What methodology was used? What are the key findings?",
                lines=2
            )
            ask_btn = gr.Button("🔍 Get Answer", variant="primary", size="lg")
        
        # Answer Section
        with gr.Column(elem_classes="card"):
            answer_output = gr.Markdown(
                """
                <div style="text-align: center; padding: 40px; color: #b0b0b0;">
                    <p style="font-size: 16px;">Your answer will appear here</p>
                </div>
                """
            )
        
        # Related Papers Section
        with gr.Column(elem_classes="card"):
            related_output = gr.Markdown("")
        
        # Event handlers
        upload_btn.click(
            ingest_files,
            inputs=[file_input],
            outputs=[ingest_output, stats_box]
        )
        
        ask_btn.click(
            ask_question,
            inputs=[question],
            outputs=[answer_output, related_output]
        )
    
    return interface

def create_app():
    """Create the complete app with authentication"""
    
    with gr.Blocks(title="Adhyayan Research Analyzer", theme=gr.themes.Soft()) as app:
        # Store authentication state
        is_authenticated = gr.State(value=False)
        
        # Login Interface
        with gr.Column(visible=True) as login_col:
            gr.Markdown(
                """
                <div style="text-align: center; padding: 40px 20px;">
                    <h1 style="color: #e6d8b9; font-size: 48px; margin-bottom: 10px;">📚 Adhyayan</h1>
                    <p style="color: #b0b0b0; font-size: 20px; margin-bottom: 40px;">AI-Powered Research Paper Analyzer</p>
                    
                    <div style="max-width: 500px; margin: 0 auto; text-align: left;">
                        <div style="background: rgba(142, 106, 159, 0.1); padding: 20px; border-radius: 12px; margin: 20px 0;">
                            <h3 style="color: #e6d8b9; margin-top: 0;">✨ Features</h3>
                            <ul style="color: #d0d0d0; line-height: 1.8;">
                                <li>Upload and analyze research papers</li>
                                <li>AI-powered Q&A with your documents</li>
                                <li>Discover related research papers</li>
                                <li>Semantic search across your library</li>
                            </ul>
                        </div>
                    </div>
                </div>
                """
            )
            
            login_btn = gr.Button("🔐 Login with Google", size="lg")
            login_status = gr.Markdown()
        
        # Main App Interface (hidden initially)
        with gr.Column(visible=False) as app_col:
            main_interface = create_main_interface()
            logout_btn = gr.Button("🚪 Logout", size="sm", variant="secondary")
        
        # Authentication handlers
        def handle_login():
            login_url = get_google_login_url()
            return (
                gr.update(visible=True),  # Keep login visible
                gr.update(visible=False), # Keep app hidden  
                f"""
                <div style='text-align: center; padding: 20px; background: rgba(142, 106, 159, 0.1); border-radius: 12px;'>
                    <p>🔗 <a href='{login_url}' target='_blank' style='color: #a784c0;'>Click here to login with Google</a></p>
                    <p style='color: #b0b0b0; font-size: 14px;'>You will be redirected to Google for authentication.</p>
                </div>
                """
            )
        
        def handle_logout():
            return (
                gr.update(visible=True),
                gr.update(visible=False),
                "Logged out successfully!"
            )
        
        def check_url_for_auth(url):
            """Check if URL contains OAuth callback code"""
            if "code=" in url:
                code = url.split("code=")[1].split("&")[0]
                user_info = verify_google_token(code)
                if user_info:
                    return (
                        gr.update(visible=False),  # Hide login
                        gr.update(visible=True),   # Show app
                        f"Welcome, {user_info.get('name', 'User')}! ✅"
                    )
            return gr.update(), gr.update(), ""
        
        # Event handlers
        login_btn.click(
            handle_login,
            outputs=[login_col, app_col, login_status]
        )
        
        logout_btn.click(
            handle_logout,
            outputs=[login_col, app_col, login_status]
        )
        
        # Check URL on load
        app.load(
            check_url_for_auth,
            inputs=gr.URL(),
            outputs=[login_col, app_col, login_status]
        )
    
    return app

# Create and launch app
if __name__ == "__main__":
    print(f"🚀 Starting Adhyayan on port {PORT}")
    print(f"🔗 URL: {RENDER_EXTERNAL_URL}")
    app = create_app()
    app.launch(
        server_name="0.0.0.0",
        server_port=PORT,
        share=False
    )
