"""
Dictionary Cache - Unified 30-Day Cache Manager
Centralized caching for all dictionary lookups (MW, RAE, etc.)
Reduces API calls and web scraping by 90%
"""

import sqlite3
import json
from typing import Dict, List, Optional, Any, Tuple  # ← THIS WAS THE BUG
from datetime import datetime, timedelta
import logging
import hashlib
from pathlib import Path

logger = logging.getLogger(__name__)


class DictionaryCache:
    """
    Unified cache for all dictionary lookups
    """

    def __init__(self, db_path: str = "/tmp/dictionary_cache.db",
                 cache_duration_days: int = 30):
        self.db_path = db_path
        self.cache_duration_days = cache_duration_days
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
        self.hits = 0
        self.misses = 0

    # ============================================================================
    # DATABASE INITIALIZATION
    # ============================================================================

    def _init_database(self):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS dictionary_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cache_key TEXT UNIQUE NOT NULL,
                    word TEXT NOT NULL,
                    source TEXT NOT NULL,
                    language TEXT NOT NULL,
                    data TEXT NOT NULL,
                    cached_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    hit_count INTEGER DEFAULT 0
                )
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_cache_key
                ON dictionary_cache(cache_key)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_word_source_lang
                ON dictionary_cache(word, source, language)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_expires_at
                ON dictionary_cache(expires_at)
            """)

            conn.commit()
            conn.close()
            logger.info(f"Dictionary cache initialized at: {self.db_path}")

        except Exception as e:
            logger.error(f"Failed to initialize dictionary cache: {e}")

    # ============================================================================
    # CACHE KEY
    # ============================================================================

    def _generate_cache_key(self, word: str, source: str, language: str) -> str:
        key = f"{word.lower()}:{source}:{language}"
        return hashlib.md5(key.encode()).hexdigest()

    # ============================================================================
    # CACHE OPERATIONS
    # ============================================================================

    def get(self, word: str, source: str, language: str = "en") -> Optional[Dict]:
        cache_key = self._generate_cache_key(word, source, language)

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                "SELECT data, expires_at, hit_count FROM dictionary_cache WHERE cache_key = ?",
                (cache_key,)
            )

            row = cursor.fetchone()
            if not row:
                self.misses += 1
                return None

            data_json, expires_at_str, hit_count = row
            expires_at = datetime.fromisoformat(expires_at_str)

            if datetime.now() > expires_at:
                cursor.execute(
                    "DELETE FROM dictionary_cache WHERE cache_key = ?",
                    (cache_key,)
                )
                conn.commit()
                self.misses += 1
                return None

            cursor.execute(
                "UPDATE dictionary_cache SET hit_count = hit_count + 1 WHERE cache_key = ?",
                (cache_key,)
            )

            conn.commit()
            self.hits += 1
            return json.loads(data_json)

        except Exception as e:
            logger.error(f"Cache get error for {word}: {e}")
            self.misses += 1
            return None

        finally:
            try:
                conn.close()
            except Exception:
                pass

    def set(self, word: str, source: str, data: Dict,
            language: str = "en") -> bool:
        cache_key = self._generate_cache_key(word, source, language)

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cached_at = datetime.now()
            expires_at = cached_at + timedelta(days=self.cache_duration_days)

            cursor.execute("""
                INSERT OR REPLACE INTO dictionary_cache
                (cache_key, word, source, language, data, cached_at, expires_at, hit_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, 0)
            """, (
                cache_key,
                word.lower(),
                source,
                language,
                json.dumps(data, ensure_ascii=False),
                cached_at.isoformat(),
                expires_at.isoformat()
            ))

            conn.commit()
            return True

        except Exception as e:
            logger.error(f"Cache set error for {word}: {e}")
            return False

        finally:
            try:
                conn.close()
            except Exception:
                pass

    # ============================================================================
    # BATCH OPERATIONS
    # ============================================================================

    def get_multiple(
        self,
        lookups: List[Tuple[str, str, str]]
    ) -> Dict[str, Optional[Dict]]:
        results: Dict[str, Optional[Dict]] = {}

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            now = datetime.now()

            for word, source, language in lookups:
                cache_key = self._generate_cache_key(word, source, language)

                cursor.execute(
                    "SELECT data, expires_at FROM dictionary_cache WHERE cache_key = ?",
                    (cache_key,)
                )

                row = cursor.fetchone()
                if not row:
                    results[cache_key] = None
                    self.misses += 1
                    continue

                data_json, expires_at_str = row
                expires_at = datetime.fromisoformat(expires_at_str)

                if now <= expires_at:
                    results[cache_key] = json.loads(data_json)
                    self.hits += 1
                else:
                    results[cache_key] = None
                    self.misses += 1

        except Exception as e:
            logger.error(f"Batch get error: {e}")

        finally:
            try:
                conn.close()
            except Exception:
                pass

        return results


# ============================================================================
# GLOBAL INSTANCE
# ============================================================================

dictionary_cache = DictionaryCache()
