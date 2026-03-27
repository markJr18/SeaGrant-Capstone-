# Web Scraper Usage Guide

## Installation

First, install the required dependencies:

```bash
pip install -r requirements.txt
```

## Setup

Make sure you have your Google API key set:

```bash
export GOOGLE_API_KEY="your-api-key-here"
```

## Quick Start

### Option 1: Scrape All Municipalities (Monthly Run)

```python
from Ret_summ import RetrievalSummarizationNetwork
from datetime import datetime

# Initialize network
network = RetrievalSummarizationNetwork()

# Scrape all 45+ SC coastal municipalities
network.scrape_all_municipalities(auto_process=True)

# Export results
timestamp = datetime.now().strftime("%Y-%m")
network.export_json(f"output/{timestamp}_results.json")
network.export_summary_csv(f"output/{timestamp}_summary.csv")

print(f"Found {len(network.results)} relevant documents")
```

### Option 2: Test with Single Municipality

```python
network = RetrievalSummarizationNetwork()

# Scrape just Charleston
scraped_docs = network.scrape_municipality(
    "CHARLESTON", 
    "https://www.charleston-sc.gov",
    auto_process=True
)

print(f"Scraped {len(scraped_docs)} documents")
print(f"Found {len(network.results)} relevant documents")
```

### Option 3: Test with Subset

```python
network = RetrievalSummarizationNetwork()

test_sites = {
    "CHARLESTON": "https://www.charleston-sc.gov",
    "MOUNT PLEASANT": "https://www.tompsc.com",
    "BEAUFORT": "https://www.cityofbeaufort.org",
}

network.scrape_all_municipalities(sites=test_sites, auto_process=True)
```

## How It Works

### 1. Navigation
The scraper uses breadth-first search to navigate websites looking for:
- Pages with "agendas", "minutes", "document center" in the URL or title
- Pages with 3+ PDF links
- Navigation links containing document-related keywords

### 2. PDF Discovery
Once document pages are found, the scraper:
- Extracts all PDF links
- Infers document type from link text (agenda, minutes, ordinance, etc.)
- Deduplicates URLs

### 3. Text Extraction
For each PDF:
- Downloads the PDF file
- Extracts text using pdfplumber
- Caches extracted text (reuses cache on subsequent runs)
- Creates `ScrapedDocument` object

### 4. Processing Pipeline
If `auto_process=True`:
- Runs keyword scanning
- Filters by relevance threshold
- Chunks text intelligently
- Generates LLM summaries for relevant documents

## Configuration

```python
network = RetrievalSummarizationNetwork(
    # Processing parameters
    relevance_threshold=0.02,           # Minimum keyword score
    rate_limit_delay=1.0,               # Delay between LLM calls
    
    # Scraper parameters
    scraper_cache_dir="./scraper_cache",  # Cache location
    scraper_max_depth=3,                  # Max navigation depth
    scraper_request_delay=1.5,            # Delay between requests
    scraper_timeout=30,                   # Request timeout seconds
)
```

## Output Files

- `scraper.log` - Detailed log of scraping operations
- `scraper_cache/` - Cached extracted text (MD5 hash filenames)
- `output/{timestamp}_results.json` - Full results with summaries
- `output/{timestamp}_summary.csv` - Flat CSV for spreadsheet analysis

## Running the Example

Simply run:

```bash
python Ret\&summ.py
```

This will execute the `main_monthly_scrape()` function at the bottom of the file.

## Troubleshooting

### JavaScript-Heavy Sites
Some municipalities might use JavaScript to load content. If you encounter issues:

1. Install Selenium: `pip install selenium`
2. Modify `_fetch_html()` to use a headless browser
3. See inline comments in code for guidance

### Rate Limiting
If you get blocked by a website:
- Increase `scraper_request_delay` (try 2.0 or 3.0)
- Add random jitter: `time.sleep(random.uniform(1.0, 3.0))`
- Check `robots.txt` for the site

### Low Document Discovery
If few documents are found:
- Increase `scraper_max_depth` to 4 or 5
- Check scraper.log for details
- Manually inspect the website structure
- Add more keywords to `TARGET_PAGE_KEYWORDS`
