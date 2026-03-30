import os
import json
import re
import time
from typing import Optional
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import logging
import hashlib
import io

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings

# Web scraper dependencies
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import pdfplumber

import streamlit as st
from PIL import Image

from rag_code.ret_summ import (
    SC_COASTAL_SITES,
    RetrievalSummarizationNetwork,
    ScrapedDocument,
    RetrievalResult,
)




# Target Website Registry 



# Data classes 






















# Streamlit UI Components
# In your main app.py, you would integrate these functions.

def display_document_card(doc: RetrievalResult):
    st.subheader(doc.url.split('/')[-1])  # Display filename or last part of URL
    st.write(f"**Municipality:** {doc.municipality}")
    st.write(f"**Document Type:** {doc.doc_type}")
    st.write(f"**Relevance Score:** {doc.relevance_score:.2f}")
    
    with st.expander("Summary & Key Findings"):
        st.write(doc.summary)
        st.write("**Key Findings:**")
        for finding in doc.key_findings:
            st.markdown(f"- {finding}")

    with st.expander("Matched Keywords & Categories"):
        st.write(f"**Keywords:** {', '.join(doc.matched_keywords)}")
        st.write(f"**Categories:** {', '.join(doc.matched_categories)}")

    st.markdown(f"[View Original Document]({doc.url})", unsafe_allow_html=True)
    st.markdown("---")


from rag_code import database

def main():
    st.set_page_config(layout="wide", page_title="SC Coastal Document RAG")
    database.initialize_database()

    # Initialize session state variables
    if 'scrape_results' not in st.session_state:
        st.session_state.scrape_results = []
    if 'search_results' not in st.session_state:
        st.session_state.search_results = []

    # Custom CSS for dark theme
    st.markdown("""
    <style>
    .main { 
        background-color: #121212;
        color: #e0e0e0; 
    }
    .stTextInput>div>div>input { 
        background-color: #1e1e1e; 
        color: #e0e0e0; 
        border: 1px solid #3b82f6;
    }
    .stButton>button { 
        background-color: #3b82f6; 
        color: white; 
        border: none; 
        padding: 10px 20px; 
        border-radius: 5px; 
        cursor: pointer;
    }
    .stButton>button:hover { 
        background-color: #2563eb;
    }
    .stSelectbox>div>div>div { 
        background-color: #1e1e1e; 
        color: #e0e0e0; 
        border: 1px solid #3b82f6;
    }
    .stExpander { 
        background-color: #1e1e1e; 
        border: 1px solid #3b82f6; 
        border-radius: 5px; 
        margin-bottom: 10px;
    }
    h1, h2, h3, h4, h5, h6 { 
        color: #e0e0e0;
    }
    </style>
    """, unsafe_allow_html=True)

    st.title("🌊 SC-Coasts: Coastal Resilience Document Analyzer")

    # --- Sidebar Controls ---
    st.sidebar.title("Configuration")
    selected_municipality = st.sidebar.selectbox(
        "Select Municipality (for scraping)", 
        list(SC_COASTAL_SITES.keys())
    )
    custom_url = st.sidebar.text_input(
        "Or enter a custom URL to scrape", 
        placeholder="e.g., https://www.charleston-sc.gov/AgendaCenter"
    )
    st.sidebar.subheader("RAG Model Settings")
    llm_model = st.sidebar.text_input("Ollama Model Name", "llama3")
    st.sidebar.subheader("Scraper Settings")
    max_depth = st.sidebar.slider("Scraping Depth", 1, 5, 2)
    request_delay = st.sidebar.slider("Request Delay (seconds)", 0.1, 5.0, 1.0)
    relevance_threshold = st.sidebar.slider("Relevance Threshold", 0.0, 1.0, 0.0, 0.01)

    # --- Main App Tabs ---
    tab1, tab2 = st.tabs(["🔍 Search Library", "➕ Add to Library (Scrape)"])

    with tab1:
        st.header("Search the Document Library")
        
        search_query = st.text_input("Enter keywords to search", key="search_query")
        
        all_munis = ["All"] + database.get_all_municipalities()
        search_municipality = st.selectbox("Filter by Municipality", options=all_munis, key="search_municipality")
        
        if st.button("Search Library"):
            if not search_query:
                st.warning("Please enter a search query.")
            else:
                with st.spinner("Searching..."):
                    results = database.search_documents(search_term=search_query, municipality=search_municipality)
                    st.session_state.search_results = results
                st.success(f"Found {len(st.session_state.search_results)} matching documents.")

        if 'search_results' in st.session_state:
            st.write("---_**## Search Results**_---")
            if st.session_state.search_results:
                for result in st.session_state.search_results:
                    display_document_card(result)
            else:
                st.info("No documents matched your search criteria.")

    with tab2:
        st.header("Add New Documents to the Library")
        st.info("Use the sidebar to configure and start the web scraper. Results will appear below.")

        if st.button("Start Scraping & Analysis"):
            st.session_state.scrape_results = []
            st.session_state.scraped_documents = []

            network = RetrievalSummarizationNetwork(
                llm_model=llm_model,
                scraper_max_depth=max_depth,
                scraper_request_delay=request_delay,
                relevance_threshold=relevance_threshold
            )

            target_url = custom_url if custom_url else SC_COASTAL_SITES[selected_municipality]
            
            progress_bar = st.progress(0, "Starting scrape...")
            status_text = st.empty()
            
            with st.spinner(f"Scraping and analyzing {target_url}..."):
                scraped_docs = network.scrape_municipality(
                    municipality_name=selected_municipality, 
                    base_url=target_url, 
                    auto_process=True,
                    st=st,
                status_text=status_text,
                progress_bar=progress_bar
                )
                st.session_state.scrape_results = network.results
                st.session_state.scraped_documents = scraped_docs
            
            if st.session_state.scrape_results:
                st.success(f"Found and processed {len(st.session_state.scrape_results)} relevant documents.")
            else:
                st.warning("No new relevant documents were found.")
        
        if 'scrape_results' in st.session_state and st.session_state.scrape_results:
            st.markdown("---_**## Last Scrape Results**_---")
    for result in st.session_state.scrape_results:
        display_document_card(result)

def display_document_card(doc):
    """Displays a single document in a card format."""
    if isinstance(doc, dict):
        from types import SimpleNamespace
        doc = SimpleNamespace(**doc)

    st.subheader(doc.url.split('/')[-1]) # Use filename as title
    
    with st.expander("View Details"):
        st.markdown(f"**Municipality:** {doc.municipality}")
        st.markdown(f"**Document Type:** {doc.doc_type}")
        st.markdown(f"**Relevance Score:** {doc.relevance_score:.2f}")
        
        st.markdown("**Summary:**")
        st.write(doc.summary)
        
        st.markdown("**Key Findings:**")
        # Handle both JSON string and list for key_findings
        try:
            import json
            findings = json.loads(doc.key_findings) if isinstance(doc.key_findings, str) else doc.key_findings
            if findings:
                for finding in findings:
                    st.markdown(f"- {finding}")
            else:
                st.write("No key findings were extracted.")
        except (json.JSONDecodeError, TypeError):
            st.write(doc.key_findings or "No key findings were extracted.")

        st.markdown(f"[Link to Document]({doc.url})", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
