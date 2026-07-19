import os
import shutil
import sqlite3
import logging

logger = logging.getLogger("app.services.document_registry")

class DocumentRegistryDB:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.backup_path = db_path + ".bak"
        self._init_db()

    def _init_db(self):
        """Initializes the database schema, checking for corruption and recovering if needed."""
        # Ensure parent directory exists
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

        # Check for corruption and attempt recovery
        if os.path.exists(self.db_path):
            if not self._verify_integrity(self.db_path):
                logger.critical("Registry database '%s' is corrupted! Attempting recovery from backup...", self.db_path)
                self._recover_from_backup()
        elif os.path.exists(self.backup_path):
            logger.warning("Registry database missing but backup exists. Restoring from backup...")
            self._recover_from_backup()
            
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    document_id TEXT PRIMARY KEY,
                    original_filename TEXT NOT NULL,
                    stored_filename TEXT NOT NULL,
                    upload_timestamp TEXT NOT NULL,
                    sha256_hash TEXT NOT NULL,
                    file_size INTEGER NOT NULL,
                    page_count INTEGER NOT NULL,
                    chunk_count INTEGER NOT NULL,
                    vector_count INTEGER NOT NULL,
                    embedding_model TEXT NOT NULL,
                    status TEXT NOT NULL,
                    processing_time REAL DEFAULT 0.0,
                    embedding_time REAL DEFAULT 0.0
                );
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_documents_hash ON documents(sha256_hash);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status);")
            conn.commit()
            conn.close()
            logger.info("SQLite registry tables initialized successfully.")
        except Exception as e:
            logger.critical("Failed to initialize SQLite registry database: %s", e, exc_info=True)
            raise e

    def get_connection(self) -> sqlite3.Connection:
        """Returns a new connection to the SQLite database with dict-like row factory."""
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _verify_integrity(self, path: str) -> bool:
        """Checks the integrity of the SQLite database file using PRAGMA integrity_check."""
        try:
            conn = sqlite3.connect(path, timeout=5.0)
            cursor = conn.cursor()
            cursor.execute("PRAGMA integrity_check;")
            row = cursor.fetchone()
            conn.close()
            if row and row[0] == "ok":
                return True
            return False
        except Exception as e:
            logger.error("Database integrity check failed for '%s': %s", path, e)
            return False

    def _recover_from_backup(self) -> None:
        """Copies the backup registry to the main database file."""
        if os.path.exists(self.backup_path):
            if self._verify_integrity(self.backup_path):
                try:
                    # Remove corrupt file first to avoid locking errors on copy
                    if os.path.exists(self.db_path):
                        os.remove(self.db_path)
                    shutil.copy2(self.backup_path, self.db_path)
                    logger.info("Registry database successfully recovered from backup file '%s'.", self.backup_path)
                except Exception as e:
                    logger.critical("Failed to restore database from backup: %s", e, exc_info=True)
            else:
                logger.error("Backup file '%s' is also corrupted! Cannot perform recovery.", self.backup_path)
        else:
            logger.error("No backup file '%s' found. Automatic recovery is impossible.", self.backup_path)

    def create_backup(self) -> None:
        """Creates a hot copy backup of the current database file."""
        try:
            if os.path.exists(self.db_path):
                shutil.copy2(self.db_path, self.backup_path)
                logger.info("Registry backup file created/updated at '%s'", self.backup_path)
        except Exception as e:
            logger.error("Failed to create registry backup copy: %s", e, exc_info=True)
