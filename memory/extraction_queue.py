import sqlite3

from pathlib import Path
from datetime import datetime, timezone


class ExtractionQueue:

    def __init__(self):

        project_root = Path(__file__).resolve().parent.parent

        data_folder = project_root / "data"
        data_folder.mkdir(exist_ok=True)

        self.db_path = data_folder / "zorin_memory.db"

        self.initialize()

    def connect(self):

        return sqlite3.connect(
            self.db_path,
            timeout=10
        )

    def initialize(self):

        with self.connect() as connection:

            connection.execute("""
                CREATE TABLE IF NOT EXISTS extraction_queue (

                    id INTEGER PRIMARY KEY AUTOINCREMENT,

                    conversation TEXT NOT NULL,

                    status TEXT NOT NULL DEFAULT 'pending',

                    attempts INTEGER NOT NULL DEFAULT 0,

                    created_at TEXT NOT NULL,

                    processed_at TEXT
                )
            """)

            connection.execute("""
                CREATE INDEX IF NOT EXISTS
                idx_extraction_queue_status
                ON extraction_queue(status)
            """)

    def enqueue(self, conversation):

        if not conversation or len(conversation.strip()) < 30:
            return None

        with self.connect() as connection:

            cursor = connection.execute("""
                INSERT INTO extraction_queue (
                    conversation,
                    status,
                    attempts,
                    created_at
                )
                VALUES (?, 'pending', 0, ?)
            """, (
                conversation.strip(),
                datetime.now(timezone.utc).isoformat()
            ))

            return cursor.lastrowid

    def get_pending(self, limit=5):

        with self.connect() as connection:

            connection.row_factory = sqlite3.Row

            rows = connection.execute("""
                SELECT *
                FROM extraction_queue
                WHERE status = 'pending'
                ORDER BY id ASC
                LIMIT ?
            """, (limit,)).fetchall()

            return [dict(row) for row in rows]

    def mark_processing(self, queue_id):

        with self.connect() as connection:

            cursor = connection.execute("""
                UPDATE extraction_queue
                SET status = 'processing',
                    attempts = attempts + 1
                WHERE id = ?
                AND status = 'pending'
            """, (queue_id,))

            return cursor.rowcount > 0

    def mark_completed(self, queue_id):

        with self.connect() as connection:

            cursor = connection.execute("""
                UPDATE extraction_queue
                SET status = 'completed',
                    processed_at = ?
                WHERE id = ?
                AND status = 'processing'
            """, (
                datetime.now(timezone.utc).isoformat(),
                queue_id
            ))

            return cursor.rowcount > 0

    def mark_pending(self, queue_id):

        with self.connect() as connection:

            cursor = connection.execute("""
                UPDATE extraction_queue
                SET status = 'pending'
                WHERE id = ?
                AND status = 'processing'
            """, (queue_id,))

            return cursor.rowcount > 0

    def recover_processing(self):

        with self.connect() as connection:

            cursor = connection.execute("""
                UPDATE extraction_queue
                SET status = 'pending'
                WHERE status = 'processing'
            """)

            return cursor.rowcount

    def get_statistics(self):

        with self.connect() as connection:

            rows = connection.execute("""
                SELECT status, COUNT(*)
                FROM extraction_queue
                GROUP BY status
            """).fetchall()

            return dict(rows)