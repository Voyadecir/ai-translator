"""
Dictionary Cache - Unified 30‑Day Cache Manager

This module implements a persistent cache for dictionary lookups.  It uses
a local SQLite database to store lookups keyed by word, source, and
language, along with metadata such as timestamps and hit counts.  The
cache reduces API calls by caching entries for 30 days (configurable).

The cache API provides get, set, delete, cleanup, statistics, and batch
operations.  A global `dictionary_cache` instance is exported for
convenience.
"""

import sqlite3
import json
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import logging
import hashlib
from pathlib import Path

logger = logging.getLogger(__name__)


class DictionaryCache:
    """
    Unified cache for all dictionary lookups.

    Provides persistent storage with expiration, hit/miss tracking, and
    batch operations.  Keys are MD5 hashes of (word, source, language)
    to normalize case and avoid filesystem issues.
    """

    def __init__(self, db_path: str = "/tmp/dictionary_cache.db", cache_duration_days: int = 30):
        self.db_path = db_path
        self.cache_duration_days = cache_duration_days
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
        self.hits = 0
        self.misses = 0

    def _init_database(self):
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
            logger.info(f"Dictionary cache initialized at: {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to initialize dictionary cache: {e}")

    def _generate_cache_key(self, word: str, source: str, language: str) -> str:
        key_string = f"{word.lower()}:{source}:{language}"
        return hashlib.md5(key_string.encode()).hexdigest()

    def get(self, word: str, source: str, language: str = 'en') -> Optional[Dict]:
        cache_key = self._generate_cache_key(word, source, language)
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT data, expires_at, hit_count FROM dictionary_cache WHERE cache_key = ?",
                (cache_key,),
            )
            result = cursor.fetchone()
            if not result:
                self.misses += 1
                return None
            data_json, expires_at_str, hit_count = result
            expires_at = datetime.fromisoformat(expires_at_str)
            if datetime.now() > expires_at:
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
            logger.error(f"Cache get error for {word}: {e}")
            self.misses += 1
            return None
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def set(self, word: str, source: str, data: Dict, language: str = 'en') -> bool:
        cache_key = self._generate_cache_key(word, source, language)
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cached_at = datetime.now()
            expires_at = cached_at + timedelta(days=self.cache_duration_days)
            data_json = json.dumps(data, ensure_ascii=False)
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
                    data_json,
                    cached_at.isoformat(),
                    expires_at.isoformat(),
                ),
            )
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

    def delete(self, word: str, source: str, language: str = 'en') -> bool:
        cache_key = self._generate_cache_key(word, source, language)
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM dictionary_cache WHERE cache_key = ?", (cache_key,))
            deleted = cursor.rowcount > 0
            conn.commit()
            return deleted
        except Exception as e:
            logger.error(f"Cache delete error for {word}: {e}")
            return False
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def cleanup_expired(self) -> int:
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            cursor.execute(
                "DELETE FROM dictionary_cache WHERE expires_at < ?",
                (now,),
            )
            deleted_count = cursor.rowcount
            conn.commit()
            if deleted_count > 0:
                logger.info(f"Cache cleanup: deleted {deleted_count} expired entries")
            return deleted_count
        except Exception as e:
            logger.error(f"Cache cleanup error: {e}")
            return 0
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def clear_all(self, confirm: bool = False) -> bool:
        if not confirm:
            logger.warning("clear_all() called without confirmation")
            return False
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM dictionary_cache")
            deleted_count = cursor.rowcount
            conn.commit()
            logger.warning(f"Cache CLEARED: deleted {deleted_count} entries")
            return True
        except Exception as e:
            logger.error(f"Cache clear error: {e}")
            return False
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def vacuum(self) -> bool:
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('VACUUM')
            conn.commit()
            logger.info("Cache database vacuumed")
            return True
        except Exception as e:
            logger.error(f"Cache vacuum error: {e}")
            return False
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def get_stats(self) -> Dict:
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM dictionary_cache')
            total_entries = cursor.fetchone()[0]
            cursor.execute(
                'SELECT source, COUNT(*) FROM dictionary_cache GROUP BY source'
            )
            by_source = dict(cursor.fetchall())
            cursor.execute(
                'SELECT language, COUNT(*) FROM dictionary_cache GROUP BY language'
            )
            by_language = dict(cursor.fetchall())
            cursor.execute('SELECT AVG(hit_count) FROM dictionary_cache')
            avg_hits = cursor.fetchone()[0] or 0
            cursor.execute(
                'SELECT page_count * page_size FROM pragma_page_count(), pragma_page_size()'
            )
            db_size_bytes = cursor.fetchone()[0]
            total_requests = self.hits + self.misses
            hit_rate = (
                (self.hits / total_requests) * 100
                if total_requests > 0
                else 0
            )
            return {
                'total_entries': total_entries,
                'by_source': by_source,
                'by_language': by_language,
                'average_hit_count': round(avg_hits, 2),
                'session_hits': self.hits,
                'session_misses': self.misses,
                'hit_rate_percent': round(hit_rate, 2),
                'database_size_mb': round(db_size_bytes / 1024 / 1024, 2),
                'cache_duration_days': self.cache_duration_days,
            }
        except Exception as e:
            logger.error(f"Stats error: {e}")
            return {}
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def get_most_popular_words(self, limit: int = 20) -> List[Dict]:
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                'SELECT word, source, language, hit_count FROM dictionary_cache ORDER BY hit_count DESC LIMIT ?',
                (limit,),
            )
            results = cursor.fetchall()
            return [
                {
                    'word': row[0],
                    'source': row[1],
                    'language': row[2],
                    'hit_count': row[3],
                }
                for row in results
            ]
        except Exception as e:
            logger.error(f"Popular words error: {e}")
            return []
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def get_multiple(self, lookups: List[Tuple[str, str, str]]) -> Dict[str, Optional[Dict]]:
        results = {}
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            now = datetime.now()
            for word, source, language in lookups:
                cache_key = self._generate_cache_key(word, source, language)
                cursor.execute(
                    'SELECT data, expires_at FROM dictionary_cache WHERE cache_key = ?',
                    (cache_key,),
                )
                row = cursor.fetchone()
                if row:
                    data_json, expires_at_str = row
                    expires_at = datetime.fromisoformat(expires_at_str)
                    if now <= expires_at:
                        results[cache_key] = json.loads(data_json)
                        self.hits += 1
                    else:
                        results[cache_key] = None
                        self.misses += 1
                else:
                    results[cache_key] = None
                    self.misses += 1
            return results
        except Exception as e:
            logger.error(f"Batch get error: {e}")
            return results
        finally:
            try:
                conn.close()
            except Exception:
                pass


# Global instance
dictionary_cache = DictionaryCache()


# Convenience functions
def get_cached(word: str, source: str, language: str = 'en') -> Optional[Dict]:
    return dictionary_cache.get(word, source, language)


def cache_result(word: str, source: str, data: Dict, language: str = 'en') -> bool:
    return dictionary_cache.set(word, source, data, language)


def cleanup_cache() -> int:
    return dictionary_cache.cleanup_expired()


def get_cache_stats() -> Dict:
    return dictionary_cache.get_stats()
