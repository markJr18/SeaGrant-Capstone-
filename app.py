import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd

# Set page config
st.set_page_config(
    page_title="SeaGrant Wetland Preservation",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for Dark Gray Theme
st.markdown("""
    <style>
    .stApp {
        background-color: #121212;
        color: #e0e0e0;
    }
    h1 {
        color: #3b82f6 !important;
        text-align: center;
        border-bottom: 2px solid #3b82f6;
        padding-bottom: 1rem;
    }
    .stTextInput > div > div > input {
        background-color: #1e1e1e;
        color: #e0e0e0;
        border: 1px solid #333;
    }
    .report-card {
        background-color: #1e1e1e;
        border: 1px solid #333;
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
        transition: all 0.3s ease;
    }
    .report-card:hover {
        border-color: #3b82f6;
        transform: translateY(-5px);
    }
    .card-meta {
        display: flex;
        justify-content: space-between;
        font-size: 0.8rem;
        margin-bottom: 0.75rem;
    }
    .report-type {
        color: #3b82f6;
        font-weight: 600;
        text-transform: uppercase;
    }
    .report-date {
        color: #666;
    }
    .report-title {
        color: #fff;
        font-size: 1.25rem;
        margin-bottom: 0.5rem;
        font-weight: 600;
    }
    .report-summary {
        color: #b0b0b0;
        font-size: 0.95rem;
        margin-bottom: 1rem;
    }
    .topic-tag {
        display: inline-block;
        font-size: 0.75rem;
        background-color: #2d2d2d;
        color: #94a3b8;
        padding: 0.15rem 0.5rem;
        border-radius: 4px;
        border: 1px solid #444;
        margin-right: 0.4rem;
        margin-bottom: 0.4rem;
    }
    .view-link {
        color: #60a5fa !important;
        text-decoration: none;
        font-weight: 600;
        display: inline-block;
        margin-top: 1rem;
    }
    .view-link:hover {
        text-decoration: underline;
    }
    </style>
""", unsafe_allow_html=True)

# Scraper Function
@st.cache_data(ttl=3600)
def scrape_reports():
    url = 'https://www.scseagrant.org/publications-search/'
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        reports = []
        table_rows = soup.select('table tbody tr')
        
        for i, row in enumerate(table_rows):
            cols = row.find_all('td')
            if len(cols) >= 5:
                title_link = cols[0].find('a')
                title = title_link.text.strip() if title_link else ""
                href = title_link['href'] if title_link else ""
                
                full_url = href if href.startswith('http') else f"https://www.scseagrant.org{href}"
                
                reports.append({
                    "id": i,
                    "title": title,
                    "summary": cols[1].text.strip(),
                    "date": cols[2].text.strip(),
                    "type": cols[3].text.strip(),
                    "topics": cols[4].text.strip(),
                    "url": full_url
                })
        return reports
    except Exception as e:
        st.error(f"Error scraping data: {e}")
        return []

# App Header
st.title("SeaGrant Wetland Preservation")
st.markdown("<p style='text-align: center; color: #b0b0b0;'>South Carolina Coastal Wetlands Information Portal</p>", unsafe_allow_html=True)

# Search and Keywords
col1, col2 = st.columns([2, 1])
with col1:
    search_term = st.text_input("Search documents and reports...", placeholder="Type to filter...")

keywords = ['Wetland', 'Coastal', 'Resilience', 'Erosion', 'Water Quality', 'Oyster', 'Flooding', 'Stormwater']

# Keyword Chips (using columns for horizontal layout)
st.write("Popular Keywords:")
chip_cols = st.columns(len(keywords))
selected_keyword = st.session_state.get('selected_keyword', None)

for i, keyword in enumerate(keywords):
    if chip_cols[i].button(keyword, key=f"btn_{keyword}", use_container_width=True):
        st.session_state.selected_keyword = keyword
        selected_keyword = keyword

# Main Content
if selected_keyword or search_term:
    with st.spinner("Fetching real-time SC Coastal documents..."):
        all_reports = scrape_reports()
        
        # Filter logic
        query = (search_term or selected_keyword).lower()
        filtered_reports = [
            r for r in all_reports 
            if query in r['title'].lower() or 
               query in r['summary'].lower() or 
               query in r['topics'].lower()
        ]
        
    if filtered_reports:
        st.markdown(f"### Real-Time Documents for: {selected_keyword or search_term} <span style='font-size: 0.8rem; background: #3b82f6; padding: 2px 8px; border-radius: 10px;'>{len(filtered_reports)} found</span>", unsafe_allow_html=True)
        
        # Display as grid (3 columns)
        for i in range(0, len(filtered_reports), 3):
            cols = st.columns(3)
            for j in range(3):
                if i + j < len(filtered_reports):
                    report = filtered_reports[i + j]
                    with cols[j]:
                        topics_html = "".join([f'<span class="topic-tag">{t.strip()}</span>' for t in report['topics'].split(',')])
                        st.markdown(f"""
                            <div class="report-card">
                                <div class="card-meta">
                                    <span class="report-type">{report['type']}</span>
                                    <span class="report-date">{report['date']}</span>
                                </div>
                                <div class="report-title">{report['title']}</div>
                                <div class="report-summary">{report['summary'][:150]}...</div>
                                <div class="report-topics">{topics_html}</div>
                                <a href="{report['url']}" target="_blank" class="view-link">View Full Report ↗</a>
                            </div>
                        """, unsafe_allow_html=True)
    else:
        st.info(f"No documents found for '{query}'. Try another keyword.")
else:
    st.info("Select a keyword or search above to view coastal reports.")
