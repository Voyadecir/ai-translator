"""
Dictionary Cache & Dictionary Orchestration

This module combines a persistent SQLite-backed cache for dictionary lookups
with orchestrated lookup logic for Merriam‑Webster (MW) and Real Academia
Española (RAE).  It exposes a unified API used by the translation engine
and mailbills agent and returns dictionary entries with caching.

The cache persists for 30 days and dramatically reduces external API calls.
"""

import sqlite3
import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import logging
import hashlib
from pathlib import Path

# External dictionary sources
from .merriam_webster_api import mw_api
from .rae_scraper import rae_scraper

logger = logging.getLogger(__name__)

# =====================================================================
# AUTHORITATIVE SOURCES
# =====================================================================
AUTHORITATIVE_SOURCES: Dict[str, Dict[str, str]] = {
    "mw": {
        "name": "Merriam-Webster Dictionary",
        "url": "https://www.merriam-webster.com",
        "category": "english",
        "description": "Authoritative English dictionary",
    },
    "rae": {
        "name": "Real Academia Española",
        "url": "https://www.rae.es",
        "category": "spanish",
        "description": "Official authority on the Spanish language",
    },
}


# =====================================================================
# DICTIONARY CACHE
# =====================================================================
class DictionaryCache:
    """
    Persistent cache for dictionary lookups.

    Entries are keyed by an MD5 hash of (word, source, language) and
    include JSON data, timestamps, expiry, and a hit count.  The cache
    automatically expires entries after `cache_duration_days`.  A local
    SQLite database provides durability between sessions and process restarts.
    """

    def __init__(self, db_path: str = "/tmp/dictionary_cache.db", cache_duration_days: int = 30):
        self.db_path = db_path
        self.cache_duration_days = cache_duration_days
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
        self.hits = 0
        self.misses = 0

    def _init_database(self) -> None:
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                """
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
                """
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_cache_key ON dictionary_cache(cache_key)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_word_source_lang ON dictionary_cache(word, source, language)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_expires_at ON dictionary_cache(expires_at)"
            )
            conn.commit()
            conn.close()
            logger.info(f"Dictionary cache initialized at {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to initialize dictionary cache: {e}")

    def _generate_cache_key(self, word: str, source: str, language: str) -> str:
        key = f"{word.lower()}:{source}:{language}"
        return hashlib.md5(key.encode()).hexdigest()

    def get(self, word: str, source: str, language: str) -> Optional[Dict]:
        cache_key = self._generate_cache_key(word, source, language)
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT data, expires_at, hit_count FROM dictionary_cache WHERE cache_key = ?",
                (cache_key,),
            )
            row = cursor.fetchone()
            if not row:
                self.misses += 1
                return None
            data_json, expires_at_str, hit_count = row
            expires_at = datetime.fromisoformat(expires_at_str)
            if datetime.utcnow() > expires_at:
                cursor.execute(
                    "DELETE FROM dictionary_cache WHERE cache_key = ?",
                    (cache_key,),
                )
                conn.commit()
                self.misses += 1
                return None
            cursor.execute(
                "UPDATE dictionary_cache SET hit_count = hit_count + 1 WHERE cache_key = ?",
                (cache_key,),
            )
            conn.commit()
            self.hits += 1
            return json.loads(data_json)
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            self.misses += 1
            return None
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def set(self, word: str, source: str, data: Dict, language: str) -> None:
        cache_key = self._generate_cache_key(word, source, language)
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cached_at = datetime.utcnow()
            expires_at = cached_at + timedelta(days=self.cache_duration_days)
            cursor.execute(
                """
                INSERT OR REPLACE INTO dictionary_cache
                (cache_key, word, source, language, data, cached_at, expires_at, hit_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, 0)
                """,
                (
                    cache_key,
                    word.lower(),
                    source,
                    language,
                    json.dumps(data, ensure_ascii=False),
                    cached_at.isoformat(),
                    expires_at.isoformat(),
                ),
            )
            conn.commit()
        except Exception as e:
            logger.error(f"Cache set error: {e}")
        finally:
            try:
                conn.close()
            except Exception:
                pass


# Global cache instance
dictionary_cache = DictionaryCache()


# =====================================================================
# DICTIONARY LOOKUP ORCHESTRATION
# =====================================================================
def get_translation(
    word: str,
    source_lang: str,
    target_lang: str,
    preferred_source: Optional[str] = None,
) -> Optional[Dict]:
    """
    Look up a word in dictionary sources with caching.

    The lookup order is:
    1. Cache
    2. Merriam‑Webster (for English source)
    3. RAE (for Spanish target)
    """
    sources = [preferred_source] if preferred_source else ["mw", "rae"]
    for source in sources:
        # Check cache first
        cached = dictionary_cache.get(word, source, target_lang)
        if cached:
            return cached
        result: Optional[Dict] = None
        try:
            if source == "mw" and source_lang == "en":
                result = mw_api.lookup(word)
            elif source == "rae" and target_lang == "es":
                result = rae_scraper.lookup(word)
        except Exception as e:
            logger.warning(f"Dictionary lookup failed ({source}): {e}")
        if result:
            dictionary_cache.set(word, source, result, target_lang)
            return result
    return None
