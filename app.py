import streamlit as st
import json
import dataclasses

from rag_code.ret_summ import (
    SC_COASTAL_SITES,
    RetrievalSummarizationNetwork,
    RetrievalResult,
)
from rag_code import database

assert dataclasses.is_dataclass(RetrievalResult)


def _he(text: object, quote: bool = False) -> str:
    """Escape text for safe HTML injection."""
    if text is None:
        return ""
    s = str(text)
    s = (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
    if quote:
        s = s.replace('"', "&quot;").replace("'", "&#x27;")
    return s


st.set_page_config(
    page_title="SC-Coasts | Coastal Resilience Analyzer",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown('<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@500;600&family=DM+Sans:wght@400;500&display=swap" rel="stylesheet">', unsafe_allow_html=True)

# --- Theme Definition ---
THEMES = {
    "Dark": {
        "bg_main": "#111111",
        "bg_secondary": "#1a1a1a",
        "bg_card": "#1a1a1a",
        "bg_card_hover": "#222222",
        "bg_input": "#222222",
        "bg_nav_active": "#2a2a2a",
        "text_main": "#f0f0f0",
        "text_secondary": "#999999",
        "text_muted": "#555555",
        "text_nav": "#999999",
        "border_color": "#2e2e2e",
        "border_color_hover": "#444444",
        "accent_blue": "#185FA5",
        "accent_blue_hover": "#1e4a6e",
        "accent_text": "#378ADD",
        "spinner_color": "#ccc",
    },
    "Light": {
        "bg_main": "#f8f9fa",
        "bg_secondary": "#ffffff",
        "bg_card": "#ffffff",
        "bg_card_hover": "#f1f3f5",
        "bg_input": "#ffffff",
        "bg_nav_active": "#e2e8f0",
        "text_main": "#1a1a1a",
        "text_secondary": "#4a5568",
        "text_muted": "#a0aec0",
        "text_nav": "#4a5568",
        "border_color": "#e2e8f0",
        "border_color_hover": "#cbd5e0",
        "accent_blue": "#378ADD",
        "accent_blue_hover": "#185FA5",
        "accent_text": "#185FA5",
        "spinner_color": "#4a5568",
    }
}

if "settings_appearance" not in st.session_state:
    st.session_state.settings_appearance = "Dark"

def _get_styles():
    theme = THEMES.get(st.session_state.get("settings_appearance", "Dark"), THEMES["Dark"])
    vars_css = "\n".join([f"    --{k.replace('_', '-')}: {v} !important;" for k, v in theme.items()])
    
    return f"""<style>
:root {{
{vars_css}
}}

html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"] {{
    background-color: var(--bg-main) !important;
    font-family: 'DM Sans', sans-serif !important;
    color: var(--text-main) !important;
}}
[data-testid="stHeader"] {{ display: none !important; }}
#MainMenu, footer, [data-testid="collapsedControl"] {{ display: none !important; }}
.block-container {{
    padding-top: 0 !important;
    padding-bottom: 2rem !important;
    max-width: 100% !important;
}}
h1, h2, h3 {{ font-family: 'Playfair Display', serif !important; color: var(--text-main) !important; }}

/* Top Nav Container & Buttons */
div.element-container:has(.top-nav-anchor) + div.element-container {{
    background-color: var(--bg-secondary) !important;
    border-bottom: 0.5px solid var(--border-color) !important;
    padding-top: 1.5rem !important;
    padding-bottom: 1rem !important;
    margin-top: -3.5rem !important;
    margin-bottom: 1rem !important;
}}

/* Municipality card "Add docs" buttons */
div[data-testid="stVerticalBlock"] div.muni-btn-row button {{
    background-color: var(--accent-blue-hover) !important;
    color: var(--accent-text) !important;
    border: 0.5px solid var(--border-color) !important;
    border-radius: 20px !important;
    font-size: 11px !important;
    padding: 3px 12px !important;
    height: auto !important;
    min-height: unset !important;
}}

div.element-container:has(.top-nav-anchor) + div.element-container button {{
    background-color: transparent !important;
    color: var(--text-nav) !important;
    border: none !important;
    font-size: 15px !important;
    font-weight: 500 !important;
    transition: all 0.15s !important;
    height: auto !important;
    padding: 0.5rem 0 !important;
}}
div.element-container:has(.top-nav-anchor) + div.element-container button:hover {{
    color: var(--text-main) !important;
    background-color: transparent !important;
}}

/* Active top nav button */
div.element-container:has(.top-nav-anchor) + div.element-container button[kind="primary"] {{
    color: var(--text-main) !important;
    background-color: var(--bg-nav-active) !important;
    border-radius: 8px !important;
}}

/* Settings Box */
div.element-container:has(.top-nav-anchor) + div.element-container div[data-testid="column"]:last-child button {{
    border: 0.5px solid var(--border-color) !important;
    border-radius: 8px !important;
    padding: 0.4rem !important;
    font-size: 16px !important;
}}
div.element-container:has(.top-nav-anchor) + div.element-container div[data-testid="column"]:last-child button:hover {{
    border-color: var(--border-color-hover) !important;
    background-color: transparent !important;
}}

/* Global Button Styles (Secondary) */
button[kind="secondary"] {{
    background-color: var(--bg-secondary) !important;
    color: var(--text-nav) !important;
    border: 0.5px solid var(--border-color) !important;
    border-radius: 6px !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 13.5px !important;
    transition: all 0.15s !important;
}}
button[kind="secondary"]:hover {{
    background-color: var(--bg-card-hover) !important;
    color: var(--text-main) !important;
    border-color: var(--border-color-hover) !important;
}}
/* Primary Action Buttons */
button[kind="primary"]:not(.top-nav-btn) {{
    background-color: var(--accent-blue) !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 6px !important;
    font-weight: 500 !important;
}}
button[kind="primary"]:not(.top-nav-btn):hover {{
    background-color: var(--accent-blue-hover) !important;
}}

/* Standard Input Widgets */

[data-testid="stTextInput"] input,
[data-testid="stSelectbox"] div[data-baseweb="select"],
[data-testid="stTextArea"] textarea {{
    background-color: var(--bg-input) !important;
    color: var(--text-main) !important;
    border: 0.5px solid var(--border-color) !important;
    border-radius: 6px !important;
    font-family: 'DM Sans', sans-serif !important;
}}
[data-testid="stTextInput"] input::placeholder {{ color: var(--text-muted) !important; }}
[data-testid="stSelectbox"] svg {{ fill: var(--text-muted) !important; }}
[data-testid="stSpinner"] p,
[data-testid="stAlert"] p {{ color: var(--text-secondary) !important; }}

/* Pills & Multi-select */
[data-testid="stPills"] button,
[data-testid="stPills"] [data-testid="stPills-item"],
div[role="radiogroup"] button {{
    background-color: var(--bg-secondary) !important;
    color: var(--text-main) !important;
    border: 0.5px solid var(--border-color) !important;
}}
/* Target the text inside specifically */
[data-testid="stPills"] button p,
[data-testid="stPills"] [data-testid="stPills-item"] p {{
    color: var(--text-main) !important;
}}
[data-testid="stPills"] button[aria-checked="true"],
[data-testid="stPills"] [data-testid="stPills-item"][aria-checked="true"] {{
    background-color: var(--accent-blue) !important;
    color: #ffffff !important;
    border-color: var(--accent-blue) !important;
}}
[data-testid="stPills"] button[aria-checked="true"] p,
[data-testid="stPills"] [data-testid="stPills-item"][aria-checked="true"] p {{
    color: #ffffff !important;
}}
[data-testid="stWidgetLabel"] p {{
    color: var(--text-main) !important;
    font-weight: 500 !important;
}}
/* Status text visibility (for scrapers) */
[data-testid="stText"] p, .stText {{
    color: var(--text-main) !important;
    font-weight: 500 !important;
    font-size: 14px !important;
}}
</style>"""

st.markdown(_get_styles(), unsafe_allow_html=True)


def _doc_button_key(prefix: str, url: str, doc_id: object = None) -> str:
    base = f"{doc_id}" if doc_id is not None else str(abs(hash(url or "")))
    return f"{prefix}_{base}"


def _render_collapsed_card(doc: dict, tag_colors) -> None:
    _, bg, fg = tag_colors(doc.get("doc_type", "unknown"))
    doc_type_label = _he(
        (doc.get("doc_type") or "Unknown").replace("_", " ").title()
    )
    filename = _he(doc.get("url", "").split("/")[-1] or "Document")
    raw_summary = doc.get("summary") or ""
    summary_plain = raw_summary[:120]
    summary = _he(summary_plain)
    score = float(doc.get("relevance_score") or 0.0)
    muni = _he(doc.get("municipality", "") or "")
    score_pct = int(min(score * 100, 100))
    ellipsis = "…" if len(raw_summary) > 120 else ""

    st.markdown(
        f"""<div style="background:var(--bg-card); border:0.5px solid var(--border-color);
border-radius:12px; padding:1rem 1.25rem; margin-bottom:4px;">
  <span style="font-size:11px; font-weight:500; padding:3px 10px;
               border-radius:20px; background:{bg}; color:{fg};
               display:inline-block; margin-bottom:8px;">
    {doc_type_label}
  </span>
  <p style="font-size:14px; font-weight:500; color:var(--text-main);
            line-height:1.4; margin:0 0 4px;">{filename}</p>
  <p style="font-size:12.5px; color:var(--text-secondary); line-height:1.5;
            margin:0 0 8px;">{summary}{ellipsis}</p>
  <div style="height:3px; background:var(--border-color); border-radius:2px; margin-top:8px;">
    <div style="height:3px; background:var(--accent-blue); border-radius:2px;
                width:{score_pct}%;"></div>
  </div>
  <p style="font-size:11px; color:var(--text-muted); margin:3px 0 8px;">
    Relevance score: {score:.2f}
  </p>
  <div style="display:flex; justify-content:space-between;
              font-size:11.5px; color:var(--text-muted);">
    <span>{muni}</span><span>PDF</span>
  </div>
</div>""",
        unsafe_allow_html=True,
    )

    url = doc.get("url") or ""
    if st.button(
        "View details",
        key=_doc_button_key("open", url, doc.get("id")),
        use_container_width=True,
    ):
        st.session_state.open_card = url
        st.rerun()


def _render_expanded_card(doc: dict, tag_colors) -> None:
    _, bg, fg = tag_colors(doc.get("doc_type", "unknown"))
    doc_type_label = _he(
        (doc.get("doc_type") or "Unknown").replace("_", " ").title()
    )
    filename = _he(doc.get("url", "").split("/")[-1] or "Document")
    score = float(doc.get("relevance_score") or 0.0)
    muni = _he(doc.get("municipality", "") or "")
    url = doc.get("url", "#") or "#"
    url_href = _he(url, quote=True)
    url_text = _he(url)
    summary = _he(doc.get("summary") or "No summary available.")

    raw_findings = doc.get("key_findings", "[]")
    try:
        findings = json.loads(raw_findings) if isinstance(raw_findings, str) else raw_findings
    except (json.JSONDecodeError, TypeError):
        findings = []
    if not isinstance(findings, list):
        findings = []

    findings_html = (
        "".join(
            f'<p style="font-size:13px; color:#ccc; margin-bottom:6px; padding-left:12px; border-left:2px solid #2e2e2e; line-height:1.5;">{_he(str(f))}</p>'
            for f in findings
        )
        if findings
        else '<p style="font-size:13px; color:#555;">No findings extracted.</p>'
    )

    st.markdown(
        f"""<div style="background:var(--bg-card); border:0.5px solid var(--accent-blue);
border-radius:12px; overflow:hidden; margin-bottom:4px;">
  <div style="padding:1rem 1.25rem; border-bottom:0.5px solid var(--border-color);">
    <span style="font-size:11px; font-weight:500; padding:3px 10px;
                 border-radius:20px; background:{bg}; color:{fg};
                 display:inline-block; margin-bottom:6px;">
      {doc_type_label}
    </span>
    <p style="font-size:15px; font-weight:500; color:var(--text-main); margin:0;">
      {filename}
    </p>
  </div>
  <div style="display:grid; grid-template-columns:1fr 1fr; gap:2rem;
              padding:1.5rem; background:var(--bg-secondary);">
    <div>
      <p style="font-size:11px; text-transform:uppercase; letter-spacing:0.06em;
                color:var(--text-muted); margin-bottom:5px;">Municipality</p>
      <p style="font-size:13px; color:var(--text-secondary); margin-bottom:1rem;">{muni}</p>
      <p style="font-size:11px; text-transform:uppercase; letter-spacing:0.06em;
                color:var(--text-muted); margin-bottom:5px;">Document Type</p>
      <p style="font-size:13px; color:var(--text-secondary); margin-bottom:1rem;">{doc_type_label}</p>
      <p style="font-size:11px; text-transform:uppercase; letter-spacing:0.06em;
                color:var(--text-muted); margin-bottom:5px;">Relevance Score</p>
      <p style="font-size:13px; color:var(--text-secondary); margin-bottom:1rem;">{score:.2f}</p>
      <p style="font-size:11px; text-transform:uppercase; letter-spacing:0.06em;
                color:var(--text-muted); margin-bottom:5px;">Summary</p>
      <p style="font-size:13px; color:var(--text-secondary); line-height:1.6;
                margin-bottom:1rem;">{summary}</p>
      <p style="font-size:11px; text-transform:uppercase; letter-spacing:0.06em;
                color:var(--text-muted); margin-bottom:5px;">Source</p>
      <a href="{url_href}" target="_blank" rel="noopener noreferrer"
         style="font-size:12px; color:var(--accent-text); word-break:break-all;">
        {url_text}
      </a>
    </div>
    <div>
      <p style="font-size:11px; text-transform:uppercase; letter-spacing:0.06em;
                color:var(--text-muted); margin-bottom:10px;">Key Findings</p>
      {findings_html}
    </div>
  </div>
</div>""",
        unsafe_allow_html=True,
    )

    st.markdown("</div>", unsafe_allow_html=True)

    col_del, col_close = st.columns([1, 1])
    with col_del:
        if st.button(
            "Delete from Library",
            key=_doc_button_key("delete", url, doc.get("id")),
            type="secondary",
            use_container_width=True,
        ):
            database.delete_document(doc.get("id"))
            st.session_state.open_card = None
            st.toast(f"Deleted {filename}")
            st.rerun()

    with col_close:
        if st.button(
            "Collapse",
            key=_doc_button_key("close", url, doc.get("id")),
            use_container_width=True,
        ):
            st.session_state.open_card = None
            st.rerun()

    st.markdown(
        """
        <script>
        var buttons = window.parent.document.querySelectorAll('button');
        for (var i = 0; i < buttons.length; i++) {
            if (buttons[i].textContent.includes('Delete from Library')) {
                buttons[i].classList.add('danger-btn');
            }
        }
        </script>
        """,
        unsafe_allow_html=True,
    )


def render_search_page() -> None:
    st.markdown(
        """
    <div style="background:var(--bg-secondary); border-bottom:0.5px solid var(--border-color);
                padding:2.5rem 2rem 1.75rem; text-align:center;">
      <h1 style="font-family:'Playfair Display',serif; font-size:30px;
                 color:var(--text-main); margin-bottom:6px;">Search the Document Library</h1>
      <p style="font-size:14px; color:var(--text-secondary); margin-bottom:0;">
        Explore coastal resilience policies, plans, and resources across
        South Carolina municipalities.
      </p>
    </div>
    """,
        unsafe_allow_html=True,
    )

    st.markdown(
        "<div style='padding:0.75rem 0 0.25rem;'></div>",
        unsafe_allow_html=True,
    )
    muni_options = ["All Municipalities"] + list(SC_COASTAL_SITES.keys())

    search_col, muni_col, btn_col = st.columns([4, 2, 1])
    with search_col:
        query = st.text_input(
            "search",
            value=st.session_state.search_query,
            placeholder="Search keywords, topics, or document titles…",
            label_visibility="collapsed",
            key="search_input",
        )
    with muni_col:
        muni = st.selectbox(
            "municipality",
            options=muni_options,
            index=muni_options.index(st.session_state.muni_filter)
            if st.session_state.muni_filter in muni_options
            else 0,
            label_visibility="collapsed",
            key="muni_select",
        )
    with btn_col:
        # Give the search button a specific style by relying on default layout instead of invisible anchors
        if st.button("Search", use_container_width=True, key="search_go"):
            st.session_state.search_query = query
            st.session_state.muni_filter = muni
            st.session_state.open_card = None
            st.rerun()

    tags = ["Flood Management", "Stormwater", "Climate Adaptation", "Zoning", "Infrastructure"]
    
    # st.pills natively renders perfectly spaced and aligned with the components above it
    selection = st.pills("Topics", options=tags, selection_mode="single", label_visibility="collapsed", key="topic_pills")
    
    if selection:
        # Check if the selection was just made to avoid infinite reruns
        if selection.lower() != st.session_state.search_query:
            st.session_state.search_query = selection.lower()
            st.session_state.pop("search_input", None)
            st.rerun()

    active_query = st.session_state.search_query.strip()
    active_muni = st.session_state.muni_filter

    if active_query:
        muni_arg = None if active_muni == "All Municipalities" else active_muni
        docs = database.search_documents(search_term=active_query, municipality=muni_arg)
    else:
        try:
            with database.get_db_connection() as conn:
                sql = "SELECT id, municipality, url, doc_type, summary, key_findings, relevance_score, scraped_at FROM documents"
                params = []
                if active_muni and active_muni != "All Municipalities":
                    sql += " WHERE municipality = ?"
                    params.append(active_muni)
                sql += " ORDER BY relevance_score DESC"
                rows = conn.execute(sql, params).fetchall()
                docs = [dict(r) for r in rows]
        except Exception:
            docs = []

    if not docs and not active_query and active_muni == "All Municipalities":
        label_text = "DOCUMENT LIBRARY"
    elif active_query or active_muni != "All Municipalities":
        label_text = f"{len(docs)} RESULT{'S' if len(docs) != 1 else ''}"
    else:
        label_text = f"{len(docs)} DOCUMENT{'S' if len(docs) != 1 else ''} IN LIBRARY"

    st.markdown(
        f'<p style="font-size:11px; font-weight:500; text-transform:uppercase; '
        f'letter-spacing:0.07em; color:var(--text-muted); padding:1.25rem 0 0.75rem;">'
        f"{_he(label_text)}</p>",
        unsafe_allow_html=True,
    )

    if not docs:
        if not active_query and active_muni == "All Municipalities":
            st.markdown(
                """
            <div style="text-align:center; padding-top:4rem; padding-bottom:1rem; color:#555;
                        font-size:14px; line-height:1.6; font-family:'DM Sans',sans-serif;">
              <div style="font-size:16px; color:var(--text-secondary); margin-bottom:8px; font-weight:500;">
                Your library is empty
              </div>
              <div>No documents have been added yet. Populate your library by scraping municipality sites.</div>
            </div>
            """,
                unsafe_allow_html=True,
            )
            
            b1, b2, b3 = st.columns([1.5, 1, 1.5])
            with b2:
                if st.button("Add Document", type="primary", use_container_width=True):
                    st.session_state.page = "add_document"
                    st.rerun()
        else:
            st.markdown(
                """
            <div style="text-align:center; padding:4rem 2rem; color:#555; font-size:14px;">
              No documents matched your search. Try different keywords or
              broaden the municipality filter.
            </div>
            """,
                unsafe_allow_html=True,
            )
        return

    doc_type_colors = {
        "report": ("tag-blue", "#0d2a40", "#7ab3e0"),
        "plan": ("tag-blue", "#0d2a40", "#7ab3e0"),
        "annual_report": ("tag-green", "#0d2a1a", "#6abf8a"),
        "meeting_minutes": ("tag-green", "#0d2a1a", "#6abf8a"),
        "ordinance": ("tag-amber", "#2a1e0d", "#c9924a"),
        "agenda": ("tag-amber", "#2a1e0d", "#c9924a"),
        "risk": ("tag-coral", "#2a150d", "#d97a5a"),
        "unknown": ("tag-blue", "#0d2a40", "#7ab3e0"),
    }

    def tag_colors(doc_type: str):
        key = (doc_type or "").lower().replace(" ", "_").replace("/", "_")
        for k, v in doc_type_colors.items():
            if k in key:
                return v
        return doc_type_colors["unknown"]

    open_url = st.session_state.open_card

    open_doc = next((d for d in docs if d.get("url") == open_url), None)
    if open_doc:
        _render_expanded_card(open_doc, tag_colors)
        st.markdown(
            "<div style='height:1rem'></div>",
            unsafe_allow_html=True,
        )

    collapsed = [d for d in docs if d.get("url") != open_url]
    CARDS_PER_ROW = 3
    for row_start in range(0, len(collapsed), CARDS_PER_ROW):
        row_docs = collapsed[row_start : row_start + CARDS_PER_ROW]
        cols = st.columns(CARDS_PER_ROW)
        for col, doc in zip(cols, row_docs):
            with col:
                _render_collapsed_card(doc, tag_colors)


def render_add_document_page() -> None:
    st.markdown(
        """
    <div style="background:var(--bg-secondary); border-bottom:0.5px solid var(--border-color);
                padding:2rem 2rem 1.5rem;">
      <h1 style="font-family:'Playfair Display',serif; font-size:26px;
                 color:var(--text-main); margin-bottom:4px;">Add Document to Library</h1>
      <p style="font-size:13.5px; color:var(--text-secondary); margin:0;">
        Scrape a municipality website or enter a custom URL to extract and
        index coastal resilience documents.
      </p>
    </div>
    """,
        unsafe_allow_html=True,
    )

    st.markdown(
        "<div style='padding:1.5rem 0 0;'></div>",
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div style="background:var(--bg-card); border:0.5px solid var(--border-color); border-radius:12px; padding:1.25rem 1.5rem; margin-bottom:1rem;">',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p style="font-size:11px; font-weight:500; text-transform:uppercase; letter-spacing:0.06em; color:var(--text-muted); margin-bottom:1rem;">Source</p>',
        unsafe_allow_html=True,
    )

    if "preset_municipality" not in st.session_state:
        st.session_state.preset_municipality = None

    muni_keys = list(SC_COASTAL_SITES.keys())
    default_idx = (
        muni_keys.index(st.session_state.preset_municipality)
        if st.session_state.preset_municipality in muni_keys
        else 0
    )

    selected_municipality = st.selectbox(
        "Select a municipality",
        muni_keys,
        index=default_idx,
    )

    # Clear the preset after it's been consumed
    st.session_state.preset_municipality = None

    st.markdown(
        '<p style="text-align:center; color:#444; font-size:12px; margin:8px 0;">— or —</p>',
        unsafe_allow_html=True,
    )
    custom_url = st.text_input(
        "Custom URL",
        placeholder="e.g., https://www.charleston-sc.gov/resilience",
        label_visibility="visible",
    )
    st.markdown("</div>", unsafe_allow_html=True)

    with st.expander("Advanced scraper settings"):
        col1, col2 = st.columns(2)
        with col1:
            llm_model = st.text_input("Ollama model name", "llama3.2:latest")
            max_depth = st.slider("Scraping depth", 1, 5, 3)
        with col2:
            request_delay = st.slider("Request delay (seconds)", 0.1, 5.0, 1.0, 0.1)
            relevance_threshold = st.slider("Relevance threshold", 0.0, 1.0, 0.01, 0.01)

    st.markdown('<div class="search-btn-col">', unsafe_allow_html=True)
    start = st.button("Start Scraping & Analysis", use_container_width=True, type="primary", key="start_scrape")
    st.markdown("</div>", unsafe_allow_html=True)

    if start:
        stop_container = st.empty()
        with stop_container:
            st.button("Stop Scraping", key="stop_scrape_btn_active", type="primary", use_container_width=True)

        st.session_state.scrape_results = []
        target_url = custom_url.strip() if custom_url.strip() else SC_COASTAL_SITES[selected_municipality]

        network = RetrievalSummarizationNetwork(
            llm_model=llm_model,
            scraper_max_depth=max_depth,
            scraper_request_delay=request_delay,
            relevance_threshold=relevance_threshold,
        )

        try:
            progress_bar = st.progress(0, text="Starting scrape…")
        except TypeError:
            progress_bar = st.progress(0)
        status_text = st.empty()

        try:
            with st.spinner(f"Scraping {target_url}…"):
                network.scrape_municipality(
                    municipality_name=selected_municipality,
                    base_url=target_url,
                    auto_process=True,
                    st=st,
                    status_text=status_text,
                    progress_bar=progress_bar,
                )
                st.session_state.scrape_results = network.results
        finally:
            stop_container.empty()

        if st.session_state.scrape_results:
            st.markdown(
                f'<div style="background:rgba(106,191,138,0.1); border:0.5px solid #6abf8a; border-radius:8px; '
                f'padding:12px 16px; font-size:14px; color:#6abf8a; margin-top:1rem; font-weight:500;">'
                f"Found and processed {len(st.session_state.scrape_results)} relevant documents. "
                f"They are now searchable in the library.</div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div style="background:rgba(201,146,74,0.1); border:0.5px solid #c9924a; border-radius:8px; '
                f'padding:12px 16px; font-size:14px; color:#c9924a; margin-top:1rem; font-weight:500;">'
                f"No relevant documents were found. Try adjusting the relevance threshold or scraping depth.</div>",
                unsafe_allow_html=True,
            )

        st.markdown(
            f'<p style="font-size:11px; font-weight:500; text-transform:uppercase; '
            'letter-spacing:0.07em; color:var(--text-muted); padding:1.25rem 0 0.75rem;">Last Scrape Results</p>',
            unsafe_allow_html=True,
        )
        doc_type_colors = {
            "report": ("#0d2a40", "#7ab3e0"),
            "plan": ("#0d2a40", "#7ab3e0"),
            "annual_report": ("#0d2a1a", "#6abf8a"),
            "meeting_minutes": ("#0d2a1a", "#6abf8a"),
            "ordinance": ("#2a1e0d", "#c9924a"),
            "agenda": ("#2a1e0d", "#c9924a"),
            "risk": ("#2a150d", "#d97a5a"),
        }

        def get_colors(doc_type):
            key = (doc_type or "").lower()
            for k, v in doc_type_colors.items():
                if k in key:
                    return v
            return "#0d2a40", "#7ab3e0"

        cols = st.columns(3)
        for i, result in enumerate(st.session_state.scrape_results):
            bg, fg = get_colors(result.doc_type)
            filename = _he(result.url.split("/")[-1] or "Document")
            raw_s = result.summary or ""
            summ_short = _he(raw_s[:120])
            ell = "…" if len(raw_s) > 120 else ""
            score_pct = int(min((result.relevance_score or 0) * 100, 100))
            dtype_label = _he(
                (result.doc_type or "Unknown").replace("_", " ").title()
            )
            muni_e = _he(result.municipality or "")
            with cols[i % 3]:
                st.markdown(
                    f"""<div style="background:var(--bg-card); border:0.5px solid var(--border-color);
                            border-radius:12px; padding:1rem 1.25rem; margin-bottom:8px;">
  <span style="font-size:11px; font-weight:500; padding:3px 10px;
               border-radius:20px; background:{bg}; color:{fg};
               display:inline-block; margin-bottom:8px;">
    {dtype_label}
  </span>
  <p style="font-size:13.5px; font-weight:500; color:var(--text-main);
            line-height:1.4; margin:0 0 4px;">{filename}</p>
  <p style="font-size:12px; color:var(--text-secondary); line-height:1.5; margin:0 0 8px;">
    {summ_short}{ell}
  </p>
  <div style="height:3px; background:var(--border-color); border-radius:2px;">
    <div style="height:3px; background:var(--accent-blue); border-radius:2px;
                width:{score_pct}%;"></div>
  </div>
  <p style="font-size:11px; color:var(--text-muted); margin:3px 0 8px;">
    Relevance score: {result.relevance_score:.2f}
  </p>
  <div style="font-size:11.5px; color:var(--text-muted);">{muni_e}</div>
</div>""",
                    unsafe_allow_html=True,
                )

                with st.expander("View details"):
                    st.markdown(f"**Summary:** {result.summary}")
                    if result.key_findings:
                        st.markdown("**Key Findings:**")
                        for f in result.key_findings:
                            st.markdown(f"- {f}")
                    st.markdown(f"[Source]({result.url})")


def _get_municipality_stats() -> list[dict]:
    """
    Returns a list of dicts, one per municipality in SC_COASTAL_SITES.
    Each dict has: name, url, doc_count, scraped (bool), last_scraped (str|None)
    """
    # Get doc counts per municipality from DB
    try:
        from rag_code.database import get_db_connection
        with get_db_connection() as conn:
            rows = conn.execute(
                "SELECT municipality, COUNT(*) as cnt, MAX(scraped_at) as last "
                "FROM documents GROUP BY municipality"
            ).fetchall()
        db_counts = {row["municipality"]: (row["cnt"], row["last"]) for row in rows}
    except Exception:
        db_counts = {}

    result = []
    for name, url in SC_COASTAL_SITES.items():
        count, last = db_counts.get(name, (0, None))
        # Format last_scraped date nicely if present
        if last:
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(str(last))
                last_str = dt.strftime("%b %-d %Y")
            except Exception:
                last_str = str(last)[:10]
        else:
            last_str = None

        result.append({
            "name": name,
            "url": url,
            "doc_count": count,
            "scraped": count > 0,
            "last_scraped": last_str,
        })

    # Sort: scraped first (by doc count desc), then unscraped alphabetically
    scraped   = sorted([m for m in result if m["scraped"]],     key=lambda x: -x["doc_count"])
    unscraped = sorted([m for m in result if not m["scraped"]], key=lambda x: x["name"])
    return scraped + unscraped


def _render_municipality_card(muni: dict, max_docs: int):
    pct       = int((muni["doc_count"] / max_docs) * 100) if max_docs else 0
    dot_color = "#6abf8a" if muni["scraped"] else "#444444"
    status_text = (
        f"Last scraped {muni['last_scraped']}" if muni["scraped"]
        else "Not yet scraped"
    )

    st.markdown(f"""
    <div style="background:var(--bg-card); border:0.5px solid var(--border-color); border-radius:12px;
                padding:1rem 1.25rem; margin-bottom:8px;">
      <div style="display:flex; align-items:flex-start; justify-content:space-between;
                  margin-bottom:10px;">
        <div>
          <div style="font-size:13.5px; font-weight:500; color:var(--text-main);">
            {muni['name']}
          </div>
        </div>
        <div style="text-align:right;">
          <div style="font-size:20px; font-weight:500; color:var(--text-main);">
            {muni['doc_count']}
          </div>
          <div style="font-size:10.5px; color:var(--text-muted);">docs</div>
        </div>
      </div>
      <div style="height:2px; background:var(--border-color); border-radius:2px; margin-bottom:8px;">
        <div style="height:2px; background:var(--accent-blue); border-radius:2px;
                    width:{pct}%;"></div>
      </div>
      <div style="display:flex; justify-content:space-between; align-items:center;
                  font-size:11px; color:var(--text-muted);">
        <span>
          <span style="display:inline-block; width:6px; height:6px; border-radius:50%;
                       background:{dot_color}; margin-right:5px; vertical-align:middle;">
          </span>
          {status_text}
        </span>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # "Add docs" button navigates to Add Document page with municipality pre-selected
    st.markdown('<div class="muni-btn-row">', unsafe_allow_html=True)
    if st.button("Add docs", key=f"muni_scrape_{muni['name']}", use_container_width=True):
        st.session_state.page = "add_document"
        st.session_state.preset_municipality = muni["name"]
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)


def render_municipalities_page():
    # ── Hero ──────────────────────────────────────────────────────────────────
    st.markdown("""
    <div style="background:var(--bg-secondary); border-bottom:0.5px solid var(--border-color);
                padding:2rem 2rem 1.5rem;">
      <h1 style="font-family:'Playfair Display',serif; font-size:26px;
                 color:var(--text-main); margin-bottom:4px;">Municipalities</h1>
      <p style="font-size:13.5px; color:var(--text-secondary); margin:0;">
        Overview of all SC coastal municipalities — documents indexed,
        scrape status, and quick access.
      </p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div style='padding-top:1.5rem;'></div>", unsafe_allow_html=True)

    # ── Load data ─────────────────────────────────────────────────────────────
    all_munis = _get_municipality_stats()
    total      = len(all_munis)
    scraped    = [m for m in all_munis if m["scraped"]]
    total_docs = sum(m["doc_count"] for m in all_munis)

    # ── Summary stat cards ────────────────────────────────────────────────────
    s1, s2, s3, s4 = st.columns(4)
    for col, label, value, color in [
        (s1, "Total municipalities", total,            "var(--text-main)"),
        (s2, "Scraped",             len(scraped),      "#6abf8a"),
        (s3, "Total documents",     total_docs,        "var(--text-main)"),
        (s4, "Not yet scraped",     total-len(scraped),"var(--text-muted)"),
    ]:
        with col:
            st.markdown(f"""
            <div style="background:var(--bg-card); border:0.5px solid var(--border-color);
                        border-radius:8px; padding:1rem; margin-bottom:1rem;">
              <div style="font-size:11px; color:var(--text-muted); text-transform:uppercase;
                          letter-spacing:0.06em; margin-bottom:6px;">{label}</div>
              <div style="font-size:22px; font-weight:500; color:{color};">{value}</div>
            </div>
            """, unsafe_allow_html=True)

    # ── Filter controls ───────────────────────────────────────────────────────
    f1, f2 = st.columns([4, 1])
    with f1:
        q = st.text_input(
            "filter",
            placeholder="Filter municipalities…",
            label_visibility="collapsed",
            key="muni_page_search",
        )
    with f2:
        status_filter = st.selectbox(
            "status",
            ["All statuses", "Scraped", "Not yet scraped"],
            label_visibility="collapsed",
            key="muni_status_filter",
        )

    # Apply filters
    filtered = all_munis
    if q:
        filtered = [m for m in filtered if q.lower() in m["name"].lower()]
    if status_filter == "Scraped":
        filtered = [m for m in filtered if m["scraped"]]
    elif status_filter == "Not yet scraped":
        filtered = [m for m in filtered if not m["scraped"]]

    # ── Section label ─────────────────────────────────────────────────────────
    n = len(filtered)
    st.markdown(
        f'<p style="font-size:11px; font-weight:500; text-transform:uppercase; '
        f'letter-spacing:0.07em; color:#555; margin-bottom:12px;">'
        f'{n} MUNICIPALIT{"Y" if n==1 else "IES"}</p>',
        unsafe_allow_html=True
    )

    # ── Municipality card grid ─────────────────────────────────────────────────
    if not filtered:
        st.markdown("""
        <div style="text-align:center; padding:4rem; color:#555; font-size:14px;">
          No municipalities match your filter.
        </div>
        """, unsafe_allow_html=True)
        return

    max_docs = max((m["doc_count"] for m in all_munis), default=1) or 1
    COLS = 3
    rows = [filtered[i:i+COLS] for i in range(0, len(filtered), COLS)]

    for row in rows:
        cols = st.columns(COLS)
        for col, muni in zip(cols, row):
            with col:
                _render_municipality_card(muni, max_docs)


def render_settings_page() -> None:
    if "settings_tab" not in st.session_state:
        st.session_state.settings_tab = "rag"

    # Layout for Settings page: sidebar column and main content column
    left_col, right_col = st.columns([1, 3.5])

    with left_col:
        st.markdown('<p style="font-size:10.5px; font-weight:600; color:var(--text-muted); text-transform:uppercase; letter-spacing:0.06em; margin-bottom:8px;">GENERAL</p>', unsafe_allow_html=True)
        
        tab_bg = "transparent"
        tab_color = "var(--text-nav)"
        
        # We simulate the visual 'active' state via CSS classes or Streamlit button types.
        rag_type = "primary" if st.session_state.settings_tab == "rag" else "secondary"
        if st.button("RAG Model", use_container_width=True, type=rag_type, key="tab_rag"):
            st.session_state.settings_tab = "rag"
            st.rerun()
            
        scraper_type = "primary" if st.session_state.settings_tab == "scraper" else "secondary"
        if st.button("Scraper Defaults", use_container_width=True, type=scraper_type, key="tab_scraper"):
            st.session_state.settings_tab = "scraper"
            st.rerun()
            
        muni_type = "primary" if st.session_state.settings_tab == "munis" else "secondary"
        if st.button("Municipalities", use_container_width=True, type=muni_type, key="tab_munis"):
            st.session_state.settings_tab = "munis"
            st.rerun()

        appearance_type = "primary" if st.session_state.settings_tab == "appearance" else "secondary"
        if st.button("Appearance", use_container_width=True, type=appearance_type, key="tab_appearance"):
            st.session_state.settings_tab = "appearance"
            st.rerun()

        st.markdown('<div style="height:25px;"></div>', unsafe_allow_html=True)
        st.markdown('<p style="font-size:10.5px; font-weight:600; color:var(--text-muted); text-transform:uppercase; letter-spacing:0.06em; margin-bottom:8px;">SYSTEM</p>', unsafe_allow_html=True)
        
        lib_type = "primary" if st.session_state.settings_tab == "lib" else "secondary"
        if st.button("Library & Storage", use_container_width=True, type=lib_type, key="tab_lib"):
            st.session_state.settings_tab = "lib"
            st.rerun()
            
        about_type = "primary" if st.session_state.settings_tab == "about" else "secondary"
        if st.button("About & Credits", use_container_width=True, type=about_type, key="tab_about"):
            st.session_state.settings_tab = "about"
            st.rerun()

    with right_col:
        if st.session_state.settings_tab == "rag":
            st.markdown(
                """
                <h1 style="font-family:'DM Sans', sans-serif; font-size:20px; font-weight:500; color:var(--text-main); margin-bottom:4px;">RAG Model</h1>
                <p style="font-size:14px; color:var(--text-secondary); margin-bottom:24px;">
                  Configure the language model used to analyze and index scraped documents.
                </p>
                """, unsafe_allow_html=True
            )
            
            with st.container(border=True):
                st.markdown('<p style="font-size:11px; font-weight:600; text-transform:uppercase; color:var(--text-muted); margin-bottom:12px; letter-spacing:0.05em;">MODEL</p>', unsafe_allow_html=True)
                
                # Text Input
                temp_llm = st.text_input(
                    "Ollama model name", 
                    value=st.session_state.get("settings_llm", "llama3.2:latest"),
                    key="input_llm"
                )
                
                # Slider with custom label layout using markdown
                st.markdown(
                    '<p style="font-size:13.5px; color:var(--text-main); margin-bottom:0; margin-top:12px;">'
                    f'Relevance threshold <span style="color:var(--text-muted);">— minimum score for a document to be indexed</span></p>', 
                    unsafe_allow_html=True
                )
                temp_threshold = st.slider(
                    "Relevance Threshold", 
                    min_value=0.0, max_value=1.0, 
                    value=float(st.session_state.get("settings_threshold", 0.01)), 
                    step=0.01,
                    label_visibility="collapsed",
                    key="input_threshold"
                )

            st.markdown('<div style="height:10px;"></div>', unsafe_allow_html=True)
            
            with st.container(border=True):
                st.markdown('<p style="font-size:11px; font-weight:600; text-transform:uppercase; color:var(--text-muted); margin-bottom:12px; letter-spacing:0.05em;">BEHAVIOR</p>', unsafe_allow_html=True)
                
                # Toggle 1
                c1, c2 = st.columns([5, 1])
                with c1:
                    st.markdown("""
                    <div style="margin-top:2px;">
                        <span style="font-size:14.5px; font-weight:500; color:var(--text-main);">Auto-tag documents on ingest</span><br>
                        <span style="font-size:13px; color:var(--text-secondary);">Automatically assign topic tags when a document is added</span>
                    </div>
                    """, unsafe_allow_html=True)
                with c2:
                    st.toggle("auto_tag", value=True, label_visibility="collapsed", key="toggle_autotag")
                
                st.markdown("<hr style='border:none; border-top:1px solid var(--border-color); margin:16px 0;'>", unsafe_allow_html=True)
                
                # Toggle 2
                c3, c4 = st.columns([5, 1])
                with c3:
                    st.markdown("""
                    <div style="margin-top:2px;">
                        <span style="font-size:14.5px; font-weight:500; color:var(--text-main);">Re-analyze on model change</span><br>
                        <span style="font-size:13px; color:var(--text-secondary);">Re-run analysis on all documents when the model is updated</span>
                    </div>
                    """, unsafe_allow_html=True)
                with c4:
                    st.toggle("reanalyze", value=False, label_visibility="collapsed", key="toggle_reanalyze")

            # Actions row
            st.markdown('<div style="height:15px;"></div>', unsafe_allow_html=True)
            ac1, ac2, ac3 = st.columns([2.5, 1, 1.2])
            with ac2:
                if st.button("Cancel", use_container_width=True):
                    st.rerun()
            with ac3:
                if st.button("Save changes", type="primary", use_container_width=True):
                    st.session_state.settings_llm = temp_llm
                    st.session_state.settings_threshold = temp_threshold
                    st.toast("Settings saved successfully!")
                    st.rerun()
                    
        elif st.session_state.settings_tab == "appearance":
            st.markdown(
                """
                <h1 style="font-family:'DM Sans', sans-serif; font-size:20px; font-weight:500; color:var(--text-main); margin-bottom:4px;">Appearance</h1>
                <p style="font-size:14px; color:var(--text-secondary); margin-bottom:24px;">
                  Customize the look and feel of the coastal resilience dashboard.
                </p>
                """, unsafe_allow_html=True
            )
            
            with st.container(border=True):
                st.markdown('<p style="font-size:11px; font-weight:600; text-transform:uppercase; color:var(--text-muted); margin-bottom:12px; letter-spacing:0.05em;">THEME</p>', unsafe_allow_html=True)
                
                temp_mode = st.selectbox(
                    "Display Mode",
                    options=["Dark", "Light"],
                    index=0 if st.session_state.settings_appearance == "Dark" else 1,
                    key="input_appearance"
                )
            
            st.markdown('<div style="height:15px;"></div>', unsafe_allow_html=True)
            ac1, ac2, ac3 = st.columns([2.5, 1, 1.2])
            with ac2:
                if st.button("Cancel", use_container_width=True, key="cancel_app"):
                    st.rerun()
            with ac3:
                if st.button("Save changes", type="primary", use_container_width=True, key="save_app"):
                    st.session_state.settings_appearance = temp_mode
                    st.toast(f"Appearance updated to {temp_mode} mode!")
                    st.rerun()
                    
        else:
            st.markdown(
                f"""
                <h1 style="font-family:'DM Sans', sans-serif; font-size:20px; font-weight:500; color:var(--text-main); margin-bottom:4px;">{st.session_state.settings_tab.title()}</h1>
                <p style="font-size:14px; color:var(--text-secondary); margin-bottom:24px;">
                  Options for this module are currently under construction.
                </p>
                """, unsafe_allow_html=True
            )


if "page" not in st.session_state:
    st.session_state.page = "search"
if "search_query" not in st.session_state:
    st.session_state.search_query = ""
if "muni_filter" not in st.session_state:
    st.session_state.muni_filter = "All Municipalities"
if "muni_page_search" not in st.session_state:
    st.session_state.muni_page_search = ""
if "preset_municipality" not in st.session_state:
    st.session_state.preset_municipality = None
if "open_card" not in st.session_state:

    st.session_state.open_card = None
if "scrape_results" not in st.session_state:
    st.session_state.scrape_results = []

database.initialize_database()

st.markdown('<div class="top-nav-anchor"></div>', unsafe_allow_html=True)
# Stretch logo block to push things across, but leave them distributed nicely alongside the title
logo_col, c1, c2, c3, c4 = st.columns([4.2, 1.2, 1.3, 1.5, 0.45])

with logo_col:
    st.markdown(
        f"""
        <div style="display:flex; align-items:center; gap:12px; margin-top:-5px;">
          <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
            <circle cx="14" cy="14" r="14" fill="var(--bg-input)"/>
            <path d="M4 18 Q8 12 14 15 Q20 18 24 11" stroke="var(--accent-text)" stroke-width="2"
                  fill="none" stroke-linecap="round"/>
            <path d="M4 21 Q10 16 16 19 Q20 21 24 15" stroke="var(--accent-blue-hover)" stroke-width="1.5"
                  fill="none" stroke-linecap="round"/>
          </svg>
          <div>
            <span style="font-family:'Playfair Display',serif; font-size:19px;
                         font-weight:600; color:var(--text-main);">SC-Coasts</span>
            <small style="display:block; font-size:11.5px; color:var(--text-muted); margin-top:-2px;">
              Coastal Resilience Analyzer
            </small>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

pages = ["search", "municipalities", "add_document", "settings"]
labels = ["Search", "Municipalities", "Add Document", "⚙"]
nav_cols = [c1, c2, c3, c4]

for col, page_id, label in zip(nav_cols, pages, labels):
    btn_type = "primary" if st.session_state.page == page_id else "secondary"
    with col:
        if st.button(label, key=f"nav_{page_id}", use_container_width=True, type=btn_type):
            st.session_state.page = page_id
            st.session_state.open_card = None
            st.rerun()

if st.session_state.page == "search":
    render_search_page()
elif st.session_state.page == "add_document":
    render_add_document_page()
elif st.session_state.page == "municipalities":
    render_municipalities_page()
elif st.session_state.page == "settings":
    render_settings_page()
else:
    st.markdown(
        '<div style="padding:4rem; text-align:center; color:#555; font-size:14px;">Coming soon</div>',
        unsafe_allow_html=True,
    )
