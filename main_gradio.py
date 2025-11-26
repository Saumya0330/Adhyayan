# main_gradio.py - Beautiful Modern UI
import gradio as gr
import os
import requests
from dotenv import load_dotenv
from paper_search import search_papers
from utils import save_uploaded_file
from ingest import ingest_pdf
from retrieval import retrieve_chunks
from llm_agent import answer_with_context

load_dotenv()
os.environ["GROQ_API_KEY"] = os.getenv("GROQ_API_KEY")

# Global state per session
uploaded_files_state = {}
doc_stats = {}


def get_session_id():
    """Get a session identifier for the current user."""
    return "user_session"


def ingest_files(files, session_state):
    """Ingest files for current user session"""
    session_id = session_state or get_session_id()
    
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

    return info, format_stats(session_id)


def format_stats(session_id):
    """Format stats for specific user with beautiful cards"""
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
            margin: 10px 0; border: 1px solid rgba(90, 90, 90, 0.4);
            transition: all 0.3s ease;">
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


def ask_question(question, session_state):
    """Answer question for current user session"""
    session_id = session_state or get_session_id()
    
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
            margin: 15px 0; border-left: 4px solid #8e6a9f;
            transition: all 0.3s ease; backdrop-filter: blur(10px);">
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


def create_gradio_interface(authenticated_sessions):
    """
    Creates the beautiful Gradio interface.
    """
    
    # Enhanced CSS with animations and modern design
    css = """
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;900&display=swap');
    
    * {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    body, .gradio-container {
        background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 50%, #16213e 100%) !important;
        background-attachment: fixed;
        color: #f2f2f2 !important;
    }
    
    /* Animated gradient background */
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
    
    /* Glass morphism cards */
    .card {
        background: rgba(30, 30, 30, 0.8) !important;
        padding: 25px !important;
        border-radius: 20px !important;
        backdrop-filter: blur(20px) !important;
        border: 1px solid rgba(142, 106, 159, 0.3) !important;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4), 
                    0 0 0 1px rgba(255, 255, 255, 0.05) inset !important;
        transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1) !important;
        position: relative;
        z-index: 1;
    }
    
    .card:hover {
        transform: translateY(-4px);
        box-shadow: 0 12px 40px rgba(142, 106, 159, 0.3), 
                    0 0 0 1px rgba(255, 255, 255, 0.1) inset !important;
        border-color: rgba(142, 106, 159, 0.5) !important;
    }
    
    /* Animated title */
    #title {
        color: #e6d8b9 !important;
        font-weight: 900 !important;
        text-align: center !important;
        font-size: 42px !important;
        letter-spacing: 2px !important;
        margin: 30px 0 !important;
        text-shadow: 0 4px 20px rgba(230, 216, 185, 0.3);
        animation: glow 3s ease-in-out infinite alternate;
    }
    
    @keyframes glow {
        from { text-shadow: 0 4px 20px rgba(230, 216, 185, 0.3); }
        to { text-shadow: 0 4px 30px rgba(230, 216, 185, 0.6), 0 0 40px rgba(142, 106, 159, 0.4); }
    }
    
    /* Enhanced buttons */
    button {
        background: linear-gradient(135deg, #6b4e71 0%, #8e6a9f 100%) !important;
        color: #fff !important;
        border-radius: 14px !important;
        font-weight: 600 !important;
        border: none !important;
        padding: 12px 28px !important;
        font-size: 15px !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        box-shadow: 0 4px 15px rgba(142, 106, 159, 0.3);
        position: relative;
        overflow: hidden;
    }
    
    button::before {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
        transition: left 0.5s;
    }
    
    button:hover::before {
        left: 100%;
    }
    
    button:hover {
        background: linear-gradient(135deg, #7d5b85 0%, #a784c0 100%) !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 25px rgba(142, 106, 159, 0.5) !important;
    }
    
    button:active {
        transform: translateY(0) !important;
    }
    
    /* Modern inputs */
    textarea, input, .input-wrap {
        background: rgba(20, 20, 20, 0.8) !important;
        color: #f2f2f2 !important;
        border-radius: 14px !important;
        border: 2px solid rgba(142, 106, 159, 0.3) !important;
        padding: 14px !important;
        transition: all 0.3s ease !important;
        font-size: 15px !important;
    }
    
    textarea:focus, input:focus {
        border-color: rgba(142, 106, 159, 0.6) !important;
        box-shadow: 0 0 0 4px rgba(142, 106, 159, 0.1) !important;
        outline: none !important;
    }
    
    /* Labels */
    label, .gradio-label {
        color: #e6d8b9 !important;
        font-weight: 600 !important;
        font-size: 15px !important;
        margin-bottom: 8px !important;
    }
    
    /* Markdown content */
    .markdown {
        white-space: pre-wrap !important;
        line-height: 1.7 !important;
        color: #f2f2f2 !important;
    }
    
    .markdown h1, .markdown h2, .markdown h3 {
        color: #e6d8b9 !important;
        margin-top: 20px !important;
        margin-bottom: 12px !important;
    }
    
    .markdown a {
        color: #a784c0 !important;
        text-decoration: none !important;
        border-bottom: 1px solid rgba(167, 132, 192, 0.3);
        transition: all 0.2s ease;
    }
    
    .markdown a:hover {
        color: #c9a5d4 !important;
        border-bottom-color: #c9a5d4;
    }
    
    /* File upload area */
    .file-preview {
        background: rgba(142, 106, 159, 0.1) !important;
        border: 2px dashed rgba(142, 106, 159, 0.4) !important;
        border-radius: 14px !important;
        padding: 20px !important;
        transition: all 0.3s ease !important;
    }
    
    .file-preview:hover {
        border-color: rgba(142, 106, 159, 0.6) !important;
        background: rgba(142, 106, 159, 0.15) !important;
    }
    
    /* Info banner */
    .info-banner {
        background: linear-gradient(135deg, rgba(107, 78, 113, 0.2), rgba(142, 106, 159, 0.2));
        padding: 16px 24px;
        border-radius: 14px;
        border-left: 4px solid #8e6a9f;
        margin: 20px 0;
        color: #e8e8e8;
        font-size: 14px;
    }
    
    /* Scrollbar */
    ::-webkit-scrollbar {
        width: 10px;
        height: 10px;
    }
    
    ::-webkit-scrollbar-track {
        background: rgba(20, 20, 20, 0.5);
        border-radius: 10px;
    }
    
    ::-webkit-scrollbar-thumb {
        background: linear-gradient(135deg, #6b4e71, #8e6a9f);
        border-radius: 10px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: linear-gradient(135deg, #7d5b85, #a784c0);
    }
    
    /* Loading animation */
    .loading {
        animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
    }
    
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.7; }
    }
    
    /* Row spacing */
    .gr-row {
        gap: 20px !important;
    }
    """

    with gr.Blocks(css=css, theme=gr.themes.Base()) as demo:
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
        
        # Info Banner
        gr.Markdown(
            """
            <div class="info-banner">
                💡 <strong>Pro Tip:</strong> Upload your research papers in PDF format, then ask questions to get instant insights and discover related research!
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
                    label="Select PDF Files",
                    elem_classes="file-upload"
                )
                upload_btn = gr.Button("🚀 Ingest Documents", variant="primary", size="lg")
                ingest_output = gr.Markdown("", elem_classes="output-box")

            # Right Column - Stats
            with gr.Column(scale=1, elem_classes="card"):
                gr.Markdown("### 📊 Document Library")
                stats_box = gr.Markdown(
                    """
                    <div style="text-align: center; padding: 40px; color: #b0b0b0;">
                        <p style="font-size: 18px;">📂 No documents yet</p>
                        <p style="font-size: 14px; margin-top: 10px;">Upload PDFs to get started</p>
                    </div>
                    """,
                    elem_classes="stats-display"
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
                """,
                elem_classes="answer-display"
            )

        # Related Papers Section
        with gr.Column(elem_classes="card"):
            related_output = gr.Markdown("", elem_classes="related-papers")
        
        # Footer
        with gr.Row():
            logout_btn = gr.Button("🚪 Logout", size="sm", variant="secondary")
        
        # Event handlers
        upload_btn.click(
            ingest_files,
            inputs=[file_input, session_state],
            outputs=[ingest_output, stats_box]
        )

        ask_btn.click(
            ask_question,
            inputs=[question, session_state],
            outputs=[answer_output, related_output]
        )
        
        # Logout redirects to Flask logout route
        logout_btn.click(
            None,
            None,
            None,
            js="() => { window.location.href = 'http://localhost:7860/logout'; }"
        )
    
    return demo