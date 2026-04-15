# Requirements & User Stories

This document outlines the functional and non-functional requirements for the SC-Coasts: Coastal Resilience Document Analyzer, along with user stories that illustrate its intended use.

## 1. Functional Requirements

- **FR1: Web Scraping**: The system must be able to crawl a given municipal website, starting from a base URL.
- **FR2: PDF Discovery**: The system must identify and download PDF documents found during the crawl.
- **FR3: Text Extraction**: The system must extract the full raw text from each downloaded PDF.
- **FR4: Keyword Scanning**: The system must scan the extracted text for a predefined list of keywords to determine initial relevance.
- **FR5: AI Summarization**: The system must use a local Large Language Model (via Ollama) to generate a summary and key findings for relevant documents.
- **FR6: Persistent Storage**: The system must save all processed document data, including summaries and raw text, to a local SQLite database.
- **FR7: Document Search**: The system must provide an interface for users to perform full-text searches across the entire database of stored documents.
- **FR8: Filter by Municipality**: The search functionality must allow users to filter results by municipality.
- **FR9: UI Feedback**: The system must provide real-time feedback during the scraping process (e.g., a progress bar and status text).

## 2. Non-Functional Requirements

- **NFR1: Local First**: The application, including the AI model, must run entirely on the user's local machine, requiring no internet connection for processing (aside from the initial scrape).
- **NFR2: No API Keys**: The application must not require any paid cloud service API keys to function.
- **NFR3: Modularity**: The code must be organized into logical modules (e.g., UI, database, scraper) to facilitate future maintenance and development.
- **NFR4: User-Friendliness**: The user interface must be intuitive and easy to navigate for non-technical users.

## 3. User Stories

**User Story 1: Populating the Library**

- **As a** policy researcher,
- **I want to** select a coastal municipality and have the application automatically find and process all their relevant public documents,
- **So that** I can build a comprehensive library of local ordinances and plans without having to manually search their websites.

**User Story 2: Searching for a Specific Topic**

- **As a** graduate student,
- **I want to** search my entire library of documents for the term "beach nourishment",
- **So that** I can quickly find all ordinances and reports related to that specific topic across multiple municipalities.

**User Story 3: Reviewing a Document**

- **As a** community planner,
- **I want to** see an AI-generated summary and a list of key findings for a search result,
- **So that** I can quickly understand the gist of a document without having to read the entire thing.

**User Story 4: Accessing the Original Source**

- **As a** legal analyst,
- **I want to** have a direct link to the original PDF document from the search results,
- **So that** I can easily cite the source and verify the information in its original context.

**User Story 5: Expanding the Library**

- **As a** researcher,
- **I want to** be able to scrape new municipalities at any time,
- **So that** my document library can grow and stay up-to-date as my research expands.

