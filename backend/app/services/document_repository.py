import sqlite3
import logging
from typing import List, Dict, Any
from app.services.document_registry import DocumentRegistryDB

logger = logging.getLogger("app.services.document_repository")

class DocumentRepository:
    def __init__(self, db: DocumentRegistryDB):
        self.db = db

    def insert_document(self, metadata: dict) -> None:
        """Inserts a new document metadata row."""
        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO documents (
                    document_id, original_filename, stored_filename, upload_timestamp,
                    sha256_hash, file_size, page_count, chunk_count, vector_count,
                    embedding_model, status, processing_time, embedding_time
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                metadata["document_id"],
                metadata["original_filename"],
                metadata["stored_filename"],
                metadata["upload_timestamp"],
                metadata["sha256_hash"],
                metadata["file_size"],
                metadata["page_count"],
                metadata["chunk_count"],
                metadata["vector_count"],
                metadata["embedding_model"],
                metadata["status"],
                metadata.get("processing_time", 0.0),
                metadata.get("embedding_time", 0.0)
            ))
            conn.commit()
            self.db.create_backup()
        except sqlite3.Error as e:
            logger.error("Failed to insert document: %s", e)
            raise e
        finally:
            conn.close()

    def update_document(self, doc_id: str, updates: dict) -> None:
        """Updates specific columns of a document metadata row."""
        if not updates:
            return
        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
            values = list(updates.values())
            values.append(doc_id)
            cursor.execute(f"UPDATE documents SET {set_clause} WHERE document_id = ?;", values)
            conn.commit()
            self.db.create_backup()
        except sqlite3.Error as e:
            logger.error("Failed to update document metadata: %s", e)
            raise e
        finally:
            conn.close()

    def update_document_status(self, doc_id: str, status: str) -> None:
        """Helper to quickly update status of a document."""
        self.update_document(doc_id, {"status": status})

    def get_document(self, doc_id: str) -> dict | None:
        """Fetches metadata for a single document, even if status is not Ready."""
        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM documents WHERE document_id = ? AND status != 'Deleted';", (doc_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        except sqlite3.Error as e:
            logger.error("Failed to fetch document %s: %s", doc_id, e)
            return None
        finally:
            conn.close()

    def get_all_active_documents(self) -> List[dict]:
        """Fetches all documents that are not marked Deleted."""
        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM documents WHERE status != 'Deleted';")
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except sqlite3.Error as e:
            logger.error("Failed to fetch active documents: %s", e)
            return []
        finally:
            conn.close()

    def get_all_documents_including_deleted(self) -> List[dict]:
        """Fetches all documents database records."""
        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM documents;")
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except sqlite3.Error as e:
            logger.error("Failed to fetch all documents: %s", e)
            return []
        finally:
            conn.close()

    def get_candidates_for_dup_check(self, filename: str, file_size: int, page_count: int) -> List[dict]:
        """Fetches active documents matching the quick duplicate criteria (filename, size, pages)."""
        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM documents 
                WHERE original_filename = ? AND file_size = ? AND page_count = ? AND status != 'Deleted';
            """, (filename, file_size, page_count))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except sqlite3.Error as e:
            logger.error("Failed to query duplicate candidates: %s", e)
            return []
        finally:
            conn.close()

    def get_document_by_hash(self, sha256_hash: str) -> dict | None:
        """Fetches active document matching the SHA-256 hash."""
        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM documents WHERE sha256_hash = ? AND status != 'Deleted';", (sha256_hash,))
            row = cursor.fetchone()
            return dict(row) if row else None
        except sqlite3.Error as e:
            logger.error("Failed to fetch document by hash: %s", e)
            return None
        finally:
            conn.close()

    def delete_document_transactional(self, doc_id: str, chroma_callback, file_callback) -> dict:
        """
        Deletes a document's vector embeddings, database metadata, and physical storage file atomically.
        If any step fails, the metadata deletion is rolled back.
        """
        conn = self.db.get_connection()
        conn.execute("BEGIN TRANSACTION;")
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM documents WHERE document_id = ? AND status != 'Deleted';", (doc_id,))
            row = cursor.fetchone()
            if not row:
                raise sqlite3.Error(f"Document with ID '{doc_id}' not found or already deleted.")
            
            doc_dict = dict(row)

            # 1. Delete Chroma vectors
            logger.info("Delete Transaction [1/3]: Deleting vectors in ChromaDB...")
            deleted_vectors = chroma_callback(doc_id)

            # 2. Delete metadata in SQLite (mark as Deleted)
            logger.info("Delete Transaction [2/3]: Deleting metadata in SQLite registry...")
            cursor.execute("UPDATE documents SET status = 'Deleted' WHERE document_id = ?;", (doc_id,))

            # 3. Delete physical stored PDF file
            logger.info("Delete Transaction [3/3]: Deleting PDF from storage disk...")
            file_callback(doc_dict["stored_filename"])

            # If all operations complete successfully, commit transaction
            conn.commit()
            logger.info("Delete Transaction: Successfully committed transaction for document %s.", doc_id)
            self.db.create_backup()

            return {
                "success": True,
                "document_id": doc_id,
                "original_filename": doc_dict["original_filename"],
                "deleted_vectors": deleted_vectors,
                "file_deleted": True,
                "message": f"Document '{doc_dict['original_filename']}' was successfully deleted."
            }
        except Exception as e:
            conn.rollback()
            logger.error("Delete Transaction FAILED for document %s. Registry metadata rolled back to original state. Error: %s", doc_id, e)
            raise e
        finally:
            conn.close()
