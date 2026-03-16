"""
PostgreSQL-backed vector database.

Stores embeddings as FLOAT4[] in a Postgres table and caches them in
memory as numpy arrays for fast cosine-similarity search.  Unlike the
file-based store, data persists across Railway (ephemeral) container
restarts and re-deploys.
"""

import logging
import numpy as np
from typing import List, Dict, Any, Optional
from psycopg2.extras import RealDictCursor, execute_batch, Json

logger = logging.getLogger(__name__)


class PostgresVectorDatabase:
    """
    Vector database backed by PostgreSQL.

    On initialisation all stored vectors are loaded into in-memory numpy
    arrays so that search is as fast as the file-based implementation.
    Writes go to Postgres first, then the in-memory cache is refreshed.
    """

    def __init__(self, postgres_db, vector_size: int = 384):
        """
        Args:
            postgres_db: An initialised PostgresDatabase instance whose
                         connection pool is already open.
            vector_size: Expected embedding dimension (e.g. 384 for
                         all-MiniLM-L6-v2, 768 for all-mpnet-base-v2).
        """
        self.pg = postgres_db
        self.vector_size = vector_size
        self.ids: List[str] = []
        self.vectors: np.ndarray = np.empty((0, vector_size), dtype=np.float32)
        self.metadata: List[Dict[str, Any]] = []
        self._load_into_memory()
        logger.info(
            f"PostgresVectorDatabase initialised with {len(self.ids)} embeddings "
            f"(vector_size={self.vector_size})"
        )

    def _load_into_memory(self) -> None:
        """Fetch all rows from vector_embeddings into numpy arrays."""
        conn = self.pg._get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        try:
            cur.execute("SELECT id, vector, metadata FROM vector_embeddings")
            rows = cur.fetchall()
            if rows:
                self.ids = [str(r["id"]) for r in rows]
                self.vectors = np.array(
                    [r["vector"] for r in rows], dtype=np.float32
                )
                self.metadata = [r["metadata"] or {} for r in rows]
                if self.vectors.shape[0] > 0:
                    self.vector_size = self.vectors.shape[1]
            else:
                self.ids = []
                self.vectors = np.empty((0, self.vector_size), dtype=np.float32)
                self.metadata = []
        finally:
            cur.close()
            self.pg._put_connection(conn)

    def batch_insert(
        self, items: List[tuple]
    ) -> None:
        """
        Insert or update multiple vectors in a single transaction.

        Args:
            items: List of (media_id, vector, metadata) tuples where
                   vector is a list/array of floats.
        """
        if not items:
            return
        conn = self.pg._get_connection()
        cur = conn.cursor()
        try:
            execute_batch(
                cur,
                """
                INSERT INTO vector_embeddings (id, vector, metadata)
                VALUES (%s, %s::float4[], %s)
                ON CONFLICT (id) DO UPDATE
                    SET vector   = EXCLUDED.vector,
                        metadata = EXCLUDED.metadata
                """,
                [
                    (
                        str(item_id),
                        list(map(float, vec)),
                        Json(meta or {}),
                    )
                    for item_id, vec, meta in items
                ],
                page_size=500,
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()
            self.pg._put_connection(conn)
        self._load_into_memory()

    def insert(
        self,
        media_id: str,
        vector: List[float],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Insert or update a single vector."""
        self.batch_insert([(media_id, vector, metadata or {})])

    def search(
        self,
        query_vector: List[float],
        top_k: int = 5,
        score_threshold: Optional[float] = None,
        filter: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Find the top-k most similar vectors using cosine similarity.

        Args:
            query_vector: Query embedding as a list of floats.
            top_k:        Number of results to return.
            score_threshold: Minimum similarity score (0-1).
            filter:       Ignored (kept for interface compatibility).

        Returns:
            List of {'id': str, 'score': float} dicts, sorted descending.
        """
        if len(self.ids) == 0:
            return []

        q = np.array(query_vector, dtype=np.float32)
        q_norm = np.linalg.norm(q)
        if q_norm == 0:
            return []

        v_norms = np.linalg.norm(self.vectors, axis=1)
        sims = np.dot(self.vectors, q) / (v_norms * q_norm + 1e-10)

        if score_threshold is not None:
            valid = np.where(sims >= score_threshold)[0]
        else:
            valid = np.arange(len(sims))

        if len(valid) == 0:
            return []

        k = min(top_k, len(valid))
        top_local = np.argsort(sims[valid])[-k:][::-1]
        top_global = valid[top_local]

        return [
            {"id": self.ids[i], "score": float(sims[i])} for i in top_global
        ]

    def count(self) -> int:
        return len(self.ids)

    def delete(self, media_id: str) -> bool:
        if media_id not in self.ids:
            return False
        conn = self.pg._get_connection()
        cur = conn.cursor()
        try:
            cur.execute(
                "DELETE FROM vector_embeddings WHERE id = %s", (media_id,)
            )
            conn.commit()
        finally:
            cur.close()
            self.pg._put_connection(conn)
        self._load_into_memory()
        return True

    def clear(self) -> None:
        conn = self.pg._get_connection()
        cur = conn.cursor()
        try:
            cur.execute("TRUNCATE vector_embeddings")
            conn.commit()
        finally:
            cur.close()
            self.pg._put_connection(conn)
        self._load_into_memory()
        logger.info("Cleared all vector embeddings")

    def close(self) -> None:
        logger.info("PostgresVectorDatabase closed")
