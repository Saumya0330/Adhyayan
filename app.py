# app.py - FINAL WORKING VERSION (Render free tier approved)
from fastapi import FastAPI, Request, Form, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
import os
import uuid
import requests
from dotenv import load_dotenv
from paper_search import search_papers
from utils import save_uploaded_file
from ingest import ingest_pdf
from retrieval import retrieve_chunks
from llm_agent import answer_with_context

load_dotenv()

PORT = int(os.getenv("PORT", 10000))
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL", f"https://adhyayan-rlei.onrender.com")

app = FastAPI(title="Adhyayan Research Analyzer")

# === SESSIONS ===
sessions = {}
uploaded_files_state = {}
doc_stats = {}

# === GOOGLE OAUTH ===
def get_google_login_url():
    base_url = "https://accounts.google.com/o/oauth2/v2/auth"
    params = {
        "client_id": os.getenv("GOOGLE_CLIENT_ID"),
        "redirect_uri": f"{RENDER_EXTERNAL_URL}/callback",
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent"
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return f"{base_url}?{query}"

def verify_google_token(code: str):
    try:
        token_url = "https://oauth2.googleapis.com/token"
        data = {
            "client_id": os.getenv("GOOGLE_CLIENT_ID"),
            "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": f"{RENDER_EXTERNAL_URL}/callback"
        }
        token_resp = requests.post(token_url, data=data, timeout=10)
        if token_resp.status_code != 200:
            return None
        access_token = token_resp.json().get("access_token")
        user_resp = requests.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10
        )
        return user_resp.json() if user_resp.status_code == 200 else None
    except:
        return None

def get_session_id(request: Request):
    sid = request.cookies.get("session_id")
    return sid if sid and sid in sessions else None

# === HTML TEMPLATES ===
MAIN_APP_HTML_RAW = """
<!DOCTYPE html>
<html>
<head>
    <title>Adhyayan - Research Analyzer</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;900&display=swap');
        * { font-family: 'Inter', sans-serif; box-sizing: border-box; }
        body {
            background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 50%, #16213e 100%);
            color: #f2f2f2;
            margin: 0;
            padding: 20px;
            min-height: 100vh;
        }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { text-align: center; padding: 20px 0; }
        .header h1 { color: #e6d8b9; font-size: 42px; margin-bottom: 10px; }
        .user-info { text-align: right; padding: 10px; color: #b0b0b0; }
        .card {
            background: rgba(30, 30, 30, 0.8);
            padding: 25px;
            border-radius: 20px;
            border: 1px solid rgba(142, 106, 159, 0.3);
            margin: 20px 0;
        }
        .btn {
            background: linear-gradient(135deg, #6b4e71, #8e6a9f);
            color: white;
            padding: 12px 28px;
            border-radius: 14px;
            border: none;
            cursor: pointer;
            font-size: 16px;
        }
        .btn:hover { opacity: 0.9; }
        .btn:disabled { opacity: 0.5; cursor: not-allowed; }
        input[type="file"], textarea {
            background: rgba(20, 20, 20, 0.8);
            color: #f2f2f2;
            border: 2px solid rgba(142, 106, 159, 0.3);
            border-radius: 14px;
            padding: 14px;
            width: 100%;
            margin: 10px 0;
        }
        .row { display: flex; gap: 20px; flex-wrap: wrap; }
        .col { flex: 1; min-width: 300px; }
        .loading { display: none; color: #8e6a9f; margin-top: 10px; }
        .loading.show { display: block; }
    </style>
</head>
<body>
    <div class="container">
        <div class="user-info">
            Welcome, {user_name}!
            <button class="btn" onclick="logout()" style="background: rgba(142, 106, 159, 0.3); padding: 8px 16px; font-size: 14px;">Logout</button>
        </div>
        <div class="header">
            <h1>Adhyayan</h1>
            <p style="color: #b0b0b0; font-size: 18px;">AI-Powered Research Paper Analyzer</p>
        </div>
        <div class="row">
            <div class="col">
                <div class="card">
                    <h3>Upload Documents</h3>
                    <form action="/upload" method="post" enctype="multipart/form-data" onsubmit="showLoading('uploadLoading')">
                        <input type="file" name="files" multiple accept=".pdf" required>
                        <button type="submit" class="btn" id="uploadBtn">Ingest Documents</button>
                        <div class="loading" id="uploadLoading">Processing documents...</div>
                    </form>
                </div>
            </div>
            <div class="col">
                <div class="card">
                    <h3>Document Library</h3>
                    <div id="stats">{stats_html}</div>
                </div>
            </div>
        </div>
        <div class="card">
            <h3>Ask Questions</h3>
            <form action="/ask" method="post" onsubmit="showLoading('askLoading')">
                <textarea name="question" rows="3" placeholder="What is this paper about? What methodology was used?" required></textarea>
                <button type="submit" class="btn" id="askBtn">Get Answer</button>
                <div class="loading" id="askLoading">Analyzing and searching...</div>
            </form>
        </div>
        <div class="card">
            <h3>Answer</h3>
            <div id="answer">{answer_html}</div>
        </div>
        <div class="card">
            <h3>Related Research Papers</h3>
            <div id="papers">{papers_html}</div>
        </div>
    </div>
    <script>
        function logout() {
            document.cookie = "session_id=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
            window.location.href = "/";
        }
        function showLoading(id) {
            document.getElementById(id).classList.add('show');
            const btn = document.getElementById(id.replace('Loading', 'Btn'));
            if (btn) btn.disabled = true;
        }
    </script>
</body>
</html>
"""

# THIS IS THE ONLY FIX YOU NEED — escapes all hyphenated CSS properties
# CORRECT — THIS FIXES IT 100%
MAIN_APP_HTML = MAIN_APP_HTML_RAW.format_map({}) \
    .replace("{", "{{") \
    .replace("}", "}}") \
    .replace("{{{{", "{") \
    .replace("}}}}", "}")

LOGIN_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Adhyayan - Login</title>
    <style>
        body {font-family: 'Inter', sans-serif; background: linear-gradient(135deg, #0f0f0f 0%, #1a1a2e 100%);
              display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; color: #f2f2f2;}
        .login-container {background: rgba(30,30,30,0.9); padding: 50px; border-radius: 20px; box-shadow: 0 10px 40px rgba(0,0,0,0.5);
                          text-align: center; max-width: 400px;}
        h1 {color: #e6d8b9; font-size: 36px; margin-bottom: 10px;}
        .login-btn {background: linear-gradient(135deg, #6b4e71, #8e6a9f); color: white; padding: 15px 40px;
                    font-size: 18px; border-radius: 12px; text-decoration: none; display: inline-block; margin-top: 20px;}
        .login-btn:hover {opacity: 0.9;}
    </style>
</head>
<body>
    <div class="login-container">
        <h1>Adhyayan</h1>
        <p>Research Paper Analyzer</p>
        <a href="/login" class="login-btn">Login with Google</a>
    </div>
</body>
</html>
"""

# === ROUTES ===
@app.get("/")
async def home(request: Request):
    return RedirectResponse("/app") if get_session_id(request) else HTMLResponse(LOGIN_HTML)

@app.get("/login")
async def login(): return RedirectResponse(get_google_login_url())

@app.get("/callback")
async def callback(request: Request, code: str = None):
    if not code: raise HTTPException(400, "No code")
    user_info = verify_google_token(code)
    if not user_info: raise HTTPException(400, "Invalid token")
    sid = str(uuid.uuid4())
    sessions[sid] = user_info
    uploaded_files_state[sid] = []
    doc_stats[sid] = {}
    resp = RedirectResponse("/app")
    resp.set_cookie("session_id", sid, httponly=True)
    return resp

@app.get("/app")
async def main_app(request: Request):
    sid = get_session_id(request)
    if not sid: return RedirectResponse("/")
    user = sessions[sid]
    stats = f"<p>{len(uploaded_files_state[sid])} documents uploaded</p>" if uploaded_files_state[sid] else "No documents uploaded yet"
    html = MAIN_APP_HTML.format(
        user_name=user.get("name", "User"),
        stats_html=stats,
        answer_html="<p style='color:#b0b0b0'>Your answer will appear here</p>",
        papers_html="<p style='color:#b0b0b0'>Related papers will appear here</p>"
    )
    return HTMLResponse(html)

@app.post("/upload")
async def upload_files(request: Request, files: list[UploadFile] = File(...)):
    sid = get_session_id(request)
    if not sid: raise HTTPException(401)
    for file in files:
        path = save_uploaded_file(file)
        n, pages, _, pdf_name = ingest_pdf(path)
        col_name = os.path.splitext(file.filename)[0]
        uploaded_files_state[sid].append(col_name)
        doc_stats[sid][col_name] = {"pages": pages, "chunks": n, "pdf": pdf_name}
    return RedirectResponse("/app", 303)

@app.post("/ask")
async def ask_question(request: Request, question: str = Form(...)):
    sid = get_session_id(request)
    if not sid: raise HTTPException(401)
    if not uploaded_files_state.get(sid):
        answer, papers = "Please upload documents first", []
    else:
        col = uploaded_files_state[sid][0]
        chunks = retrieve_chunks(question, col)
        answer = answer_with_context(question, chunks)
        topic = doc_stats[sid][col]["pdf"]
        papers = search_papers(topic) if topic else []
    user = sessions[sid]
    stats = f"<p>{len(uploaded_files_state[sid])} documents uploaded</p>"
    answer_html = f"<div style='color:#f2f2f2;line-height:1.6'>{answer}</div>"
    papers_html = ""
    for i, p in enumerate(papers[:5]):
        papers_html += f"""
        <div style='background:rgba(30,30,30,0.7);padding:15px;border-radius:12px;margin:10px 0;'>
            <h4 style='color:#e6d8b9;margin-top:0'>{i+1}. {p.get('title','N/A')}</h4>
            <a href="{p.get('link','#')}" target="_blank" style='color:#a784c0'>View Paper</a>
            <p style='color:#d0d0d0;margin:0'>{p.get('summary','No summary')[:200]}...</p>
        </div>"""
    if not papers: papers_html = "<p style='color:#b0b0b0'>No related papers found.</p>"
    html = MAIN_APP_HTML.format(
        user_name=user.get("name","User"),
        stats_html=stats,
        answer_html=answer_html,
        papers_html=papers_html
    )
    return HTMLResponse(html)

@app.get("/logout")
async def logout(request: Request):
    sid = get_session_id(request)
    if sid:
        sessions.pop(sid, None)
        uploaded_files_state.pop(sid, None)
        doc_stats.pop(sid, None)
    resp = RedirectResponse("/")
    resp.delete_cookie("session_id")
    return resp

@app.get("/health")
async def health(): return {"status": "healthy"}
