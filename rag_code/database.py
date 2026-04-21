
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

CREATE_ARCHIVE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS archived_documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    original_id INTEGER,
    municipality TEXT NOT NULL,
    url TEXT NOT NULL,
    doc_type TEXT,
    summary TEXT,
    key_findings TEXT,
    relevance_score REAL,
    raw_text TEXT,
    scraped_at TIMESTAMP,
    archived_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
    """Creates the database and the documents / archive tables if they don't exist."""
    try:
        with get_db_connection() as conn:
            conn.execute(CREATE_TABLE_SQL)
            conn.execute(CREATE_ARCHIVE_TABLE_SQL)
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
            query = "SELECT id, municipality, url, doc_type, summary, key_findings, relevance_score, scraped_at FROM documents WHERE raw_text LIKE ?"
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
            results = conn.execute("SELECT DISTINCT municipality FROM documents WHERE municipality IS NOT NULL ORDER BY municipality").fetchall()
            return [row['municipality'] for row in results]
    except sqlite3.Error as e:
        logger.error(f"Failed to get municipalities: {e}")
        return []
def delete_document(doc_id: int):
    """Hard-deletes a document from the documents table by its ID."""
    try:
        with get_db_connection() as conn:
            conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
            logger.info(f"Successfully deleted document with ID: {doc_id}")
    except sqlite3.Error as e:
        logger.error(f"Failed to delete document {doc_id}: {e}")


def archive_document(doc_id: int):
    """Moves a document from documents into archived_documents (soft delete)."""
    try:
        with get_db_connection() as conn:
            row = conn.execute(
                "SELECT * FROM documents WHERE id = ?", (doc_id,)
            ).fetchone()
            if row is None:
                logger.warning(f"archive_document: no document found with id={doc_id}")
                return
            conn.execute(
                """
                INSERT INTO archived_documents
                    (original_id, municipality, url, doc_type, summary,
                     key_findings, relevance_score, raw_text, scraped_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row["id"], row["municipality"], row["url"], row["doc_type"],
                    row["summary"], row["key_findings"], row["relevance_score"],
                    row["raw_text"], row["scraped_at"],
                ),
            )
            conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
            logger.info(f"Archived document id={doc_id}")
    except sqlite3.Error as e:
        logger.error(f"Failed to archive document {doc_id}: {e}")


def get_archived_documents() -> list[dict]:
    """Returns all documents in the archive, newest first."""
    try:
        with get_db_connection() as conn:
            rows = conn.execute(
                """
                SELECT id, original_id, municipality, url, doc_type, summary,
                       key_findings, relevance_score, scraped_at, archived_at
                FROM archived_documents
                ORDER BY archived_at DESC
                """
            ).fetchall()
            return [dict(r) for r in rows]
    except sqlite3.Error as e:
        logger.error(f"Failed to fetch archived documents: {e}")
        return []


def restore_document(archive_id: int):
    """Moves a document from archived_documents back into documents."""
    try:
        with get_db_connection() as conn:
            row = conn.execute(
                "SELECT * FROM archived_documents WHERE id = ?", (archive_id,)
            ).fetchone()
            if row is None:
                logger.warning(f"restore_document: no archive row id={archive_id}")
                return
            conn.execute(
                """
                INSERT INTO documents
                    (municipality, url, doc_type, summary, key_findings,
                     relevance_score, raw_text, scraped_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(url) DO UPDATE SET
                    doc_type=excluded.doc_type,
                    summary=excluded.summary,
                    key_findings=excluded.key_findings,
                    relevance_score=excluded.relevance_score,
                    raw_text=excluded.raw_text,
                    scraped_at=excluded.scraped_at
                """,
                (
                    row["municipality"], row["url"], row["doc_type"],
                    row["summary"], row["key_findings"], row["relevance_score"],
                    row["raw_text"], row["scraped_at"],
                ),
            )
            conn.execute("DELETE FROM archived_documents WHERE id = ?", (archive_id,))
            logger.info(f"Restored archive row id={archive_id} back to documents")
    except sqlite3.Error as e:
        logger.error(f"Failed to restore archive row {archive_id}: {e}")


def permanently_delete_archived(archive_id: int):
    """Permanently removes a document from the archive."""
    try:
        with get_db_connection() as conn:
            conn.execute("DELETE FROM archived_documents WHERE id = ?", (archive_id,))
            logger.info(f"Permanently deleted archive row id={archive_id}")
    except sqlite3.Error as e:
        logger.error(f"Failed to permanently delete archive row {archive_id}: {e}")
