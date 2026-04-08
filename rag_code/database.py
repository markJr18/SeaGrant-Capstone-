
import sqlite3
import logging

# --- Database Configuration ---
DB_FILE = "document_library.db"

# --- Database Schema ---
CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    municipality TEXT NOT NULL,
    url TEXT NOT NULL UNIQUE,
    doc_type TEXT,
    summary TEXT,
    key_findings TEXT,
    relevance_score REAL,
    raw_text TEXT,
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

# --- Logging Setup ---
logger = logging.getLogger(__name__)

# --- Database Functions ---

def get_db_connection():
    """Establishes a connection to the SQLite database."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def initialize_database():
    """Creates the database and the documents table if they don't exist."""
    try:
        with get_db_connection() as conn:
            conn.execute(CREATE_TABLE_SQL)
            logger.info("Database initialized successfully.")
    except sqlite3.Error as e:
        logger.error(f"Database initialization failed: {e}")
        raise

def add_document(doc_data: dict):
    """Adds a new document to the database or updates it if it already exists."""
    
    # Ensure key_findings is a string (e.g., JSON)
    if isinstance(doc_data.get('key_findings'), list):
        import json
        doc_data['key_findings'] = json.dumps(doc_data['key_findings'])

    sql = """
    INSERT INTO documents (municipality, url, doc_type, summary, key_findings, relevance_score, raw_text)
    VALUES (:municipality, :url, :doc_type, :summary, :key_findings, :relevance_score, :raw_text)
    ON CONFLICT(url) DO UPDATE SET
        doc_type=excluded.doc_type,
        summary=excluded.summary,
        key_findings=excluded.key_findings,
        relevance_score=excluded.relevance_score,
        raw_text=excluded.raw_text,
        scraped_at=CURRENT_TIMESTAMP;
    """
    try:
        with get_db_connection() as conn:
            conn.execute(sql, doc_data)
            logger.info(f"Successfully added/updated document: {doc_data['url']}")
    except sqlite3.Error as e:
        logger.error(f"Failed to add/update document {doc_data['url']}: {e}")

def search_documents(search_term: str, municipality: str = None) -> list:
    """
    Searches the database for documents containing the search term.
    Can be filtered by municipality.
    """
    try:
        with get_db_connection() as conn:
            query = "SELECT * FROM documents WHERE raw_text LIKE ?"
            params = [f'%{search_term}%']

            if municipality and municipality != "All":
                query += " AND municipality = ?"
                params.append(municipality)
            
            query += " ORDER BY relevance_score DESC"

            results = conn.execute(query, params).fetchall()
            logger.info(f"Found {len(results)} documents for search term '{search_term}' in '{municipality or 'All'}'.")
            return [dict(row) for row in results]
    except sqlite3.Error as e:
        logger.error(f"Search failed: {e}")
        return []

def get_all_municipalities() -> list[str]:
    """Returns a list of all unique municipalities in the database."""
    try:
        with get_db_connection() as conn:
            results = conn.execute("SELECT DISTINCT municipality FROM documents ORDER BY municipality").fetchall()
            return [row['municipality'] for row in results]
    except sqlite3.Error as e:
        logger.error(f"Failed to get municipalities: {e}")
        return []
def delete_document(doc_id: int):
    """Deletes a document from the database by its ID."""
    try:
        with get_db_connection() as conn:
            conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
            logger.info(f"Successfully deleted document with ID: {doc_id}")
    except sqlite3.Error as e:
        logger.error(f"Failed to delete document {doc_id}: {e}")
