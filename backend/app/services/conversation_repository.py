import sqlite3
import logging
import json
import time
from typing import List, Dict, Any

logger = logging.getLogger("app.services.conversation_repository")

class ConversationRepository:
    """Repository to manage session, message, summary persistence and FTS index in unified SQLite DB."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Helper to get a connection and enable foreign keys and dictionary row factory."""
        conn = sqlite3.connect(self.db_path, timeout=15.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def _init_db(self) -> None:
        """Initializes tables, FTS virtual table, and sync triggers."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            
            # 1. Sessions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    created_time TEXT NOT NULL,
                    updated_time TEXT NOT NULL,
                    message_count INTEGER DEFAULT 0,
                    document_filter TEXT,
                    summary TEXT,
                    status TEXT NOT NULL DEFAULT 'active',
                    last_accessed TEXT NOT NULL,
                    total_tokens INTEGER DEFAULT 0,
                    favorite INTEGER DEFAULT 0,
                    archived INTEGER DEFAULT 0,
                    pinned INTEGER DEFAULT 0
                );
            """)

            # 2. Messages table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    message_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    prompt_tokens INTEGER DEFAULT 0,
                    completion_tokens INTEGER DEFAULT 0,
                    response_time REAL DEFAULT 0.0,
                    is_summarized INTEGER DEFAULT 0,
                    citations TEXT,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
                );
            """)

            # 3. Conversation summaries table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversation_summaries (
                    summary_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    created_time TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
                );
            """)

            # 4. FTS5 Virtual Table for Messages
            cursor.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(
                    message_id UNINDEXED,
                    session_id UNINDEXED,
                    role UNINDEXED,
                    content
                );
            """)

            # 5. SQLite triggers to automatically sync messages to messages_fts
            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS after_messages_insert AFTER INSERT ON messages BEGIN
                    INSERT INTO messages_fts(message_id, session_id, role, content)
                    VALUES (new.message_id, new.session_id, new.role, new.content);
                END;
            """)

            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS after_messages_delete AFTER DELETE ON messages BEGIN
                    DELETE FROM messages_fts WHERE message_id = old.message_id;
                END;
            """)

            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS after_messages_update AFTER UPDATE ON messages BEGIN
                    UPDATE messages_fts SET content = new.content WHERE message_id = old.message_id;
                END;
            """)

            # Indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_summaries_session ON conversation_summaries(session_id);")

            conn.commit()
            logger.info("Unified database tables and FTS5 triggers initialized successfully.")
        except Exception as e:
            logger.critical("Failed to initialize conversational memory schema: %s", e, exc_info=True)
            raise e
        finally:
            conn.close()

    # --- Session operations ---

    def create_session(self, session_dict: Dict[str, Any]) -> None:
        """Inserts a new session metadata row."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO sessions (
                    session_id, title, created_time, updated_time, message_count,
                    document_filter, summary, status, last_accessed, total_tokens,
                    favorite, archived, pinned
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                session_dict["session_id"],
                session_dict["title"],
                session_dict["created_time"],
                session_dict["updated_time"],
                session_dict.get("message_count", 0),
                session_dict.get("document_filter"),
                session_dict.get("summary"),
                session_dict.get("status", "active"),
                session_dict["last_accessed"],
                session_dict.get("total_tokens", 0),
                1 if session_dict.get("favorite") else 0,
                1 if session_dict.get("archived") else 0,
                1 if session_dict.get("pinned") else 0
            ))
            conn.commit()
            logger.info("Session %s created in SQLite registry.", session_dict["session_id"])
        except sqlite3.Error as e:
            logger.error("Failed to create session: %s", e)
            raise e
        finally:
            conn.close()

    def get_session(self, session_id: str) -> Dict[str, Any] | None:
        """Fetches metadata for a single session."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM sessions WHERE session_id = ?;", (session_id,))
            row = cursor.fetchone()
            if row:
                res = dict(row)
                res["favorite"] = bool(res["favorite"])
                res["archived"] = bool(res["archived"])
                res["pinned"] = bool(res["pinned"])
                return res
            return None
        except sqlite3.Error as e:
            logger.error("Failed to fetch session %s: %s", session_id, e)
            return None
        finally:
            conn.close()

    def list_sessions(self) -> List[Dict[str, Any]]:
        """Lists all active (non-archived) sessions, ordered by pinned DESC, last_accessed DESC."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM sessions ORDER BY pinned DESC, last_accessed DESC;")
            rows = cursor.fetchall()
            sessions_list = []
            for row in rows:
                res = dict(row)
                res["favorite"] = bool(res["favorite"])
                res["archived"] = bool(res["archived"])
                res["pinned"] = bool(res["pinned"])
                sessions_list.append(res)
            return sessions_list
        except sqlite3.Error as e:
            logger.error("Failed to list sessions: %s", e)
            return []
        finally:
            conn.close()

    def update_session(self, session_id: str, updates: Dict[str, Any]) -> None:
        """Updates specific columns of a session."""
        if not updates:
            return
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
            values = []
            for k, v in updates.items():
                if k in ["favorite", "pinned", "archived"]:
                    values.append(1 if v else 0)
                else:
                    values.append(v)
            values.append(session_id)
            cursor.execute(f"UPDATE sessions SET {set_clause} WHERE session_id = ?;", values)
            conn.commit()
            logger.info("Session %s updated with: %s", session_id, list(updates.keys()))
        except sqlite3.Error as e:
            logger.error("Failed to update session %s: %s", session_id, e)
            raise e
        finally:
            conn.close()

    def delete_session(self, session_id: str) -> None:
        """Deletes a session and cascadingly removes its history and summaries."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM sessions WHERE session_id = ?;", (session_id,))
            conn.commit()
            logger.info("Session %s successfully deleted.", session_id)
        except sqlite3.Error as e:
            logger.error("Failed to delete session %s: %s", session_id, e)
            raise e
        finally:
            conn.close()

    # --- Message operations ---

    def add_message(self, message_dict: Dict[str, Any]) -> None:
        """Stores a message permanently and updates session metadata inside a transaction."""
        conn = self._get_connection()
        conn.execute("BEGIN TRANSACTION;")
        try:
            cursor = conn.cursor()
            
            # Save the message
            cursor.execute("""
                INSERT INTO messages (
                    message_id, session_id, role, content, timestamp,
                    prompt_tokens, completion_tokens, response_time, is_summarized, citations
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                message_dict["message_id"],
                message_dict["session_id"],
                message_dict["role"],
                message_dict["content"],
                message_dict["timestamp"],
                message_dict.get("prompt_tokens", 0),
                message_dict.get("completion_tokens", 0),
                message_dict.get("response_time", 0.0),
                1 if message_dict.get("is_summarized") else 0,
                json.dumps(message_dict.get("citations", []))
            ))
            
            # Increment message count, last accessed, and total tokens in the session table
            cursor.execute("""
                UPDATE sessions 
                SET message_count = message_count + 1,
                    last_accessed = ?,
                    updated_time = ?,
                    total_tokens = total_tokens + ?
                WHERE session_id = ?;
            """, (
                message_dict["timestamp"],
                message_dict["timestamp"],
                message_dict.get("prompt_tokens", 0) + message_dict.get("completion_tokens", 0),
                message_dict["session_id"]
            ))
            
            conn.commit()
            logger.info("Message %s saved, session %s metadata updated.", message_dict["message_id"], message_dict["session_id"])
        except Exception as e:
            conn.rollback()
            logger.error("Failed to add message and update session: %s", e)
            raise e
        finally:
            conn.close()

    def get_session_messages(self, session_id: str, include_summarized: bool = True) -> List[Dict[str, Any]]:
        """Loads messages for a session, optionally filtering out summarized messages."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            if include_summarized:
                cursor.execute("SELECT * FROM messages WHERE session_id = ? ORDER BY timestamp ASC;", (session_id,))
            else:
                cursor.execute("SELECT * FROM messages WHERE session_id = ? AND is_summarized = 0 ORDER BY timestamp ASC;", (session_id,))
            
            rows = cursor.fetchall()
            messages = []
            for row in rows:
                m = dict(row)
                m["is_summarized"] = bool(m["is_summarized"])
                m["citations"] = json.loads(m["citations"]) if m["citations"] else []
                messages.append(m)
            return messages
        except sqlite3.Error as e:
            logger.error("Failed to load messages for session %s: %s", session_id, e)
            return []
        finally:
            conn.close()

    def mark_messages_as_summarized(self, session_id: str, message_ids: List[str]) -> None:
        """Marks a block of messages as summarized."""
        if not message_ids:
            return
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            placeholders = ",".join(["?" for _ in message_ids])
            cursor.execute(f"""
                UPDATE messages 
                SET is_summarized = 1 
                WHERE session_id = ? AND message_id IN ({placeholders});
            """, [session_id] + message_ids)
            conn.commit()
            logger.info("Marked %d messages as summarized in session %s.", len(message_ids), session_id)
        except sqlite3.Error as e:
            logger.error("Failed to mark messages summarized: %s", e)
            raise e
        finally:
            conn.close()

    # --- Conversation Summaries ---

    def add_summary(self, summary_id: str, session_id: str, summary: str, created_time: str) -> None:
        """Stores a new summary chunk and updates the session's cumulative summary in a transaction."""
        conn = self._get_connection()
        conn.execute("BEGIN TRANSACTION;")
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO conversation_summaries (summary_id, session_id, summary, created_time)
                VALUES (?, ?, ?, ?);
            """, (summary_id, session_id, summary, created_time))
            
            cursor.execute("UPDATE sessions SET summary = ?, updated_time = ? WHERE session_id = ?;", (summary, created_time, session_id))
            conn.commit()
            logger.info("Saved summary %s and updated session %s summary.", summary_id, session_id)
        except Exception as e:
            conn.rollback()
            logger.error("Failed to add summary: %s", e)
            raise e
        finally:
            conn.close()

    # --- Full Text Search ---

    def search_messages(self, query_str: str, session_id: str | None = None) -> List[Dict[str, Any]]:
        """Uses SQLite FTS5 index to search across message contents."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            # We match content against query_str and join sessions/messages to return full context
            if session_id:
                cursor.execute("""
                    SELECT m.*, s.title as session_title
                    FROM messages_fts fts
                    JOIN messages m ON fts.message_id = m.message_id
                    JOIN sessions s ON m.session_id = s.session_id
                    WHERE fts.content MATCH ? AND m.session_id = ?
                    ORDER BY m.timestamp DESC;
                """, (query_str, session_id))
            else:
                cursor.execute("""
                    SELECT m.*, s.title as session_title
                    FROM messages_fts fts
                    JOIN messages m ON fts.message_id = m.message_id
                    JOIN sessions s ON m.session_id = s.session_id
                    WHERE fts.content MATCH ?
                    ORDER BY m.timestamp DESC;
                """, (query_str,))
            
            rows = cursor.fetchall()
            results = []
            for row in rows:
                m = dict(row)
                m["is_summarized"] = bool(m["is_summarized"])
                m["citations"] = json.loads(m["citations"]) if m["citations"] else []
                results.append(m)
            logger.info("FTS Search match count: %d for query: '%s'", len(results), query_str)
            return results
        except sqlite3.Error as e:
            logger.error("FTS Search failed for query '%s': %s", query_str, e)
            return []
        finally:
            conn.close()

    # --- Analytics & Statistics Queries ---

    def get_chat_analytics(self) -> Dict[str, Any]:
        """Runs aggregation queries to return Sprint 9 conversational metrics."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            
            # Basic Session/Message counts
            cursor.execute("SELECT COUNT(*) FROM sessions;")
            total_sessions = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM messages;")
            total_messages = cursor.fetchone()[0]

            # Avg session length
            cursor.execute("SELECT AVG(message_count) FROM sessions;")
            avg_session_length = cursor.fetchone()[0] or 0.0
            avg_session_length = round(avg_session_length, 2)

            # Longest conversation
            cursor.execute("SELECT MAX(message_count) FROM sessions;")
            longest_conversation = cursor.fetchone()[0] or 0

            # Avg response time
            cursor.execute("SELECT AVG(response_time) FROM messages WHERE role = 'assistant';")
            avg_response_time = cursor.fetchone()[0] or 0.0
            avg_response_time = round(avg_response_time, 4)

            # Token averages
            cursor.execute("SELECT SUM(prompt_tokens), SUM(completion_tokens) FROM messages;")
            sum_tokens_row = cursor.fetchone()
            sum_prompt = sum_tokens_row[0] or 0
            sum_completion = sum_tokens_row[1] or 0
            total_tokens = sum_prompt + sum_completion

            cursor.execute("SELECT AVG(prompt_tokens + completion_tokens) FROM messages;")
            avg_tokens = cursor.fetchone()[0] or 0.0
            avg_tokens = round(avg_tokens, 2)

            # Most active session
            cursor.execute("SELECT session_id, title, message_count FROM sessions ORDER BY message_count DESC LIMIT 1;")
            active_row = cursor.fetchone()
            most_active_session = dict(active_row) if active_row else None

            # Summaries generated
            cursor.execute("SELECT COUNT(*) FROM conversation_summaries;")
            total_summaries = cursor.fetchone()[0]

            cursor.execute("SELECT AVG(LENGTH(summary)) FROM conversation_summaries;")
            avg_summary_len = cursor.fetchone()[0] or 0.0
            avg_summary_len = round(avg_summary_len, 2)

            # Fallback response count vs total assistant answers (grounding quality metric)
            cursor.execute("""
                SELECT COUNT(*) FROM messages 
                WHERE role = 'assistant' 
                  AND content LIKE '%couldn''t find sufficient information%';
            """)
            fallback_responses = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM messages WHERE role = 'assistant';")
            total_answers = cursor.fetchone()[0] or 1
            fallback_rate = round(fallback_responses / total_answers, 4)

            return {
                "total_sessions": total_sessions,
                "total_messages": total_messages,
                "average_session_length": avg_session_length,
                "longest_conversation": longest_conversation,
                "average_response_time_seconds": avg_response_time,
                "total_tokens_consumed": total_tokens,
                "average_tokens_per_message": avg_tokens,
                "most_active_session": most_active_session,
                "total_summaries_generated": total_summaries,
                "average_summary_length_chars": avg_summary_len,
                "fallback_response_rate": fallback_rate
            }
        except sqlite3.Error as e:
            logger.error("Failed to compile chat analytics: %s", e)
            return {}
        finally:
            conn.close()
