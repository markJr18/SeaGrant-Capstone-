

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
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import OllamaEmbeddings

# Web scraper dependencies
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import pdfplumber
import dataclasses
from rag_code import database


KEYWORD_LIBRARY: dict[str, dict[str, list[str]]] = {
    "Aquaculture & Oyster Farming": {
        "primary": ["oyster farming", "shellfish aquaculture", "aquaculture operations",
                    "oyster lease", "oyster harvesting", "bivalve cultivation", "marine farming"],
        "secondary": ["hatchery", "spat", "grow-out", "submerged lands", "tidal zone", "cultivation gear"],
        "legal_context": ["permit", "licensing", "lease agreement", "regulatory approval", "compliance", "zoning"],
    },
    "Environmental Conservation": {
        "primary": ["conservation", "habitat protection", "ecosystem protection",
                    "environmental preservation", "marine preservation", "biodiversity"],
        "secondary": ["wetlands", "estuary", "shoreline stabilization", "protected species", "buffer zone"],
        "legal_context": ["environmental impact", "mitigation", "regulatory compliance", "agency review", "public comment"],
    },
    "Ecological Impact": {
        "primary": ["ecological impact", "environmental impact", "water quality",
                    "sediment disturbance", "nutrient cycling"],
        "secondary": ["dissolved oxygen", "turbidity", "runoff", "contamination", "habitat disruption"],
        "legal_context": ["environmental assessment", "impact statement", "findings of fact", "expert testimony"],
    },
    "Legal & Hearing Language": {
        "primary": ["findings of fact", "administrative ruling", "hearing officer",
                    "tribunal decision", "testimony", "evidentiary record"],
        "secondary": ["motion", "appeal", "compliance order", "violation", "enforcement action", "regulatory authority"],
        "legal_context": ["the board finds", "it was determined that", "the evidence shows",
                          "the agency concludes", "the record reflects", "the commission voted"],
    },
    "Water Quality & Monitoring": {
        "primary": ["water quality monitoring", "numeric criteria", "dissolved oxygen",
                    "chlorophyll levels", "nitrogen levels", "eutrophication"],
        "secondary": ["water quality metrics", "water quality parameters", "harmful algal blooms", "safe water use"],
        "legal_context": [],
    },
    "Septic & Wastewater": {
        "primary": ["septic systems", "septic functionality"],
        "secondary": ["septic impacts", "wastewater management"],
        "legal_context": [],
    },
    "Stormwater Management": {
        "primary": ["stormwater runoff", "stormwater outfalls", "stormwater infrastructure", "municipal stormwater"],
        "secondary": ["MS4", "watershed management", "stormwater pathways"],
        "legal_context": [],
    },
    "Habitat & Ecosystems": {
        "primary": ["habitat protection", "habitat restoration", "marsh restoration",
                    "salt marsh resilience", "wetland protection", "estuarine ecosystems"],
        "secondary": ["habitat fragmentation", "critical habitat", "ecosystem services",
                      "marsh migration", "marsh accretion"],
        "legal_context": [],
    },
    "Contaminants & Pollution": {
        "primary": ["emerging contaminants", "chemicals of emerging concern", "PFAS", "forever chemicals"],
        "secondary": ["bioaccumulation", "cumulative impacts", "synergistic impacts"],
        "legal_context": [],
    },
    "Climate & Sea Level Rise": {
        "primary": ["sea level rise", "coastal erosion", "land subsidence", "salt intrusion"],
        "secondary": ["climate change impacts", "rising tides", "tidal flooding", "compound flooding"],
        "legal_context": [],
    },
    "Coastal Development": {
        "primary": ["coastal development", "land use planning", "affordable housing", "urban sprawl"],
        "secondary": ["development impacts", "climate migration", "gentrification"],
        "legal_context": [],
    },
    "Beach & Shoreline Management": {
        "primary": ["beach renourishment", "shoreline preservation", "living shorelines", "nature-based solutions"],
        "secondary": ["beneficial use", "dredged material", "sediment management"],
        "legal_context": [],
    },
    "Fisheries & Seafood": {
        "primary": ["commercial fisheries", "recreational fisheries", "local seafood",
                    "seafood sustainability", "illegal fishing"],
        "secondary": ["seafood fraud", "seafood imports", "fishing pressure", "fish stock management"],
        "legal_context": [],
    },
    "Working Waterfronts": {
        "primary": ["working waterfronts", "waterfront access"],
        "secondary": ["processing capacity", "conservation easements", "business continuity"],
        "legal_context": [],
    },
    "Emergency & Resilience": {
        "primary": ["emergency preparedness", "flood monitoring", "hazard communication", "resilience strategies"],
        "secondary": ["risk communication", "community resilience", "regional coordination"],
        "legal_context": [],
    },
    "Conservation & Land Use": {
        "primary": ["farmland preservation", "land conservation", "buildout analysis"],
        "secondary": ["farmland conversion", "resource exploitation"],
        "legal_context": [],
    },
    "Tourism & Recreation": {
        "primary": ["sustainable tourism", "ecotourism", "beach access", "coastal access"],
        "secondary": ["non-motorized access", "recreational impacts"],
        "legal_context": [],
    },
    "Community Engagement": {
        "primary": ["citizen science", "community engagement", "stewardship ethic"],
        "secondary": ["participatory GIS", "outreach programs"],
        "legal_context": [],
    },
    "Data & Research": {
        "primary": ["long-term monitoring", "environmental change", "benchmark research"],
        "secondary": ["data collection", "environmental indicators", "research gaps"],
        "legal_context": [],
    },
    "Education & Workforce": {
        "primary": ["workforce development", "environmental literacy", "STEM education"],
        "secondary": ["career pathways", "skills training", "internship programs"],
        "legal_context": [],
    },
}

# Flat keyword list for fast regex scanning
ALL_KEYWORDS: list[str] = [
    kw for cat in KEYWORD_LIBRARY.values()
    for tier in cat.values()
    for kw in tier
]

# Target Website Registry 
SC_COASTAL_SITES: dict[str, str] = {
    "HILTON HEAD ISLAND": "https://www.hiltonheadislandsc.gov",
    "BLUFFTON": "https://www.townofbluffton.com",
    "PORT ROYAL": "https://www.portroyal.gov",
    "BEAUFORT": "https://www.cityofbeaufort.org",
    "JAMESTOWN": "https://www.jamestownsc.gov",
    "BONNEAU": "https://www.bonneau-sc.gov",
    "HANAHAN": "https://www.cityofhanahan.com",
    "GOOSE CREEK": "https://www.cityofgoosecreek.com",
    "ST STEPHEN": "https://www.ststephensc.gov",
    "MONCKS CORNER": "https://www.monckscornersc.gov",
    "McCLELLANVILLE": "https://www.mcclellanvillesc.gov",
    "SULLIVANS ISLAND": "https://www.sullivansisland.com",
    "SEABROOK ISLAND": "https://www.townofseabrookisland.org",
    "LINCOLNVILLE": "https://www.lincolnvillesc.org",
    "RAVENEL": "https://www.townofravanel.sc.gov",
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
    # Counties
    "BEAUFORT COUNTY": "https://www.bcgov.net",
    "BERKELEY COUNTY": "https://www.berkeleycountysc.gov",
    "CHARLESTON COUNTY": "https://www.charlestoncounty.org",
    "COLLETON COUNTY": "https://www.colletoncounty.org",
    "DORCHESTER COUNTY": "https://www.dorchestercounty.net",
    "GEORGETOWN COUNTY": "https://www.georgetowncountysc.org",
    "HAMPTON COUNTY": "https://www.hamptoncounty.sc.gov",
    "HORRY COUNTY": "https://www.horrycounty.org",
}


# Data classes 
@dataclass
class ScrapedDocument:
    """Passed in by the scraper skeleton. No scraping logic here."""
    url: str
    municipality: str
    raw_text: str
    doc_type: str = "unknown"        # e.g. "meeting_minutes", "agenda", "ordinance"
    scraped_at: str = ""             # ISO timestamp from scraper


@dataclass
class DocumentLink:
    """Intermediate representation of a discovered document link during scraping."""
    url: str                # Full URL to the document
    link_text: str          # Anchor text from the link
    found_on_page: str      # URL of the page where this link was found
    doc_type: str = "pdf"   # Document type inferred from link


@dataclass
class RetrievalResult:
    url: str
    municipality: str
    doc_type: str
    matched_keywords: list[str]
    matched_categories: list[str]
    relevance_score: float           # 0-1
    summary: str
    key_findings: list[str]
    raw_excerpt: str
    metadata: dict = field(default_factory=dict)


# Keyword Scanner 
class KeywordScanner:
    """
    Fast pre-filter pass. Returns matched keywords + categories.
    Runs BEFORE the LLM to avoid burning tokens on irrelevant docs.
    """

    def __init__(self):
        self._pattern_cache: dict[str, re.Pattern] = {
            kw: re.compile(r'\b' + re.escape(kw) + r'\b', re.IGNORECASE)
            for kw in ALL_KEYWORDS
        }

    def scan(self, text: str) -> tuple[list[str], list[str], float]:
        """
        Returns:
            matched_keywords  – deduplicated list
            matched_categories – category names that fired
            relevance_score   – simple hit-density score (0-1)
        """
        matched = [kw for kw, pat in self._pattern_cache.items() if pat.search(text)]
        categories = sorted({
            cat for cat, tiers in KEYWORD_LIBRARY.items()
            for tier_kws in tiers.values()
            for kw in tier_kws
            if kw in matched
        })
        word_count = max(len(text.split()), 1)
        score = min(len(matched) / max(word_count / 100, 1), 1.0)
        return matched, categories, round(score, 4)


# Text Chunker
class DocumentChunker:
    def __init__(self, chunk_size: int = 2000, chunk_overlap: int = 200):
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

    def chunk(self, text: str) -> list[str]:
        return self._splitter.split_text(text)


# Ollama LLM Client 
class OllamaClient:
    """Thin LangChain wrapper around local Ollama models."""

    SUMMARIZE_PROMPT = ChatPromptTemplate.from_messages([
        ("system",
         "You are a legal and environmental policy analyst specializing in "
         "SC coastal municipalities. Extract ONLY information relevant to the "
         "matched keyword categories. Be concise and factual."),
        ("human",
         "Document URL: {url}\nMunicipality: {municipality}\n"
         "Matched Categories: {categories}\nMatched Keywords: {keywords}\n\n"
         "TEXT EXCERPT:\n{text}\n\n"
         "Return JSON with keys:\n"
         "  summary (2-4 sentences),\n"
         "  key_findings (list of bullet strings, max 6),\n"
         "  doc_type_detected (string),\n"
         "  hearing_relevance (high|medium|low)"),
    ])

    def __init__(self, model: str = "llama3", temperature: float = 0.1):
        self._llm = ChatOllama(
            model=model,
            temperature=temperature,
            format="json",
        )
        self._chain = self.SUMMARIZE_PROMPT | self._llm

    def summarize(
        self,
        text: str,
        url: str,
        municipality: str,
        categories: list[str],
        keywords: list[str],
    ) -> dict:
        response = self._chain.invoke({
            "text": text[:6000],   # hard cap before sending
            "url": url,
            "municipality": municipality,
            "categories": ", ".join(categories),
            "keywords": ", ".join(keywords[:20]),
        })
        raw = response.content.strip()
        # Strip markdown fences if present
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {
                "summary": raw[:500],
                "key_findings": [],
                "doc_type_detected": "unknown",
                "hearing_relevance": "unknown",
            }


# ── Optional: Vector Store for semantic search ────────────────────────────────
class VectorIndex:
    """
    Optional semantic retrieval layer on top of keyword pre-filter.
    Call build() once after bulk scrape, then query() per session.
    """

    def __init__(self):
        self._embeddings = OllamaEmbeddings()
        self._store: Optional[FAISS] = None

    def build(self, docs: list[Document]) -> None:
        self._store = FAISS.from_documents(docs, self._embeddings)

    def query(self, query: str, k: int = 5) -> list[Document]:
        if not self._store:
            raise RuntimeError("Call build() before query().")
        return self._store.similarity_search(query, k=k)

    def save(self, path: str) -> None:
        if self._store:
            self._store.save_local(path)

    def load(self, path: str) -> None:
        self._store = FAISS.load_local(path, self._embeddings)



class RetrievalSummarizationNetwork:
    """
    Ingestion point for the scraper skeleton.

    Scraper calls:
        network = RetrievalSummarizationNetwork()
        result  = network.process(scraped_doc)

    Results are returned AND appended to self.results for batch export.
    """

    # Common patterns for identifying document center pages during scraping
    TARGET_PAGE_KEYWORDS = [
        "agendas", "minutes", "document center", "documents",
        "meetings", "council", "planning commission", 
        "public records", "records center", "archive",
        "agendas & minutes", "agendas, minutes & videos",
        "adopted plans, guides & reports", "town council",
        "public meeting calendar"
    ]

    def __init__(
        self,
        relevance_threshold: float = 0.02,
        use_vector_index: bool = False,
        llm_model: str = "llama3",
        rate_limit_delay: float = 1.0,
        # Scraper-specific params
        scraper_log_file: str = "./.streamlit/scraper.log", # Log file path
        scraper_cache_dir: str = "./scraper_cache",
        scraper_max_depth: int = 2,
        scraper_request_delay: float = 1.5,
        scraper_timeout: int = 30,
    ):
        self.threshold = relevance_threshold
        self.rate_limit_delay = rate_limit_delay

        self._scanner = KeywordScanner()
        self._chunker = DocumentChunker()
        self._llm = OllamaClient(model=llm_model)
        self._vector_index = VectorIndex() if use_vector_index else None

        self.results: list[RetrievalResult] = []

        # Web scraper initialization
        self.scraper_cache_dir = Path(scraper_cache_dir)
        self.scraper_cache_dir.mkdir(exist_ok=True)
        self.scraper_max_depth = scraper_max_depth
        self.scraper_request_delay = scraper_request_delay
        self.scraper_timeout = scraper_timeout
        
        # Track visited URLs and discovered documents during scraping
        self._visited_urls: set[str] = set()
        self._discovered_pdfs: list[DocumentLink] = []
        
        # HTTP session for connection pooling and reuse
        self._session = requests.Session()
        self._session.headers.update({
            'User-Agent': 'Mozilla/5.0 (SC Coastal Research Bot) Python/3.x'
        })
        
        # Setup logging for scraper operations
        # Clear previous log file
        if os.path.exists(scraper_log_file):
            os.remove(scraper_log_file)
            
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(scraper_log_file),
                logging.StreamHandler()
            ]
        )
        self._logger = logging.getLogger(__name__)

    # ── Public API - Web Scraper ──────────────────────────────────────────────

    def scrape_municipality(
        self, 
        municipality_name: str, 
        base_url: str,
        auto_process: bool = False,
        st=None,
        status_text=None,
        progress_bar=None
    ) -> list[ScrapedDocument]:
        """
        Scrape a single municipality website for documents.
        
        Workflow:
            1. Navigate website to find document center pages
            2. Discover all PDF links on those pages
            3. Download and extract text from each PDF
            4. Optionally auto-process through the retrieval pipeline
        
        Args:
            municipality_name: Name from SC_COASTAL_SITES
            base_url: Root URL of the municipality website
            auto_process: If True, automatically calls process() on each document
        
        Returns:
            List of ScrapedDocument objects
        """
        self._logger.info(f"Starting scrape for {municipality_name} at {base_url}")
        self._logger.info(f"Scraper settings: max_depth={self.scraper_max_depth}, delay={self.scraper_request_delay}s, timeout={self.scraper_timeout}s")
        
        # Reset scraper state for this municipality
        self._visited_urls.clear()
        self._discovered_pdfs.clear()
        
        try:
            # Step 1: Navigate and find document center pages
            doc_pages = self._find_document_pages(base_url)
            self._logger.info(f"Found {len(doc_pages)} potential document pages")
            
            # Step 2: Discover all PDF links on those pages
            for page_url in doc_pages:
                self._discover_pdfs_on_page(page_url)
            
            self._logger.info(f"Discovered {len(self._discovered_pdfs)} PDF links")
            
            # Step 3: Download and extract text from each PDF
            scraped_docs = []
            for i, pdf_link in enumerate(self._discovered_pdfs):
                self._logger.info(
                    f"Processing PDF {i+1}/{len(self._discovered_pdfs)}: {pdf_link.url}"
                )
                if st:
                    progress = (i + 1) / len(self._discovered_pdfs)
                    status_text.text(f"Processing PDF {i+1}/{len(self._discovered_pdfs)}: {pdf_link.url}")
                    progress_bar.progress(progress)
                doc = self._download_and_extract_pdf(pdf_link, municipality_name)
                if doc:
                    scraped_docs.append(doc)
                    
                    # Optionally run through retrieval pipeline immediately
                    if auto_process:
                        self.process(doc)
                
                time.sleep(self.scraper_request_delay)
            
            self._logger.info(
                f"Successfully scraped {len(scraped_docs)} documents for {municipality_name}"
            )
            return scraped_docs
            
        except Exception as e:
            self._logger.error(f"Scraping error for {municipality_name}: {e}", exc_info=True)
            return []

    def scrape_all_municipalities(
        self,
        sites: dict[str, str] = None,
        auto_process: bool = True
    ) -> list[ScrapedDocument]:
        """
        Scrape all municipalities in the registry (monthly batch operation).
        
        Args:
            sites: Dictionary of {name: url}. Uses SC_COASTAL_SITES if None
            auto_process: Auto-process each document through the pipeline
        
        Returns:
            Combined list of all scraped documents from all municipalities
        """
        if sites is None:
            sites = SC_COASTAL_SITES
        
        all_docs = []
        total_sites = len(sites)
        
        for i, (name, url) in enumerate(sites.items(), 1):
            self._logger.info(f"\n{'='*70}\n[{i}/{total_sites}] Scraping {name}\n{'='*70}")
            docs = self.scrape_municipality(name, url, auto_process)
            all_docs.extend(docs)
            
        self._logger.info(f"\n{'='*70}\nScraping complete: {len(all_docs)} total documents\n{'='*70}")
        return all_docs

    # ── Public API ────────────────────────────────────────────────────────────

    def process(self, doc: ScrapedDocument) -> Optional[RetrievalResult]:
        """
        Full pipeline for a single scraped document.
        Returns None if the document doesn't pass the relevance threshold.
        """
        # 1. Keyword scan (cheap, no API call)
        keywords, categories, score = self._scanner.scan(doc.raw_text)

        if score < self.threshold or not keywords:
            return None

        # 2. Select the most relevant chunk to send to the LLM
        chunks = self._chunker.chunk(doc.raw_text)
        best_chunk = self._best_chunk(chunks, keywords)

        # 3. LLM summarization
        time.sleep(self.rate_limit_delay)   # gentle rate limiting
        llm_result = self._llm.summarize(
            text=best_chunk,
            url=doc.url,
            municipality=doc.municipality,
            categories=categories,
            keywords=keywords,
        )

        result = RetrievalResult(
            url=doc.url,
            municipality=doc.municipality,
            doc_type=llm_result.get("doc_type_detected", doc.doc_type),
            matched_keywords=keywords,
            matched_categories=categories,
            relevance_score=score,
            summary=llm_result.get("summary", ""),
            key_findings=llm_result.get("key_findings", []),
            raw_excerpt=best_chunk[:800],
            metadata={
                "scraped_at": doc.scraped_at,
                "hearing_relevance": llm_result.get("hearing_relevance", "unknown"),
                "keyword_hit_count": len(keywords),
            },
        )

        self.results.append(result)

        # Save to database
        db_data = dataclasses.asdict(result)
        db_data['raw_text'] = doc.raw_text
        database.add_document(db_data)

        return result

    def process_batch(self, docs: list[ScrapedDocument]) -> list[RetrievalResult]:
        """Process a list of scraped documents, skip irrelevant ones."""
        output = []
        for doc in docs:
            r = self.process(doc)
            if r:
                output.append(r)
        return output

    def export_json(self, path: str) -> None:
        """Write all results to a JSON file for downstream UX consumption."""
        import dataclasses
        with open(path, "w", encoding="utf-8") as f:
            json.dump(
                [dataclasses.asdict(r) for r in self.results],
                f, indent=2, ensure_ascii=False
            )

    def export_summary_csv(self, path: str) -> None:
        """Flat CSV export: one row per result."""
        import csv, dataclasses
        if not self.results:
            return
        fieldnames = list(dataclasses.asdict(self.results[0]).keys())
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in self.results:
                row = dataclasses.asdict(r)
                # flatten lists to pipe-separated strings for CSV
                row["matched_keywords"] = " | ".join(row["matched_keywords"])
                row["matched_categories"] = " | ".join(row["matched_categories"])
                row["key_findings"] = " | ".join(row["key_findings"])
                row["metadata"] = json.dumps(row["metadata"])
                writer.writerow(row)

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _best_chunk(self, chunks: list[str], keywords: list[str]) -> str:
        """Return chunk with highest keyword density."""
        if not chunks:
            return ""
        kw_set = {kw.lower() for kw in keywords}
        scored = []
        for chunk in chunks:
            lower = chunk.lower()
            hits = sum(1 for kw in kw_set if kw in lower)
            scored.append((hits, chunk))
        scored.sort(key=lambda x: -x[0])
        return scored[0][1]

    # ── Web Scraper Internal Methods ──────────────────────────────────────────

    def _find_document_pages(self, base_url: str) -> list[str]:
        """
        Crawl the site to find pages likely to contain documents.
        Uses breadth-first search up to max_depth.
        
        Returns:
            List of URLs identified as document center pages
        """
        doc_pages = []
        to_visit = [(base_url, 0)]  # (url, depth)
        
        while to_visit:
            url, depth = to_visit.pop(0)
            
            if url in self._visited_urls or depth > self.scraper_max_depth:
                continue
            
            self._visited_urls.add(url)
            
            try:
                html = self._fetch_html(url)
                if not html:
                    continue
                
                soup = BeautifulSoup(html, 'html.parser')
                
                # Check if this page looks like a document center
                if self._is_document_page(soup, url):
                    doc_pages.append(url)
                    self._logger.info(f"Found document page: {url}")
                
                # Find more pages to explore (only if not too deep)
                if depth < self.scraper_max_depth:
                    links = self._extract_relevant_links(soup, url)
                    for link in links:
                        if link not in self._visited_urls:
                            to_visit.append((link, depth + 1))
                
                time.sleep(self.scraper_request_delay)
                
            except Exception as e:
                self._logger.warning(f"Error visiting {url}: {e}")
                continue
        
        return doc_pages

    def _is_document_page(self, soup: BeautifulSoup, url: str) -> bool:
        """
        Heuristic to determine if a page contains documents.
        Checks URL, title, PDF link density, and headings.
        """
        # Check URL for keywords
        url_lower = url.lower()
        if any(kw in url_lower for kw in self.TARGET_PAGE_KEYWORDS):
            return True
        
        # Check page title
        title = soup.find('title')
        if title and any(kw in title.get_text().lower() for kw in self.TARGET_PAGE_KEYWORDS):
            return True
        
        # Check for multiple PDF links (strong signal)
        pdf_links = soup.find_all('a', href=re.compile(r'\.pdf$', re.I))
        if len(pdf_links) >= 3:
            return True
        
        # Check headings for document-related keywords
        for heading in soup.find_all(['h1', 'h2', 'h3']):
            text = heading.get_text().lower()
            if any(kw in text for kw in self.TARGET_PAGE_KEYWORDS):
                return True
        
        return False

    def _extract_relevant_links(self, soup: BeautifulSoup, base_url: str) -> list[str]:
        """
        Extract navigation links that might lead to document pages.
        Only follows links within the same domain.
        """
        links = []
        base_domain = urlparse(base_url).netloc
        
        FILE_EXTENSIONS_TO_IGNORE = [
            '.pdf', '.jpg', '.jpeg', '.png', '.gif', '.zip', '.docx', '.xlsx', '.pptx'
        ]

        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']

            # Ignore mailto, tel, and other non-http links
            if not href.startswith(('http', '/', '#')):
                continue

            full_url = urljoin(base_url, href)

            # Ignore links to files
            if any(full_url.lower().endswith(ext) for ext in FILE_EXTENSIONS_TO_IGNORE):
                continue
            
            # Only follow links on the same domain
            if urlparse(full_url).netloc != base_domain:
                continue
            
            # Check if link text or URL suggests documents
            link_text = a_tag.get_text().lower()
            url_lower = full_url.lower()
            
            # Match against target keywords
            if any(kw in link_text or kw in url_lower for kw in self.TARGET_PAGE_KEYWORDS):
                links.append(full_url)
        
        return links

    def _discover_pdfs_on_page(self, page_url: str) -> None:
        """
        Find all PDF links on a given page and add to discovered_pdfs list.
        Deduplicates and infers document type from link text.
        """
        try:
            html = self._fetch_html(page_url)
            if not html:
                return
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # Find all links ending in .pdf (case insensitive)
            for a_tag in soup.find_all('a', href=re.compile(r'\.pdf$', re.I)):
                href = a_tag['href']
                pdf_url = urljoin(page_url, href)
                
                # Skip if already discovered
                if any(pdf.url == pdf_url for pdf in self._discovered_pdfs):
                    continue
                
                link_text = a_tag.get_text(strip=True)
                
                # Infer document type from link text and URL
                doc_type = self._infer_doc_type(link_text, pdf_url)
                
                self._discovered_pdfs.append(DocumentLink(
                    url=pdf_url,
                    link_text=link_text,
                    found_on_page=page_url,
                    doc_type=doc_type
                ))
                
        except Exception as e:
            self._logger.warning(f"Error discovering PDFs on {page_url}: {e}")

    def _infer_doc_type(self, link_text: str, url: str) -> str:
        """
        Guess document type from link text or URL patterns.
        Returns category like 'agenda', 'meeting_minutes', 'ordinance', etc.
        """
        text = (link_text + " " + url).lower()
        
        if any(w in text for w in ["agenda", "agendas"]):
            return "agenda"
        elif any(w in text for w in ["minutes", "minute"]):
            return "meeting_minutes"
        elif any(w in text for w in ["ordinance", "resolution"]):
            return "ordinance"
        elif any(w in text for w in ["report", "environmental", "impact"]):
            return "report"
        else:
            return "unknown"

    def _download_and_extract_pdf(
        self, 
        pdf_link: DocumentLink,
        municipality: str
    ) -> Optional[ScrapedDocument]:
        """
        Download PDF, extract text, and create ScrapedDocument.
        Uses cache to avoid re-downloading/re-processing the same PDF.
        """
        try:
            # Check cache first (saves bandwidth and time)
            cache_key = self._get_cache_key(pdf_link.url)
            cached_text = self._load_from_cache(cache_key)
            
            if cached_text:
                self._logger.info(f"Using cached text for {pdf_link.url}")
                text = cached_text
            else:
                # Download PDF content
                pdf_content = self._fetch_pdf(pdf_link.url)
                if not pdf_content:
                    return None
                
                # Extract text from PDF
                text = self._extract_text_from_pdf(pdf_content)
                if not text or len(text.strip()) < 100:
                    self._logger.warning(f"Insufficient text extracted from {pdf_link.url}")
                    return None
                
                # Cache the extracted text for future runs
                self._save_to_cache(cache_key, text)
            
            # Create ScrapedDocument ready for processing pipeline
            return ScrapedDocument(
                url=pdf_link.url,
                municipality=municipality,
                raw_text=text,
                doc_type=pdf_link.doc_type,
                scraped_at=datetime.now().isoformat()
            )
            
        except Exception as e:
            self._logger.error(f"Error processing PDF {pdf_link.url}: {e}", exc_info=True)
            return None

    def _fetch_html(self, url: str) -> Optional[str]:
        """Fetch HTML content from a URL with error handling."""
        try:
            response = self._session.get(url, timeout=self.scraper_timeout)
            response.raise_for_status()
            return response.text
        except Exception as e:
            self._logger.warning(f"Failed to fetch {url}: {e}")
            return None

    def _fetch_pdf(self, url: str) -> Optional[bytes]:
        """Download PDF content as bytes."""
        try:
            response = self._session.get(url, timeout=self.scraper_timeout)
            response.raise_for_status()
            return response.content
        except Exception as e:
            self._logger.warning(f"Failed to download PDF {url}: {e}")
            return None

    def _extract_text_from_pdf(self, pdf_content: bytes) -> str:
        """
        Extract text from PDF bytes using pdfplumber.
        Processes all pages and combines into single text string.
        """
        try:
            text_parts = []
            
            with pdfplumber.open(io.BytesIO(pdf_content)) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        text_parts.append(text)
            
            return "\n\n".join(text_parts)
            
        except Exception as e:
            self._logger.error(f"PDF text extraction failed: {e}")
            return ""

    def _get_cache_key(self, url: str) -> str:
        """Generate unique cache filename from URL using MD5 hash."""
        return hashlib.md5(url.encode()).hexdigest()

    def _save_to_cache(self, cache_key: str, text: str) -> None:
        """Save extracted text to cache directory for reuse."""
        cache_file = self.scraper_cache_dir / f"{cache_key}.txt"
        cache_file.write_text(text, encoding='utf-8')

    def _load_from_cache(self, cache_key: str) -> Optional[str]:
        """Load previously extracted text from cache if it exists."""
        cache_file = self.scraper_cache_dir / f"{cache_key}.txt"
        if cache_file.exists():
            return cache_file.read_text(encoding='utf-8')
        return None


# ══════════════════════════════════════════════════════════════════════════════
# Usage Example - Monthly Scraping Operation
# ══════════════════════════════════════════════════════════════════════════════

def main_monthly_scrape():
    """
    Example of monthly batch scraping operation.
    
    This function demonstrates the complete workflow:
        1. Initialize the network with scraper enabled
        2. Scrape all SC coastal municipalities
        3. Auto-process through keyword filtering and LLM summarization
        4. Export results to JSON and CSV
    """
    # Initialize network with scraper configuration
    network = RetrievalSummarizationNetwork(
        relevance_threshold=0.02,
        scraper_cache_dir="./scraper_cache",
        scraper_max_depth=3,
        scraper_request_delay=1.5,  # Respectful rate limiting
        rate_limit_delay=1.0,
    )
    
    # Option 1: Scrape all municipalities (full monthly run)
    network.scrape_all_municipalities(auto_process=True)
    
    # Option 2: Test with a single municipality first
    # network.scrape_municipality("CHARLESTON", "https://www.charleston-sc.gov")
    
    # Option 3: Test with a subset
    # test_sites = {
    #     "CHARLESTON": "https://www.charleston-sc.gov",
    #     "MOUNT PLEASANT": "https://www.tompsc.com",
    # }
    # network.scrape_all_municipalities(sites=test_sites, auto_process=True)
    
    # Export results
    timestamp = datetime.now().strftime("%Y-%m")
    network.export_json(f"output/{timestamp}_results.json")
    network.export_summary_csv(f"output/{timestamp}_summary.csv")
    
    print(f"\n{'='*70}")
    print(f"Monthly scrape complete!")
    print(f"Total relevant documents found: {len(network.results)}")
    print(f"Results exported to: output/{timestamp}_*.json/csv")
    print(f"{'='*70}")


if __name__ == "__main__":
    # Run the monthly scraping operation
    main_monthly_scrape()