import json
import sqlite3
import threading
from typing import List, Optional

import sqlite_vec

from fpm.models import FailureEvent, WarningResult

EMBED_DIM = 384
MODEL_NAME = "all-MiniLM-L6-v2"


class FailureStore:
    """SQLite-backed storage with vector search for failure patterns.

    Uses ONE persistent connection (so ':memory:' works) guarded by a lock
    (so FastAPI's thread pool is safe).
    """

    def __init__(self, db_path: str = "failures.db", embedder=None):
        self.db_path = db_path
        self._embedder = embedder  # any object with .encode(text, normalize_embeddings=True)
        self._lock = threading.RLock()

        self.db = sqlite3.connect(db_path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self._load_vec()
        self._init_db()

    # ---------- setup ----------
    def _load_vec(self):
        try:
            self.db.enable_load_extension(True)
            sqlite_vec.load(self.db)
            self.db.enable_load_extension(False)
        except AttributeError as e:
            raise RuntimeError(
                "This Python's sqlite3 was built without extension loading. "
                "Use python.org / conda / pyenv (with --enable-loadable-sqlite-extensions) Python."
            ) from e

    @property
    def embedder(self):
        if self._embedder is None:
            from sentence_transformers import SentenceTransformer
            self._embedder = SentenceTransformer(MODEL_NAME)
        return self._embedder

    def _init_db(self):
        with self._lock, self.db:
            self.db.execute("""
                CREATE TABLE IF NOT EXISTS failures (
                    seq INTEGER PRIMARY KEY AUTOINCREMENT,
                    id TEXT UNIQUE NOT NULL,
                    timestamp TEXT,
                    error_category TEXT,
                    description TEXT,
                    task_type TEXT,
                    agent_id TEXT,
                    context_pattern TEXT,
                    root_cause TEXT,
                    resolution TEXT,
                    prevention TEXT,
                    severity TEXT,
                    tags TEXT
                )
            """)
            self.db.execute(
                f"CREATE VIRTUAL TABLE IF NOT EXISTS failure_vectors "
                f"USING vec0(embedding float[{EMBED_DIM}])"
            )

    # ---------- helpers ----------
    def _embed(self, text: str) -> bytes:
        vec = self.embedder.encode(text, normalize_embeddings=True)
        return sqlite_vec.serialize_float32([float(x) for x in vec])

    # ---------- public API ----------
    def record(self, event: FailureEvent) -> str:
        blob = self._embed(event.context_pattern)
        with self._lock, self.db:  # transaction: both inserts or neither
            cur = self.db.execute(
                """
                INSERT INTO failures (id, timestamp, error_category, description, task_type,
                    agent_id, context_pattern, root_cause, resolution, prevention, severity, tags)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.id,
                    event.timestamp.isoformat(),
                    event.error_category,
                    event.description,
                    event.task_type,
                    event.agent_id,
                    event.context_pattern,
                    event.root_cause,
                    event.resolution,
                    event.prevention,
                    event.severity,
                    json.dumps(event.tags),
                ),
            )
            self.db.execute(
                "INSERT INTO failure_vectors(rowid, embedding) VALUES (?, ?)",
                (cur.lastrowid, blob),
            )
        return event.id

    def find_warnings(self, task_description: str, top_k: int = 5,
                      min_similarity: float = 0.3) -> List[WarningResult]:
        blob = self._embed(task_description)
        with self._lock:
            rows = self.db.execute(
                """
                SELECT rowid, distance FROM failure_vectors
                WHERE embedding MATCH ? AND k = ?
                ORDER BY distance
                """,
                (blob, top_k),
            ).fetchall()

            results: List[WarningResult] = []
            for r in rows:
                # Vectors are unit-normalised, so cosine = 1 - (L2^2 / 2)
                similarity = max(0.0, 1.0 - (r["distance"] ** 2) / 2.0)
                if similarity < min_similarity:
                    continue
                f = self.db.execute(
                    "SELECT id, context_pattern, prevention, severity FROM failures WHERE seq = ?",
                    (r["rowid"],),
                ).fetchone()
                if f:
                    results.append(WarningResult(
                        failure_id=f["id"],
                        context_pattern=f["context_pattern"],
                        prevention=f["prevention"],
                        severity=f["severity"],
                        similarity=round(similarity, 3),
                    ))
        return results

    def get_all(self) -> List[dict]:
        with self._lock:
            rows = self.db.execute(
                "SELECT id, timestamp, error_category, description, task_type, agent_id, "
                "context_pattern, root_cause, resolution, prevention, severity, tags "
                "FROM failures ORDER BY seq DESC"
            ).fetchall()
        return [dict(r) for r in rows]

    def close(self):
        with self._lock:
            self.db.close()
