# Product Design Document: SC-Coasts Analyzer

## 1. Overview

The SC-Coasts: Coastal Resilience Document Analyzer is a Python-based web application designed to help researchers and policymakers find and analyze public documents from South Carolina's coastal municipalities. The application automates the tedious process of searching local government websites by providing a tool to scrape, summarize, and create a searchable library of relevant documents.

The system is built around a "scrape-and-search" model. A user can direct the application to scrape a target municipal website. The scraper finds and downloads PDF documents, uses a local Large Language Model (LLM) via Ollama to generate summaries, and then saves everything into a persistent SQLite database. The user can then use a simple search interface to perform full-text searches across this entire library of documents.

## 2. System Architecture

The application is composed of four primary components that work together:

![Architecture Diagram](https://i.imgur.com/your-architecture-diagram.png) *Placeholder for a visual diagram.*

### 2.1. Streamlit Web Interface (`app.py`)

The entire user experience is managed by a Streamlit web application. This provides a simple, interactive UI that runs locally.

- **UI Structure**: The UI is organized into two main tabs:
    - **Search Library**: The primary interface for searching the document database.
    - **Add to Library (Scrape)**: The interface for controlling the web scraper.
- **State Management**: It uses Streamlit's `session_state` to maintain the user's search results and other UI-related data between interactions.

### 2.2. RAG & Scraper Core (`rag_code/ret_summ.py`)

This is the engine of the application. The `RetrievalSummarizationNetwork` class orchestrates the scraping, processing, and summarization workflow.

- **Web Scraping**: It uses the `requests` and `BeautifulSoup` libraries to recursively crawl websites, identify links, and find PDF documents.
- **Document Processing**: For each PDF found, it uses `pdfplumber` to extract the raw text content.
- **Relevance Scoring**: A `KeywordScanner` performs a cheap, initial scan of the raw text to determine if a document is potentially relevant based on a predefined list of keywords.
- **Summarization**: Documents that meet the relevance threshold are sent to the Ollama client for summarization.

### 2.3. Ollama LLM Integration

To provide AI-powered summaries without relying on paid cloud APIs, the application integrates with a local Ollama instance.

- **Local First**: All AI processing happens on the user's machine, ensuring privacy and eliminating API costs.
- **LangChain Wrapper**: The `ChatOllama` class from the `langchain-community` library is used to provide a simple, high-level interface to the local LLM.
- **JSON Output**: The model is prompted to return structured JSON, making the summary, key findings, and other data easy to parse and display.

### 2.4. SQLite Database (`rag_code/database.py`)

To create a persistent, searchable library, the application uses a lightweight, file-based SQLite database.

- **Schema**: A single table, `documents`, stores all the extracted information, including the municipality, URL, summary, key findings, and the full raw text for searching.
- **Persistence**: The database file (`document_library.db`) is stored locally, so the library grows with each successful scrape and persists between application runs.
- **Search**: The database is indexed for efficient full-text search, allowing users to quickly find documents containing specific keywords.

## 3. UI/UX Flow

1.  **Initial View (Search)**: The user is first presented with the "Search Library" tab, encouraging a search-first approach.
2.  **Building the Library**: If the user wants to add new documents, they navigate to the "Add to Library" tab.
3.  **Scraping**: The user selects a municipality and clicks "Start Scraping." A progress bar provides real-time feedback as documents are found and processed.
4.  **Saving**: Each successfully processed document is automatically saved to the SQLite database.
5.  **Searching**: The user returns to the "Search" tab, enters a keyword, and optionally filters by municipality.
6.  **Viewing Results**: Search results are displayed in a clean, card-based format. Each card shows the document title and can be expanded to view the full summary, key findings, and a direct link to the original PDF.

