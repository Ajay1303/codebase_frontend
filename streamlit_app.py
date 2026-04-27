"""
Streamlit UI — Codebase Q&A Assistant
======================================
Run locally  : streamlit run streamlit_app.py
Deploy       : Push to GitHub → connect to share.streamlit.io
"""
import streamlit as st
import requests
import time

# ── Page configuration ────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Codebase Q&A Assistant",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Backend URL ───────────────────────────────────────────────────────────────
# Change this to your deployed FastAPI URL when hosting on Render / Railway
BACKEND_URL = "https://codebase-assistance.onrender.com"

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ── Global ── */
[data-testid="stAppViewContainer"] {
    background: #0d1117;
}
[data-testid="stSidebar"] {
    background: #161b22;
    border-right: 1px solid #30363d;
}

/* ── Inputs ── */
input[type="text"] {
    background-color: #161b22 !important;
    color: #e6edf3 !important;
    border: 1px solid #30363d !important;
    border-radius: 6px !important;
}

/* ── Answer box ── */
.answer-card {
    background: #161b22;
    border: 1px solid #30363d;
    border-left: 4px solid #7c3aed;
    border-radius: 8px;
    padding: 18px 22px;
    color: #e6edf3;
    font-size: 15px;
    line-height: 1.8;
    margin-top: 10px;
    white-space: pre-wrap;
}

/* ── Source chips ── */
.chip-row { margin-top: 10px; }
.chip {
    display: inline-block;
    background: #21262d;
    color: #a78bfa;
    border: 1px solid #30363d;
    border-radius: 20px;
    padding: 3px 12px;
    font-size: 12px;
    font-family: monospace;
    margin: 3px 3px 3px 0;
}

/* ── Section badges ── */
.badge {
    background: #7c3aed;
    color: white;
    border-radius: 12px;
    padding: 3px 12px;
    font-size: 13px;
    font-weight: 700;
    display: inline-block;
    margin-bottom: 8px;
}

/* ── Metric tiles ── */
.metric-row {
    display: flex;
    gap: 12px;
    margin-top: 12px;
}
.metric-tile {
    flex: 1;
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 12px 16px;
    text-align: center;
}
.metric-num  { font-size: 26px; font-weight: 700; color: #a78bfa; }
.metric-label{ font-size: 12px; color: #8b949e; margin-top: 2px; }

/* ── Chat bubbles ── */
.q-bubble {
    background: #21262d;
    border-radius: 8px;
    padding: 10px 14px;
    color: #e6edf3;
    margin-bottom: 6px;
    font-weight: 500;
}
.divider-line {
    border: none;
    border-top: 1px solid #21262d;
    margin: 20px 0;
}
</style>
""", unsafe_allow_html=True)


# ── Session state defaults ────────────────────────────────────────────────────
if "repo_name" not in st.session_state:
    st.session_state.repo_name = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "repo_stats" not in st.session_state:
    st.session_state.repo_stats = {}


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🧠 Codebase Q&A")
    st.markdown("Ask natural language questions about any public GitHub repository.")
    st.divider()

    if st.session_state.repo_name:
        st.success(f"✅ Active: `{st.session_state.repo_name}`")
        stats = st.session_state.repo_stats
        if stats:
            st.markdown(
                f"""
                <div class="metric-row">
                  <div class="metric-tile">
                    <div class="metric-num">{stats.get('files_processed', '—')}</div>
                    <div class="metric-label">Files</div>
                  </div>
                  <div class="metric-tile">
                    <div class="metric-num">{stats.get('chunks_created', '—')}</div>
                    <div class="metric-label">Chunks</div>
                  </div>
                </div>
                """,
                unsafe_allow_html=True
            )
        if st.button("🔄 Load a different repo", use_container_width=True):
            st.session_state.repo_name = None
            st.session_state.chat_history = []
            st.session_state.repo_stats = {}
            st.rerun()
    else:
        st.info("No repository loaded yet. Use Step 1 to get started.")

    st.divider()
    st.markdown("**Tech Stack**")
    st.markdown("""
- 🔗 FastAPI backend
- 🦙 Groq Llama 3 70B (LLM)
- 🤗 MiniLM-L6-v2 (Embeddings)
- 🗄️ FAISS (Vector DB)
- 🐙 GitPython (Cloning)
    """)
    st.divider()
    st.caption("Built for showcase · [GitHub](https://github.com)")


# ── Main content ──────────────────────────────────────────────────────────────
st.markdown("# 🧠 Codebase Q&A Assistant")
st.markdown("Understand any GitHub codebase by asking questions in plain English.")
st.markdown('<hr class="divider-line">', unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════
# STEP 1 — Load Repository
# ════════════════════════════════════════════════════════════════════════════
st.markdown('<span class="badge">Step 1</span> &nbsp; Load a GitHub Repository', unsafe_allow_html=True)
st.markdown("")

repo_url = st.text_input(
    label="GitHub Repository URL",
    placeholder="https://github.com/username/repository-name",
    label_visibility="visible",
    disabled=bool(st.session_state.repo_name)  # Lock after loading
)

col_btn, col_hint = st.columns([1, 5])
with col_btn:
    process_btn = st.button(
        "🚀 Process",
        use_container_width=True,
        disabled=bool(st.session_state.repo_name)
    )
with col_hint:
    st.caption("Only public GitHub repos are supported. Large repos may take 2–4 minutes.")

if process_btn:
    if not repo_url.strip():
        st.error("⚠️ Please enter a GitHub URL.")
    elif not repo_url.startswith("https://github.com/"):
        st.error("⚠️ URL must start with https://github.com/")
    else:
        progress_bar = st.progress(0, text="Initialising...")
        status_text = st.empty()

        try:
            # Animate progress while waiting for backend
            status_text.info("📥 Cloning repository from GitHub...")
            progress_bar.progress(15, text="Cloning repo...")
            time.sleep(0.5)

            progress_bar.progress(30, text="Extracting code files...")
            status_text.info("🔍 Extracting and chunking code files...")

            response = requests.post(
                f"{BACKEND_URL}/upload",
                json={"repo_url": repo_url},
                timeout=360
            )

            progress_bar.progress(80, text="Building vector index...")
            status_text.info("🧮 Generating embeddings and building FAISS index...")
            time.sleep(0.5)
            progress_bar.progress(100, text="Done!")

            if response.status_code == 200:
                data = response.json()
                st.session_state.repo_name = data["repo_name"]
                st.session_state.repo_stats = {
                    "files_processed": data["files_processed"],
                    "chunks_created": data["chunks_created"]
                }
                st.session_state.chat_history = []
                status_text.empty()
                progress_bar.empty()
                st.success(
                    f"✅ **{data['repo_name']}** is ready! "
                    f"{data['files_processed']} files · {data['chunks_created']} chunks indexed."
                )
                st.rerun()
            else:
                progress_bar.empty()
                status_text.empty()
                detail = response.json().get("detail", "Unknown error from backend.")
                st.error(f"❌ Backend error: {detail}")

        except requests.exceptions.ConnectionError:
            progress_bar.empty()
            status_text.empty()
            st.error("❌ Cannot connect to the FastAPI backend. Make sure it's running on port 8000.")
        except requests.exceptions.Timeout:
            progress_bar.empty()
            status_text.empty()
            st.error("⏱️ Request timed out. The repository may be too large — try a smaller one.")
        except Exception as e:
            progress_bar.empty()
            status_text.empty()
            st.error(f"Unexpected error: {str(e)}")

st.markdown('<hr class="divider-line">', unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════
# STEP 2 — Ask Questions
# ════════════════════════════════════════════════════════════════════════════
st.markdown('<span class="badge">Step 2</span> &nbsp; Ask Questions About the Code', unsafe_allow_html=True)
st.markdown("")

if not st.session_state.repo_name:
    st.info("💡 Complete Step 1 first — load a repository to enable the Q&A.")
else:
    # Example question chips
    st.caption("💡 Example questions:")
    ex_cols = st.columns(4)
    examples = [
        "What does this project do?",
        "How is authentication handled?",
        "What are the main API endpoints?",
        "How is the database connected?"
    ]
    selected_example = None
    for i, ex in enumerate(examples):
        with ex_cols[i]:
            if st.button(ex, key=f"ex_{i}", use_container_width=True):
                selected_example = ex

    # Question input
    query = st.text_input(
        label="Your question",
        placeholder="e.g. How does error handling work in this codebase?",
        value=selected_example if selected_example else "",
        key="query_input"
    )

    ask_col, clear_col = st.columns([1, 1])
    with ask_col:
        ask_btn = st.button("💬 Ask", use_container_width=True, type="primary")
    with clear_col:
        if st.button("🗑️ Clear Chat", use_container_width=True):
            st.session_state.chat_history = []
            st.rerun()

    if ask_btn:
        if not query.strip():
            st.warning("Please type a question first.")
        else:
            with st.spinner("🔍 Searching code and generating answer..."):
                try:
                    response = requests.post(
                        f"{BACKEND_URL}/ask",
                        json={
                            "query": query,
                            "repo_name": st.session_state.repo_name
                        },
                        timeout=60
                    )

                    if response.status_code == 200:
                        data = response.json()
                        st.session_state.chat_history.append({
                            "question": query,
                            "answer": data["answer"],
                            "sources": data.get("sources", [])
                        })
                    else:
                        detail = response.json().get("detail", "Unknown error.")
                        st.error(f"❌ {detail}")

                except requests.exceptions.ConnectionError:
                    st.error("❌ Cannot connect to backend.")
                except Exception as e:
                    st.error(f"Unexpected error: {str(e)}")

    # ── Chat History ──────────────────────────────────────────────────────
    if st.session_state.chat_history:
        st.markdown('<hr class="divider-line">', unsafe_allow_html=True)
        st.markdown("### 💬 Conversation")

        for item in reversed(st.session_state.chat_history):
            # Question bubble
            st.markdown(
                f'<div class="q-bubble">🧑 {item["question"]}</div>',
                unsafe_allow_html=True
            )

            # Answer card
            st.markdown(
                f'<div class="answer-card">🤖 {item["answer"]}</div>',
                unsafe_allow_html=True
            )

            # Source chips
            if item["sources"]:
                chips = "".join(
                    f'<span class="chip">📄 {s}</span>'
                    for s in item["sources"]
                )
                st.markdown(
                    f'<div class="chip-row"><strong style="color:#8b949e;font-size:12px;">SOURCES &nbsp;</strong>{chips}</div>',
                    unsafe_allow_html=True
                )

            st.markdown('<hr class="divider-line">', unsafe_allow_html=True)
