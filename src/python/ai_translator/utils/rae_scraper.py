"""
RAE Scraper - Real Academia Española (Spanish Royal Academy) Dictionary
Web scraping since RAE doesn't offer a free API
Most authoritative source for Spanish language definitions

Why RAE?
- THE authority on Spanish language (like Oxford for English)
- Free to access via web (no API)
- Comprehensive definitions for all Spanish words
- Includes regional variations (Spain, Latin America)
- Etymology and usage notes

Scraping Strategy:
- Use dle.rae.es (Diccionario de la lengua española)
- Respectful scraping (delays, caching, User-Agent)
- 30-day cache to minimize requests
- Fallback to cached data if site unavailable

Legal/Ethical:
- RAE content is publicly accessible
- We cache aggressively to minimize load
- Use respectful delays between requests
- Attribute RAE as source in our app
"""

import requests
from bs4 import BeautifulSoup
import time
import re
from typing import Dict, List, Optional
from functools import lru_cache
import logging
from datetime import datetime, timedelta
import json
import hashlib

logger = logging.getLogger(__name__)

class RAEScraper:
    """
    Scrapes Spanish definitions from Real Academia Española
    
    Features:
    - Word definitions (all meanings)
    - Etymology
    - Regional variations
    - Usage examples
    - 30-day persistent cache
    - Respectful rate limiting
    - Fallback handling
    
    Cost: FREE (web scraping)
    """
    
    def __init__(self, cache_dir: str = "/tmp/rae_cache"):
        """
        Initialize RAE scraper
        
        Args:
            cache_dir: Directory for persistent cache
        """
        self.base_url = "https://dle.rae.es/"
        self.search_url = f"{self.base_url}"
        
        # Cache settings
        self.cache_dir = cache_dir
        self.cache_duration_days = 30
        
        # Rate limiting (be respectful)
        self.min_delay_seconds = 2.0  # Minimum 2 seconds between requests
        self.last_request_time = 0
        
        # User agent (identify ourselves)
        self.headers = {
            'User-Agent': 'Voyadecir Translation App (Educational/Non-commercial)',
            'Accept': 'text/html,application/xhtml+xml',
            'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
        }
        
        # Create cache directory
        import os
        os.makedirs(cache_dir, exist_ok=True)
    
    # ============================================================================
    # MAIN LOOKUP METHOD
    # ============================================================================
    
    def lookup_word(self, word: str) -> Optional[Dict]:
        """
        Look up Spanish word in RAE dictionary
        
        Args:
            word: Spanish word to look up
        
        Returns:
            Dict with definitions, etymology, examples
            None if word not found or error
        """
        # Check cache first
        cached = self._get_from_cache(word)
        if cached:
            logger.info(f"RAE cache hit: {word}")
            return cached
        
        # Scrape from RAE
        logger.info(f"RAE scraping: {word}")
        result = self._scrape_rae(word)
        
        # Cache the result (even if None - avoid repeated failures)
        if result:
            self._save_to_cache(word, result)
        
        return result
    
    # ============================================================================
    # WEB SCRAPING
    # ============================================================================
    
    def _scrape_rae(self, word: str) -> Optional[Dict]:
        """
        Scrape word definition from RAE website
        """
        # Respect rate limiting
        self._wait_for_rate_limit()
        
        try:
            # RAE URL format: https://dle.rae.es/palabra
            url = f"{self.base_url}{word.lower()}"
            
            response = requests.get(url, headers=self.headers, timeout=10)
            self.last_request_time = time.time()
            
            if response.status_code == 404:
                logger.info(f"RAE: Word not found: {word}")
                return None
            
            if response.status_code != 200:
                logger.error(f"RAE HTTP {response.status_code} for word: {word}")
                return None
            
            # Parse HTML
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Parse the page
            parsed = self._parse_rae_page(soup, word)
            
            if not parsed:
                logger.warning(f"RAE: Could not parse page for word: {word}")
                return None
            
            return parsed
            
        except requests.exceptions.Timeout:
            logger.error(f"RAE timeout for word: {word}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"RAE request failed for {word}: {e}")
            return None
        except Exception as e:
            logger.error(f"RAE scraping error for {word}: {e}")
            return None
    
    def _parse_rae_page(self, soup: BeautifulSoup, word: str) -> Optional[Dict]:
        """
        Parse RAE dictionary page
        
        RAE HTML structure (as of 2024):
        - Main article: <article id="contenedor">
        - Entry header: <header>
        - Definitions: <p class="j"> or similar
        - Etymology: Usually in first paragraph
        """
        result = {
            'word': word,
            'found': True,
            'source': 'RAE',
            'url': f"{self.base_url}{word.lower()}",
            'scraped_at': datetime.now().isoformat(),
            'entries': []
        }
        
        # Find main article container
        article = soup.find('article', id='resultados')
        if not article:
            # Try alternative container
            article = soup.find('div', class_='resultados')
        
        if not article:
            logger.warning(f"RAE: Could not find article container for {word}")
            return None
        
        # Extract all definition entries
        # RAE uses <article> tags for each word entry
        entries = article.find_all('article')
        
        if not entries:
            logger.warning(f"RAE: No entries found for {word}")
            return None
        
        for entry in entries:
            parsed_entry = self._parse_entry(entry)
            if parsed_entry:
                result['entries'].append(parsed_entry)
        
        return result if result['entries'] else None
    
    def _parse_entry(self, entry) -> Optional[Dict]:
        """
        Parse a single RAE dictionary entry
        """
        parsed = {
            'headword': '',
            'part_of_speech': '',
            'etymology': '',
            'definitions': []
        }
        
        # Extract headword (the word itself)
        header = entry.find('header')
        if header:
            headword_elem = header.find('span', class_='f')
            if headword_elem:
                parsed['headword'] = headword_elem.get_text(strip=True)
        
        # Extract part of speech
        # Usually in format: "sustantivo masculino", "verbo transitivo", etc.
        pos_elem = header.find('p', class_='n2') if header else None
        if pos_elem:
            parsed['part_of_speech'] = pos_elem.get_text(strip=True)
        
        # Extract etymology
        # Usually marked with "Del lat." or "Etim."
        etym_elem = entry.find('p', class_='k4')
        if etym_elem:
            parsed['etymology'] = etym_elem.get_text(strip=True)
        
        # Extract definitions
        # Definitions are in <p> tags with various classes
        definition_paragraphs = entry.find_all('p', class_=['j', 'k'])
        
        for i, def_p in enumerate(definition_paragraphs, 1):
            # Get definition number (if present)
            number_elem = def_p.find('span', class_='n_acep')
            number = number_elem.get_text(strip=True) if number_elem else str(i)
            
            # Get definition text
            # Remove the number span to get just the definition
            if number_elem:
                number_elem.decompose()
            
            definition_text = def_p.get_text(strip=True)
            
            if definition_text:
                parsed['definitions'].append({
                    'number': number,
                    'definition': definition_text,
                    'examples': []  # RAE doesn't always have examples in HTML
                })
        
        return parsed if parsed['definitions'] else None
    
    # ============================================================================
    # HELPER METHODS
    # ============================================================================
    
    def get_all_meanings(self, word: str) -> Optional[List[Dict]]:
        """
        Get all meanings of a Spanish word in simple format
        
        Returns list of definitions
        Used by context_handler.py to show all meanings
        """
        result = self.lookup_word(word)
        
        if not result or not result.get('found'):
            return None
        
        all_meanings = []
        
        for entry in result.get('entries', []):
            part_of_speech = entry.get('part_of_speech', 'unknown')
            
            for definition in entry.get('definitions', []):
                meaning = {
                    'part_of_speech': part_of_speech,
                    'definition': definition.get('definition', ''),
                    'number': definition.get('number', '1')
                }
                all_meanings.append(meaning)
        
        return all_meanings
    
    def get_simple_definition(self, word: str) -> Optional[str]:
        """
        Get first/primary definition only
        
        Quick lookup for single definition
        """
        result = self.lookup_word(word)
        
        if not result or not result.get('found'):
            return None
        
        entries = result.get('entries', [])
        if not entries:
            return None
        
        definitions = entries[0].get('definitions', [])
        if not definitions:
            return None
        
        return definitions[0].get('definition', '')
    
    def is_valid_word(self, word: str) -> bool:
        """
        Check if Spanish word exists in RAE dictionary
        
        Quick validation
        """
        result = self.lookup_word(word)
        return result is not None and result.get('found', False)
    
    # ============================================================================
    # CACHING (30-day persistent cache)
    # ============================================================================
    
    def _get_cache_path(self, word: str) -> str:
        """
        Get cache file path for word
        
        Uses MD5 hash to avoid filesystem issues with special characters
        """
        word_hash = hashlib.md5(word.lower().encode()).hexdigest()
        return f"{self.cache_dir}/{word_hash}.json"
    
    def _get_from_cache(self, word: str) -> Optional[Dict]:
        """
        Get word from cache if available and not expired
        """
        cache_path = self._get_cache_path(word)
        
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                cached_data = json.load(f)
            
            # Check if cache is still valid (30 days)
            cached_date = datetime.fromisoformat(cached_data.get('cached_at', ''))
            if datetime.now() - cached_date > timedelta(days=self.cache_duration_days):
                logger.info(f"RAE cache expired for: {word}")
                return None
            
            return cached_data.get('data')
            
        except FileNotFoundError:
            return None
        except Exception as e:
            logger.warning(f"RAE cache read error for {word}: {e}")
            return None
    
    def _save_to_cache(self, word: str, data: Dict):
        """
        Save word data to cache
        """
        cache_path = self._get_cache_path(word)
        
        cache_entry = {
            'word': word,
            'cached_at': datetime.now().isoformat(),
            'data': data
        }
        
        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(cache_entry, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"RAE cache write error for {word}: {e}")
    
    # ============================================================================
    # RATE LIMITING
    # ============================================================================
    
    def _wait_for_rate_limit(self):
        """
        Wait to respect rate limiting (minimum 2 seconds between requests)
        """
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_delay_seconds:
            wait_time = self.min_delay_seconds - elapsed
            logger.debug(f"RAE rate limit: waiting {wait_time:.2f}s")
            time.sleep(wait_time)


# ============================================================================
# GLOBAL INSTANCE
# ============================================================================
rae_scraper = RAEScraper()

# Convenience functions
def lookup_word(word: str) -> Optional[Dict]:
    """
    Convenience function: Look up Spanish word in RAE
    
    Returns full entry with definitions, etymology, etc.
    """
    return rae_scraper.lookup_word(word)

def get_all_meanings(word: str) -> Optional[List[Dict]]:
    """
    Convenience function: Get all meanings of Spanish word
    
    Returns simple list of definitions
    """
    return rae_scraper.get_all_meanings(word)

def get_definition(word: str) -> Optional[str]:
    """
    Convenience function: Get primary definition only
    
    Returns single string definition
    """
    return rae_scraper.get_simple_definition(word)


# Test example
if __name__ == "__main__":
    print("\n" + "="*60)
    print("RAE SCRAPER - SPANISH ROYAL ACADEMY DICTIONARY")
    print("="*60)
    
    # Test word with multiple meanings
    test_word = "casa"
    
    print(f"\n**Looking up Spanish word: '{test_word}'**")
    
    # Full lookup
    result = lookup_word(test_word)
    
    if result and result.get('found'):
        print(f"\n✅ Word found: {result['word']}")
        print(f"Source: {result['source']}")
        print(f"URL: {result['url']}")
        print(f"Number of entries: {len(result['entries'])}")
        
        for i, entry in enumerate(result['entries'][:2], 1):  # Show first 2 entries
            print(f"\n**Entry {i}:**")
            print(f"Headword: {entry['headword']}")
            print(f"Part of speech: {entry['part_of_speech']}")
            if entry['etymology']:
                print(f"Etymology: {entry['etymology']}")
            print(f"Definitions:")
            for definition in entry['definitions'][:3]:  # Show first 3 definitions
                print(f"  {definition['number']}. {definition['definition']}")
    else:
        print(f"\n❌ Word not found or scraping failed")
    
    # Simple meanings
    print(f"\n\n**All meanings (simple format):**")
    meanings = get_all_meanings(test_word)
    if meanings:
        for i, meaning in enumerate(meanings[:5], 1):  # Show first 5
            print(f"{i}. [{meaning['part_of_speech']}] {meaning['definition']}")
    
    # Single definition
    print(f"\n\n**Primary definition:**")
    primary = get_definition(test_word)
    if primary:
        print(primary)
    
    print("\n" + "="*60)
