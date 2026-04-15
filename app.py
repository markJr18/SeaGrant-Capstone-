
import streamlit as st
from datetime import datetime

# Use absolute imports, which will work because of main.py
from rag_code import database
from rag_code.ret_summ import (
    SC_COASTAL_SITES,
    RetrievalSummarizationNetwork,
    RetrievalResult
)

def main():
    st.set_page_config(layout="wide", page_title="SC Coastal Document RAG")
    database.initialize_database()
    current_year = datetime.now().year

    if 'search_results' not in st.session_state:
        st.session_state.search_results = []

    st.title("🌊 SC-Coasts: Coastal Resilience Document Analyzer")

    # --- Sidebar ---
    st.sidebar.title("Configuration")
    selected_municipality = st.sidebar.selectbox("Select Municipality", list(SC_COASTAL_SITES.keys()))
    target_year = st.sidebar.number_input("Target Year", min_value=2000, max_value=current_year + 1, value=current_year)
    request_delay = st.sidebar.slider("Request Delay (s)", 0.5, 10.0, 2.5, 0.5)
    max_depth = st.sidebar.slider("Scraping Depth", 1, 5, 2)
    relevance_threshold = st.sidebar.slider("Relevance Threshold", 0.0, 1.0, 0.01, 0.01)
    llm_model = st.sidebar.text_input("Ollama Model", "llama3")

    # --- Main Tabs ---
    tab1, tab2 = st.tabs(["🔍 Search Library", "➕ Add to Library"])

    with tab1:
        st.header("Search the Document Library")
        search_query = st.text_input("Enter keywords to search")
        all_munis = ["All"] + database.get_all_municipalities()
        search_municipality = st.selectbox("Filter by Municipality", options=all_munis)
        
        if st.button("Search Library"):
            if not search_query: st.warning("Please enter a search query.")
            else:
                with st.spinner("Searching..."):
                    st.session_state.search_results = database.search_documents(search_query, search_municipality)
                st.success(f"Found {len(st.session_state.search_results)} matching documents.")

        if st.session_state.search_results:
            st.markdown("---_**## Search Results**_---")
            for doc in st.session_state.search_results:
                display_document_card(doc)

    with tab2:
        st.header("Add New Documents to the Library")
        if st.button("Start Scraping & Analysis"):
            network = RetrievalSummarizationNetwork(
                relevance_threshold=relevance_threshold,
                llm_model=llm_model,
                scraper_max_depth=max_depth,
                scraper_request_delay=request_delay
            )
            target_url = SC_COASTAL_SITES[selected_municipality]
            status_text = st.empty()
            progress_bar = st.progress(0)
            
            with st.spinner(f"Scraping for {target_year} & {target_year - 1}..."):
                status_text.text(f"Scraping documents for {target_year}...")
                network.scrape_municipality(selected_municipality, target_url, target_year, True, st, status_text, progress_bar)
                
                status_text.text(f"Scraping documents for {target_year - 1}...")
                network.scrape_municipality(selected_municipality, target_url, target_year - 1, True, st, status_text, progress_bar)
            
            st.session_state.scrape_results = network.results
            if network.results:
                st.success(f"Found and processed {len(network.results)} relevant documents.")
            else:
                st.warning("No new relevant documents were found.")

        if 'scrape_results' in st.session_state and st.session_state.scrape_results:
            st.markdown("---_**## Last Scrape Results**_---")
            for result in st.session_state.scrape_results:
                display_document_card(result)

def display_document_card(doc):
    if isinstance(doc, dict):
        from types import SimpleNamespace
        doc = SimpleNamespace(**doc)

    st.subheader(doc.url.split('/')[-1])
    with st.expander("View Details"):
        st.markdown(f"**Municipality:** {doc.municipality}")
        st.markdown(f"**Summary:** {doc.summary}")
        try:
            key_findings = json.loads(doc.key_findings) if isinstance(doc.key_findings, str) else doc.key_findings
            if key_findings:
                st.markdown("**Key Findings:**")
                for finding in key_findings:
                    st.markdown(f"- {finding}")
        except (json.JSONDecodeError, TypeError):
            pass # No key findings to display
        st.markdown(f"[Link to Document]({doc.url})")

if __name__ == "__main__":
    main()
