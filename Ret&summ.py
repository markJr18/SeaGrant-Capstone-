

import os
import json
import re
import time
from typing import Optional
from dataclasses import dataclass, field

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings


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


# Gemini LLM Client 
class GeminiClient:
    """Thin LangChain wrapper around Gemini Flash / Pro."""

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

    def __init__(self, model: str = "gemini-1.5-flash", temperature: float = 0.1):
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise EnvironmentError("GOOGLE_API_KEY not set in environment.")
        self._llm = ChatGoogleGenerativeAI(
            model=model,
            temperature=temperature,
            google_api_key=api_key,
            convert_system_message_to_human=True,
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
        api_key = os.environ.get("GOOGLE_API_KEY", "")
        self._embeddings = GoogleGenerativeAIEmbeddings(
            model="models/embedding-001",
            google_api_key=api_key,
        )
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

    def __init__(
        self,
        relevance_threshold: float = 0.02,
        use_vector_index: bool = False,
        gemini_model: str = "gemini-1.5-flash",
        rate_limit_delay: float = 1.0,
    ):
        self.threshold = relevance_threshold
        self.rate_limit_delay = rate_limit_delay

        self._scanner = KeywordScanner()
        self._chunker = DocumentChunker()
        self._llm = GeminiClient(model=gemini_model)
        self._vector_index = VectorIndex() if use_vector_index else None

        self.results: list[RetrievalResult] = []

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