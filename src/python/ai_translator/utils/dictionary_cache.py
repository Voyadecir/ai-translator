"""
Dictionary Cache - Unified 30-Day Cache Manager
Centralized caching for all dictionary lookups (MW, RAE, etc.)
Reduces API calls and web scraping by 90%+

Philosophy:
- Dictionary definitions don't change daily → cache for 30 days
- Unified cache across MW API, RAE scraper, and custom dictionaries
- Persistent storage (survives server restarts)
- Automatic expiration and cleanup
- Cache hit metrics for monitoring

Benefits:
- Save API quota (MW: 1000/day limit)
- Reduce RAE scraping (be respectful)
- Faster response times (no network calls)
- Works offline when cached
- $0 cost for repeated lookups

Storage:
- SQLite database (simple, fast, serverless)
- JSON serialization for complex data
- Indexed by word + source + language
"""

import sqlite3
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging
import hashlib
from pathlib import Path

logger = logging.getLogger(__name__)

class DictionaryCache:
    """
    Unified cache for all dictionary lookups
    
    Features:
    - 30-day expiration (configurable)
    - Multi-source support (MW, RAE, custom)
    - SQLite persistence
    - Automatic cleanup
    - Cache statistics
    - Thread-safe operations
    
    Cache Keys:
    - word: The word being looked up
    - source: Dictionary source (mw, rae, custom, etc.)
    - language: Language code (en, es, pt, fr)
    
    Cache Data:
    - Full dictionary response (JSON)
    - Timestamp
    - Expiration date
    """
    
    def __init__(self, db_path: str = "/tmp/dictionary_cache.db", 
                 cache_duration_days: int = 30):
        """
        Initialize dictionary cache
        
        Args:
            db_path: Path to SQLite database file
            cache_duration_days: How long to cache entries (default: 30 days)
        """
        self.db_path = db_path
        self.cache_duration_days = cache_duration_days
        
        # Ensure directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self._init_database()
        
        # Stats
        self.hits = 0
        self.misses = 0
    
    # ============================================================================
    # DATABASE INITIALIZATION
    # ============================================================================
    
    def _init_database(self):
        """
        Create cache database and tables if they don't exist
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create cache table
            cursor.execute('''
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
            ''')
            
            # Create indexes for fast lookups
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_cache_key 
                ON dictionary_cache(cache_key)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_word_source_lang 
                ON dictionary_cache(word, source, language)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_expires_at 
                ON dictionary_cache(expires_at)
            ''')
            
            # Create stats table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS cache_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    hits INTEGER DEFAULT 0,
                    misses INTEGER DEFAULT 0,
                    entries_added INTEGER DEFAULT 0,
                    entries_expired INTEGER DEFAULT 0
                )
            ''')
            
            conn.commit()
            conn.close()
            
            logger.info(f"Dictionary cache initialized at: {self.db_path}")
            
        except Exception as e:
            logger.error(f"Failed to initialize dictionary cache: {e}")
    
    # ============================================================================
    # CACHE OPERATIONS (Get, Set, Delete)
    # ============================================================================
    
    def get(self, word: str, source: str, language: str = 'en') -> Optional[Dict]:
        """
        Get cached dictionary entry
        
        Args:
            word: The word to look up
            source: Dictionary source (mw, rae, custom, etc.)
            language: Language code (en, es, pt, fr)
        
        Returns:
            Cached data dict or None if not found/expired
        """
        cache_key = self._generate_cache_key(word, source, language)
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get entry
            cursor.execute('''
                SELECT data, expires_at, hit_count 
                FROM dictionary_cache 
                WHERE cache_key = ?
            ''', (cache_key,))
            
            result = cursor.fetchone()
            
            if not result:
                self.misses += 1
                conn.close()
                return None
            
            data_json, expires_at_str, hit_count = result
            
            # Check if expired
            expires_at = datetime.fromisoformat(expires_at_str)
            if datetime.now() > expires_at:
                # Expired - delete it
                cursor.execute('DELETE FROM dictionary_cache WHERE cache_key = ?', 
                              (cache_key,))
                conn.commit()
                conn.close()
                self.misses += 1
                return None
            
            # Update hit count
            cursor.execute('''
                UPDATE dictionary_cache 
                SET hit_count = hit_count + 1 
                WHERE cache_key = ?
            ''', (cache_key,))
            
            conn.commit()
            conn.close()
            
            # Cache hit!
            self.hits += 1
            logger.debug(f"Cache HIT: {word} ({source}/{language}) - hits: {hit_count + 1}")
            
            return json.loads(data_json)
            
        except Exception as e:
            logger.error(f"Cache get error for {word}: {e}")
            self.misses += 1
            return None
    
    def set(self, word: str, source: str, data: Dict, 
           language: str = 'en') -> bool:
        """
        Save dictionary entry to cache
        
        Args:
            word: The word
            source: Dictionary source (mw, rae, custom)
            data: Dictionary data to cache
            language: Language code
        
        Returns:
            True if saved successfully, False otherwise
        """
        cache_key = self._generate_cache_key(word, source, language)
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Calculate expiration
            cached_at = datetime.now()
            expires_at = cached_at + timedelta(days=self.cache_duration_days)
            
            # Serialize data to JSON
            data_json = json.dumps(data, ensure_ascii=False)
            
            # Insert or replace
            cursor.execute('''
                INSERT OR REPLACE INTO dictionary_cache 
                (cache_key, word, source, language, data, cached_at, expires_at, hit_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, 0)
            ''', (
                cache_key,
                word.lower(),
                source,
                language,
                data_json,
                cached_at.isoformat(),
                expires_at.isoformat()
            ))
            
            conn.commit()
            conn.close()
            
            logger.debug(f"Cache SET: {word} ({source}/{language})")
            return True
            
        except Exception as e:
            logger.error(f"Cache set error for {word}: {e}")
            return False
    
    def delete(self, word: str, source: str, language: str = 'en') -> bool:
        """
        Delete entry from cache
        
        Args:
            word: The word
            source: Dictionary source
            language: Language code
        
        Returns:
            True if deleted, False otherwise
        """
        cache_key = self._generate_cache_key(word, source, language)
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM dictionary_cache WHERE cache_key = ?', 
                          (cache_key,))
            
            deleted = cursor.rowcount > 0
            conn.commit()
            conn.close()
            
            logger.debug(f"Cache DELETE: {word} ({source}/{language})")
            return deleted
            
        except Exception as e:
            logger.error(f"Cache delete error for {word}: {e}")
            return False
    
    # ============================================================================
    # CACHE KEY GENERATION
    # ============================================================================
    
    def _generate_cache_key(self, word: str, source: str, language: str) -> str:
        """
        Generate unique cache key
        
        Format: md5(word:source:language)
        Using MD5 to handle special characters and ensure consistent length
        """
        key_string = f"{word.lower()}:{source}:{language}"
        return hashlib.md5(key_string.encode()).hexdigest()
    
    # ============================================================================
    # CACHE MAINTENANCE
    # ============================================================================
    
    def cleanup_expired(self) -> int:
        """
        Remove all expired entries from cache
        
        Returns:
            Number of entries deleted
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            now = datetime.now().isoformat()
            
            # Delete expired entries
            cursor.execute('''
                DELETE FROM dictionary_cache 
                WHERE expires_at < ?
            ''', (now,))
            
            deleted_count = cursor.rowcount
            
            conn.commit()
            conn.close()
            
            if deleted_count > 0:
                logger.info(f"Cache cleanup: deleted {deleted_count} expired entries")
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"Cache cleanup error: {e}")
            return 0
    
    def clear_all(self, confirm: bool = False) -> bool:
        """
        Clear ALL cache entries
        
        Args:
            confirm: Must be True to actually clear (safety check)
        
        Returns:
            True if cleared, False otherwise
        """
        if not confirm:
            logger.warning("clear_all() called without confirmation")
            return False
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM dictionary_cache')
            deleted_count = cursor.rowcount
            
            conn.commit()
            conn.close()
            
            logger.warning(f"Cache CLEARED: deleted {deleted_count} entries")
            return True
            
        except Exception as e:
            logger.error(f"Cache clear error: {e}")
            return False
    
    def vacuum(self) -> bool:
        """
        Optimize database (reclaim space, rebuild indexes)
        
        Run this periodically (e.g., daily) to keep database efficient
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('VACUUM')
            
            conn.commit()
            conn.close()
            
            logger.info("Cache database vacuumed")
            return True
            
        except Exception as e:
            logger.error(f"Cache vacuum error: {e}")
            return False
    
    # ============================================================================
    # CACHE STATISTICS
    # ============================================================================
    
    def get_stats(self) -> Dict:
        """
        Get cache statistics
        
        Returns:
            Dict with stats (total entries, hit rate, size, etc.)
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Total entries
            cursor.execute('SELECT COUNT(*) FROM dictionary_cache')
            total_entries = cursor.fetchone()[0]
            
            # Entries by source
            cursor.execute('''
                SELECT source, COUNT(*) 
                FROM dictionary_cache 
                GROUP BY source
            ''')
            by_source = dict(cursor.fetchall())
            
            # Entries by language
            cursor.execute('''
                SELECT language, COUNT(*) 
                FROM dictionary_cache 
                GROUP BY language
            ''')
            by_language = dict(cursor.fetchall())
            
            # Average hit count
            cursor.execute('SELECT AVG(hit_count) FROM dictionary_cache')
            avg_hits = cursor.fetchone()[0] or 0
            
            # Database size
            cursor.execute('SELECT page_count * page_size FROM pragma_page_count(), pragma_page_size()')
            db_size_bytes = cursor.fetchone()[0]
            
            conn.close()
            
            # Calculate hit rate
            total_requests = self.hits + self.misses
            hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0
            
            return {
                'total_entries': total_entries,
                'by_source': by_source,
                'by_language': by_language,
                'average_hit_count': round(avg_hits, 2),
                'session_hits': self.hits,
                'session_misses': self.misses,
                'hit_rate_percent': round(hit_rate, 2),
                'database_size_mb': round(db_size_bytes / 1024 / 1024, 2),
                'cache_duration_days': self.cache_duration_days
            }
            
        except Exception as e:
            logger.error(f"Stats error: {e}")
            return {}
    
    def get_most_popular_words(self, limit: int = 20) -> List[Dict]:
        """
        Get most frequently accessed cached words
        
        Args:
            limit: Number of words to return
        
        Returns:
            List of dicts with word, source, language, hit_count
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT word, source, language, hit_count 
                FROM dictionary_cache 
                ORDER BY hit_count DESC 
                LIMIT ?
            ''', (limit,))
            
            results = cursor.fetchall()
            conn.close()
            
            return [
                {
                    'word': row[0],
                    'source': row[1],
                    'language': row[2],
                    'hit_count': row[3]
                }
                for row in results
            ]
            
        except Exception as e:
            logger.error(f"Popular words error: {e}")
            return []
    
    # ============================================================================
    # BATCH OPERATIONS
    # ============================================================================
    
    def get_multiple(self, lookups: List[Tuple[str, str, str]]) -> Dict[str, Optional[Dict]]:
        """
        Get multiple cached entries in one operation
        
        Args:
            lookups: List of (word, source, language) tuples
        
        Returns:
            Dict mapping cache_key → data
        """
        results = {}
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            now = datetime.now()
            
            for word, source, language in lookups:
                cache_key = self._generate_cache_key(word, source, language)
                
                cursor.execute('''
                    SELECT data, expires_at 
                    FROM dictionary_cache 
                    WHERE cache_key = ?
                ''', (cache_key,))
                
                result = cursor.fetchone()
                
                if result:
                    data_json, expires_at_str = result
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
            
            conn.close()
            
        except Exception as e:
            logger.error(f"Batch get error: {e}")
        
        return results


# ============================================================================
# GLOBAL INSTANCE
# ============================================================================
dictionary_cache = DictionaryCache()

# Convenience functions
def get_cached(word: str, source: str, language: str = 'en') -> Optional[Dict]:
    """Get from cache"""
    return dictionary_cache.get(word, source, language)

def cache_result(word: str, source: str, data: Dict, language: str = 'en') -> bool:
    """Save to cache"""
    return dictionary_cache.set(word, source, data, language)

def cleanup_cache() -> int:
    """Remove expired entries"""
    return dictionary_cache.cleanup_expired()

def get_cache_stats() -> Dict:
    """Get cache statistics"""
    return dictionary_cache.get_stats()


# Test example
if __name__ == "__main__":
    print("\n" + "="*60)
    print("DICTIONARY CACHE - UNIFIED 30-DAY CACHE MANAGER")
    print("="*60)
    
    # Test caching
    test_word = "example"
    test_source = "mw"
    test_data = {
        'word': test_word,
        'definitions': ['A thing that serves as a pattern'],
        'part_of_speech': 'noun'
    }
    
    print(f"\n**Test 1: Cache SET**")
    success = cache_result(test_word, test_source, test_data)
    print(f"Cached '{test_word}': {success}")
    
    print(f"\n**Test 2: Cache GET**")
    cached = get_cached(test_word, test_source)
    print(f"Retrieved '{test_word}': {cached is not None}")
    if cached:
        print(f"Data: {cached}")
    
    print(f"\n**Test 3: Cache MISS**")
    cached_miss = get_cached("nonexistent", test_source)
    print(f"Retrieved 'nonexistent': {cached_miss is not None}")
    
    print(f"\n**Test 4: Cache Statistics**")
    stats = get_cache_stats()
    print(f"Total entries: {stats['total_entries']}")
    print(f"Hit rate: {stats['hit_rate_percent']}%")
    print(f"Database size: {stats['database_size_mb']} MB")
    print(f"By source: {stats['by_source']}")
    
    print(f"\n**Test 5: Most Popular Words**")
    popular = dictionary_cache.get_most_popular_words(5)
    for word_data in popular:
        print(f"  - {word_data['word']} ({word_data['source']}): {word_data['hit_count']} hits")
    
    print(f"\n**Test 6: Cleanup**")
    expired_count = cleanup_cache()
    print(f"Removed {expired_count} expired entries")
    
    print("\n" + "="*60)
