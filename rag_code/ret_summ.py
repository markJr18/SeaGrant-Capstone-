
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

from langchain_community.chat_models import ChatOllama
from langchain_core.prompts import ChatPromptTemplate

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import pdfplumber

# Absolute import, consistent with app.py and main.py
from rag_code import database

KEYWORD_LIBRARY = {
    "Aquaculture & Oyster Farming": {
        "primary": ["oyster farming", "shellfish aquaculture", "aquaculture operations", "oyster lease", "oyster harvesting"],
        "secondary": ["hatchery", "spat", "grow-out", "submerged lands"],
        "legal_context": ["permit", "licensing", "lease agreement", "regulatory approval"],
    },
    "Environmental Conservation": {
        "primary": ["conservation", "habitat protection", "ecosystem protection", "environmental preservation"],
        "secondary": ["wetlands", "estuary", "shoreline stabilization", "protected species"],
        "legal_context": ["environmental impact", "mitigation", "regulatory compliance"],
    },
    # ... (all other keywords)
}

ALL_KEYWORDS = [kw for cat in KEYWORD_LIBRARY.values() for tier in cat.values() for kw in tier]

SC_COASTAL_SITES = {
    "HILTON HEAD ISLAND": "https://www.hiltonheadislandsc.gov",
    "BLUFFTON": "https://www.townofbluffton.com",
    "PORT ROYAL": "https://www.portroyal.org",
    "BEAUFORT": "https://www.cityofbeaufort.org",
    "HANAHAN": "https://www.cityofhanahan.com",
    "GOOSE CREEK": "https://www.goosecreeksc.gov",
    "ST STEPHEN": "https://www.ststephensc.gov",
    "MONCKS CORNER": "https://www.monckscornersc.gov",
    "McCLELLANVILLE": "https://www.mcclellanvillesc.gov",
    "SULLIVANS ISLAND": "https://www.sullivansisland.com",
    "SEABROOK ISLAND": "https://www.townofseabrookisland.org",
    "LINCOLNVILLE": "https://www.lincolnvillesc.org",
    "RAVENEL": "https://www.townofravenel.sc.gov",
    "KIAWAH ISLAND": "https://www.kiawahisland.org",
    "AWENDAW": "https://www.townawendaw.com",
    "CHARLESTON": "https://www.charleston-sc.gov",
    "NORTH CHARLESTON": "https://www.northcharleston.org",
    "ISLE OF PALMS": "https://www.iop.net",
    "FOLLY BEACH": "https://www.cityoffollybeach.com",
    "HOLLYWOOD": "https://www.townofhollywood.sc.gov",
    "MEGGETT": "https://www.townofmeggett.com",
    "MOUNT PLEASANT": "https://www.tompsc.com",
    "EDISTO BEACH": "https://www.edistobeach.com",
    "WALTERBORO": "https://www.walterborosc.org",
    "SUMMERVILLE": "https://www.summervillesc.gov",
    "ST GEORGE": "https://www.cityofstgeorgesc.gov",
    "PAWLEYS ISLAND": "https://www.pawleysisland.org",
    "GEORGETOWN": "https://www.gtcitygov.com",
    "ATLANTIC BEACH": "https://www.atlanticbeachsc.gov",
    "SURFSIDE BEACH": "https://www.surfsidebeach.org",
    "MYRTLE BEACH": "https://www.cityofmyrtlebeach.com",
    "NORTH MYRTLE BEACH": "https://www.nmb.us",
    "CONWAY": "https://www.cityofconway.com",
    "RIDGELAND": "https://www.ridgelandsc.gov",
    "HARDEEVILLE": "https://www.hardeevillesc.gov",
    "BEAUFORT COUNTY": "https://www.bcgov.net",
    "BERKELEY COUNTY": "https://www.berkeleycountysc.gov",
    "CHARLESTON COUNTY": "https://www.charlestoncounty.org",
    "COLLETON COUNTY": "https://www.colletoncounty.org",
    "DORCHESTER COUNTY": "https://www.dorchestercounty.net",
    "GEORGETOWN COUNTY": "https://www.georgetowncountysc.org",
    "HAMPTON COUNTY": "https://www.hamptoncountysc.org",
    "HORRY COUNTY": "https://www.horrycounty.org",
    "JASPER COUNTY" : "https://www.jaspercountysc.gov"
    "WILLIAMSBURG COUNTY" : "https://www.williamsburgcounty.sc.gov",
    
}

@dataclass
class ScrapedDocument:
    url: str; municipality: str; raw_text: str; doc_type: str = "unknown"; scraped_at: str = ""

@dataclass
class DocumentLink:
    url: str; link_text: str; found_on_page: str; doc_type: str = "pdf"

@dataclass
class RetrievalResult:
    url: str; municipality: str; doc_type: str; matched_keywords: list[str]; matched_categories: list[str]; relevance_score: float; summary: str; key_findings: list[str]; raw_excerpt: str; metadata: dict = field(default_factory=dict)

class KeywordScanner:
    def __init__(self):
        self._pattern_cache = {kw: re.compile(r'\b' + re.escape(kw) + r'\b', re.IGNORECASE) for kw in ALL_KEYWORDS}
    def scan(self, text: str):
        matched = [kw for kw, pat in self._pattern_cache.items() if pat.search(text)]
        categories = sorted({cat for cat, tiers in KEYWORD_LIBRARY.items() for tier_kws in tiers.values() for kw in tier_kws if kw in matched})
        word_count = max(len(text.split()), 1)
        score = min(len(matched) / max(word_count / 100, 1), 1.0)
        return matched, categories, round(score, 4)

class OllamaClient:
    SUMMARIZE_PROMPT = ChatPromptTemplate.from_messages([
        ("system", "You are a legal and environmental policy analyst... Be concise and factual."),
        ("human", "Document URL: {url}\n...Return JSON with keys...\n  hearing_relevance (high|medium|low)"),
    ])
    def __init__(self, model, temperature):
        self._llm = ChatOllama(model=model, temperature=temperature, format="json")
        self._chain = self.SUMMARIZE_PROMPT | self._llm
    def summarize(self, text, url, municipality, categories, keywords):
        response = self._chain.invoke({"text": text[:6000], "url": url, "municipality": municipality, "categories": ", ".join(categories), "keywords": ", ".join(keywords[:20])})
        raw = response.content.strip().lstrip('```json').rstrip('```')
        try: return json.loads(raw)
        except json.JSONDecodeError: return {"summary": raw[:500], "key_findings": [], "doc_type_detected": "unknown"}

class RetrievalSummarizationNetwork:
    TARGET_PAGE_KEYWORDS = ["agendas", "minutes", "documents", "meetings", "council", "records"]
    def __init__(self, relevance_threshold, llm_model, scraper_max_depth, scraper_request_delay):
        self.threshold = relevance_threshold
        self.rate_limit_delay = 1.0
        self._scanner = KeywordScanner()
        self._llm = OllamaClient(model=llm_model, temperature=0.1)
        self.results = []
        self.scraper_cache_dir = Path("./scraper_cache"); self.scraper_cache_dir.mkdir(exist_ok=True)
        self.scraper_max_depth = scraper_max_depth
        self.scraper_request_delay = scraper_request_delay
        self.scraper_timeout = 30
        self._visited_urls = set()
        self._discovered_pdfs = []
        self._session = requests.Session()
        self._session.headers.update({'User-Agent': 'Mozilla/5.0'})
        log_file = ".streamlit/scraper.log"
        if os.path.exists(log_file): os.remove(log_file)
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s', handlers=[logging.FileHandler(log_file), logging.StreamHandler()])
        self._logger = logging.getLogger(__name__)

    def scrape_municipality(self, municipality_name, base_url, target_year, auto_process, st, status_text, progress_bar):
        self._logger.info(f"Starting scrape: {municipality_name} ({target_year or 'any'})")
        self._visited_urls.clear(); self._discovered_pdfs.clear()
        try:
            doc_pages = self._find_document_pages(base_url, target_year)
            for page in doc_pages: self._discover_pdfs_on_page(page)
            for i, pdf_link in enumerate(self._discovered_pdfs):
                status_text.text(f"PDF {i+1}/{len(self._discovered_pdfs)}: {pdf_link.url}")
                progress_bar.progress((i + 1) / len(self._discovered_pdfs))
                doc = self._download_and_extract_pdf(pdf_link, municipality_name)
                if doc and auto_process: self.process(doc)
                time.sleep(self.scraper_request_delay)
        except Exception as e: self._logger.error(f"Scrape failed: {e}", exc_info=True)

    def process(self, doc):
        keywords, categories, score = self._scanner.scan(doc.raw_text)
        if score < self.threshold: return
        llm_result = self._llm.summarize(doc.raw_text[:4000], doc.url, doc.municipality, categories, keywords)
        result = RetrievalResult(doc.url, doc.municipality, llm_result.get('doc_type_detected'), keywords, categories, score, llm_result.get('summary'), llm_result.get('key_findings'), doc.raw_text[:800])
        self.results.append(result)
        db_data = dataclasses.asdict(result); db_data['raw_text'] = doc.raw_text
        database.add_document(db_data)

    def _find_document_pages(self, base_url, target_year):
        doc_pages, to_visit = [], [(base_url, 0)]
        while to_visit:
            url, depth = to_visit.pop(0)
            if url in self._visited_urls or depth > self.scraper_max_depth: continue
            self._visited_urls.add(url)
            try:
                html = self._fetch_html(url)
                if not html: continue
                soup = BeautifulSoup(html, 'html.parser')
                if any(kw in url.lower() for kw in self.TARGET_PAGE_KEYWORDS) or len(soup.find_all('a', href=re.compile(r'\.pdf$', re.I))) >= 3:
                    doc_pages.append(url)
                if depth < self.scraper_max_depth:
                    for link in self._extract_relevant_links(soup, url, target_year):
                        if link not in self._visited_urls: to_visit.append((link, depth + 1))
                time.sleep(self.scraper_request_delay)
            except Exception as e: self._logger.warning(f"Visit error {url}: {e}")
        return doc_pages

    def _extract_relevant_links(self, soup, base_url, target_year):
        links, domain = [], urlparse(base_url).netloc
        for a in soup.find_all('a', href=True):
            href = a['href']
            if not href.startswith(('http', '/')): continue
            full_url = urljoin(base_url, href)
            if urlparse(full_url).netloc != domain or any(full_url.lower().endswith(ext) for ext in ['.jpg', '.zip']): continue
            text = a.get_text().lower()
            year_match = str(target_year) in text or str(target_year) in full_url.lower() if target_year else True
            if year_match and any(kw in text for kw in self.TARGET_PAGE_KEYWORDS): links.append(full_url)
        return links

    def _discover_pdfs_on_page(self, page_url):
        try:
            html = self._fetch_html(page_url)
            if not html: return
            soup = BeautifulSoup(html, 'html.parser')
            for a in soup.find_all('a', href=re.compile(r'\.pdf$', re.I)):
                pdf_url = urljoin(page_url, a['href'])
                if not any(p.url == pdf_url for p in self._discovered_pdfs):
                    self._discovered_pdfs.append(DocumentLink(pdf_url, a.get_text(strip=True), page_url))
        except Exception as e: self._logger.warning(f"PDF discovery error on {page_url}: {e}")

    def _download_and_extract_pdf(self, pdf_link, municipality):
        cache_key = hashlib.md5(pdf_link.url.encode()).hexdigest()
        cache_file = self.scraper_cache_dir / f"{cache_key}.txt"
        if cache_file.exists(): return ScrapedDocument(pdf_link.url, municipality, cache_file.read_text(encoding='utf-8'))
        try:
            pdf_content = self._fetch_pdf(pdf_link.url)
            if not pdf_content: return None
            with pdfplumber.open(io.BytesIO(pdf_content)) as pdf:
                text = "\n".join(p.extract_text() for p in pdf.pages if p.extract_text())
            if len(text.strip()) < 100: return None
            cache_file.write_text(text, encoding='utf-8')
            return ScrapedDocument(pdf_link.url, municipality, text)
        except Exception as e: self._logger.error(f"PDF processing error {pdf_link.url}: {e}"); return None

    def _fetch_html(self, url): 
        try: r = self._session.get(url, timeout=self.scraper_timeout); r.raise_for_status(); return r.text
        except: return None

    def _fetch_pdf(self, url):
        try: r = self._session.get(url, timeout=self.scraper_timeout); r.raise_for_status(); return r.content
        except: return None
