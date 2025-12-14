"""
Merriam-Webster API Integration - American English Dictionary
Provides authoritative American English definitions and pronunciations
FREE: 1,000 requests/day (perfect for our needs)

Why Merriam-Webster?
- Most authoritative American English dictionary
- Free tier is generous (1,000 requests/day)
- Provides multiple definitions per word
- Includes pronunciation, part of speech, examples
- Etymology information

API Endpoints:
- Collegiate Dictionary: dictionaryapi.com/api/v3/references/collegiate/json/{word}
- Learner's Dictionary: dictionaryapi.com/api/v3/references/learners/json/{word}

Integration with File 3 (context_handler.py):
When user encounters ambiguous word, we query MW API for ALL meanings
"""

import requests
import time
from typing import Dict, List, Optional, Any
from functools import lru_cache
import logging
import os

logger = logging.getLogger(__name__)

class MerriamWebsterAPI:
    """
    Interface to Merriam-Webster Dictionary API
    
    Features:
    - Word definitions (all meanings)
    - Pronunciations
    - Parts of speech
    - Example sentences
    - Etymology
    - Synonyms/Antonyms
    - LRU caching (5000 words)
    - Rate limit handling (1000/day)
    
    Cost: FREE (1,000 requests/day)
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Merriam-Webster API client
        
        Args:
            api_key: MW API key (get free at dictionaryapi.com)
                    Falls back to environment variable MW_API_KEY
        """
        self.api_key = api_key or os.getenv('MW_API_KEY')
        
        if not self.api_key:
            logger.warning("Merriam-Webster API key not provided. Set MW_API_KEY environment variable.")
        
        # API endpoints
        self.collegiate_url = "https://dictionaryapi.com/api/v3/references/collegiate/json/"
        self.learners_url = "https://dictionaryapi.com/api/v3/references/learners/json/"
        
        # Rate limiting
        self.requests_made_today = 0
        self.daily_limit = 1000
        self.last_reset = time.time()
        
        # Cache settings
        self.cache_size = 5000
    
    # ============================================================================
    # MAIN API METHODS
    # ============================================================================
    
    @lru_cache(maxsize=5000)
    def lookup_word(self, word: str, use_learners: bool = False) -> Optional[Dict]:
        """
        Look up word in Merriam-Webster dictionary
        
        Args:
            word: Word to look up
            use_learners: If True, use Learner's Dictionary (simpler definitions)
                         If False, use Collegiate Dictionary (comprehensive)
        
        Returns:
            Dict with definitions, pronunciations, examples, etc.
            None if word not found or API error
        """
        if not self.api_key:
            logger.error("MW API key not configured")
            return None
        
        # Check rate limit
        if not self._check_rate_limit():
            logger.warning("Merriam-Webster API rate limit exceeded (1000/day)")
            return None
        
        # Choose endpoint
        base_url = self.learners_url if use_learners else self.collegiate_url
        url = f"{base_url}{word.lower()}?key={self.api_key}"
        
        try:
            response = requests.get(url, timeout=5)
            self._increment_request_count()
            
            if response.status_code != 200:
                logger.error(f"MW API error: {response.status_code}")
                return None
            
            data = response.json()
            
            # Check if word was found
            if not data or not isinstance(data, list):
                return None
            
            # If first result is string, these are suggestions (word not found)
            if isinstance(data[0], str):
                return {
                    'word': word,
                    'found': False,
                    'suggestions': data[:10],  # Return suggestions
                }
            
            # Parse the response
            parsed = self._parse_mw_response(data, word)
            return parsed
            
        except requests.exceptions.Timeout:
            logger.error(f"MW API timeout for word: {word}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"MW API request failed: {e}")
            return None
        except Exception as e:
            logger.error(f"MW API parsing error: {e}")
            return None
    
    # ============================================================================
    # PARSE MW RESPONSE
    # ============================================================================
    
    def _parse_mw_response(self, data: List[Dict], word: str) -> Dict:
        """
        Parse Merriam-Webster API response into usable format
        
        MW response is complex JSON - we extract what we need
        """
        result = {
            'word': word,
            'found': True,
            'entries': []
        }
        
        for entry in data:
            # Only process entries that match the word
            if not isinstance(entry, dict):
                continue
            
            headword = entry.get('hwi', {}).get('hw', '').replace('*', '')
            if headword.lower() != word.lower():
                continue
            
            parsed_entry = {
                'headword': headword,
                'functional_label': entry.get('fl', ''),  # Part of speech
                'pronunciations': self._extract_pronunciations(entry),
                'definitions': self._extract_definitions(entry),
                'etymology': entry.get('et', []),
                'date': entry.get('date', ''),  # First known use
            }
            
            result['entries'].append(parsed_entry)
        
        return result
    
    def _extract_pronunciations(self, entry: Dict) -> List[Dict]:
        """Extract pronunciation information"""
        pronunciations = []
        
        hwi = entry.get('hwi', {})
        prs = hwi.get('prs', [])
        
        for pr in prs:
            pronunciation = {
                'ipa': pr.get('ipa', ''),  # International Phonetic Alphabet
                'sound': pr.get('sound', {}).get('audio', ''),  # Audio filename
                'label': pr.get('l', '')  # Label (e.g., "British")
            }
            pronunciations.append(pronunciation)
        
        return pronunciations
    
    def _extract_definitions(self, entry: Dict) -> List[Dict]:
        """
        Extract definitions from entry
        MW format is complex - definitions are nested
        """
        definitions = []
        
        shortdef = entry.get('shortdef', [])
        for i, definition in enumerate(shortdef, 1):
            definitions.append({
                'number': i,
                'definition': definition,
                'examples': []  # Shortdef doesn't include examples
            })
        
        # For detailed definitions with examples, parse 'def' field
        def_array = entry.get('def', [])
        if def_array:
            detailed_defs = self._parse_detailed_definitions(def_array)
            # Merge with shortdef
            for i, detailed in enumerate(detailed_defs):
                if i < len(definitions):
                    definitions[i]['examples'] = detailed.get('examples', [])
                else:
                    definitions.append(detailed)
        
        return definitions
    
    def _parse_detailed_definitions(self, def_array: List[Dict]) -> List[Dict]:
        """
        Parse detailed definition structure
        This is where examples are stored
        """
        definitions = []
        
        for def_section in def_array:
            sseq = def_section.get('sseq', [])
            
            for sense_sequence in sseq:
                for sense in sense_sequence:
                    if isinstance(sense, list) and len(sense) > 1:
                        sense_type = sense[0]
                        sense_data = sense[1]
                        
                        if sense_type == 'sense':
                            dt = sense_data.get('dt', [])
                            
                            definition_text = ''
                            examples = []
                            
                            for dt_item in dt:
                                if isinstance(dt_item, list) and len(dt_item) > 1:
                                    dt_type = dt_item[0]
                                    dt_content = dt_item[1]
                                    
                                    if dt_type == 'text':
                                        definition_text = dt_content.replace('{bc}', '').strip()
                                    elif dt_type == 'vis':
                                        # Verbal illustrations (examples)
                                        for vis in dt_content:
                                            example_text = vis.get('t', '').replace('{it}', '').replace('{/it}', '')
                                            examples.append(example_text)
                            
                            if definition_text:
                                definitions.append({
                                    'number': len(definitions) + 1,
                                    'definition': definition_text,
                                    'examples': examples
                                })
        
        return definitions
    
    # ============================================================================
    # HELPER METHODS
    # ============================================================================
    
    def get_all_meanings(self, word: str) -> Optional[List[Dict]]:
        """
        Get all meanings of a word in simple format
        
        Returns list of definitions with examples
        Used by context_handler.py to show all meanings
        """
        result = self.lookup_word(word)
        
        if not result or not result.get('found'):
            return None
        
        all_meanings = []
        
        for entry in result.get('entries', []):
            part_of_speech = entry.get('functional_label', 'unknown')
            
            for definition in entry.get('definitions', []):
                meaning = {
                    'part_of_speech': part_of_speech,
                    'definition': definition.get('definition', ''),
                    'examples': definition.get('examples', []),
                    'number': definition.get('number', 1)
                }
                all_meanings.append(meaning)
        
        return all_meanings
    
    def get_simple_definition(self, word: str) -> Optional[str]:
        """
        Get first/primary definition only
        
        Quick lookup for single definition
        """
        result = self.lookup_word(word, use_learners=True)  # Use learner's for simplicity
        
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
        Check if word exists in dictionary
        
        Quick validation without full lookup
        """
        result = self.lookup_word(word)
        return result is not None and result.get('found', False)
    
    # ============================================================================
    # RATE LIMITING
    # ============================================================================
    
    def _check_rate_limit(self) -> bool:
        """
        Check if we're within rate limit (1000 requests/day)
        
        Returns True if we can make request, False if limit exceeded
        """
        # Reset counter at midnight (24 hours)
        if time.time() - self.last_reset > 86400:  # 24 hours in seconds
            self.requests_made_today = 0
            self.last_reset = time.time()
        
        return self.requests_made_today < self.daily_limit
    
    def _increment_request_count(self):
        """Increment request counter"""
        self.requests_made_today += 1
    
    def get_remaining_requests(self) -> int:
        """Get number of requests remaining today"""
        self._check_rate_limit()  # Reset if needed
        return max(0, self.daily_limit - self.requests_made_today)
    
    # ============================================================================
    # BATCH LOOKUP (Multiple words)
    # ============================================================================
    
    def lookup_multiple_words(self, words: List[str], 
                             max_words: int = 50) -> Dict[str, Optional[Dict]]:
        """
        Look up multiple words efficiently
        
        Args:
            words: List of words to look up
            max_words: Maximum words to process (rate limit protection)
        
        Returns:
            Dict mapping word → result
        """
        results = {}
        
        # Limit to prevent rate limit exhaustion
        words_to_process = words[:max_words]
        
        for word in words_to_process:
            if not self._check_rate_limit():
                logger.warning(f"Rate limit reached. Processed {len(results)}/{len(words_to_process)} words")
                break
            
            results[word] = self.lookup_word(word)
            
            # Small delay to be nice to API
            time.sleep(0.1)
        
        return results


# ============================================================================
# GLOBAL INSTANCE
# ============================================================================
# Initialize with API key from environment
mw_api = MerriamWebsterAPI()

# Convenience functions
def lookup_word(word: str) -> Optional[Dict]:
    """
    Convenience function: Look up word in Merriam-Webster
    
    Returns full entry with all definitions, pronunciations, etc.
    """
    return mw_api.lookup_word(word)

def get_all_meanings(word: str) -> Optional[List[Dict]]:
    """
    Convenience function: Get all meanings of a word
    
    Returns simple list of definitions with examples
    """
    return mw_api.get_all_meanings(word)

def get_definition(word: str) -> Optional[str]:
    """
    Convenience function: Get primary definition only
    
    Returns single string definition
    """
    return mw_api.get_simple_definition(word)


# Test example
if __name__ == "__main__":
    print("\n" + "="*60)
    print("MERRIAM-WEBSTER API - AMERICAN ENGLISH DICTIONARY")
    print("="*60)
    
    # Test word with multiple meanings
    test_word = "run"
    
    print(f"\n**Looking up word: '{test_word}'**")
    print(f"Remaining requests today: {mw_api.get_remaining_requests()}")
    
    # Full lookup
    result = lookup_word(test_word)
    
    if result and result.get('found'):
        print(f"\n✅ Word found: {result['word']}")
        print(f"Number of entries: {len(result['entries'])}")
        
        for i, entry in enumerate(result['entries'][:2], 1):  # Show first 2 entries
            print(f"\n**Entry {i}:**")
            print(f"Part of speech: {entry['functional_label']}")
            print(f"Definitions:")
            for definition in entry['definitions'][:3]:  # Show first 3 definitions
                print(f"  {definition['number']}. {definition['definition']}")
                if definition['examples']:
                    print(f"     Example: {definition['examples'][0]}")
    else:
        print(f"\n❌ Word not found")
        if result and result.get('suggestions'):
            print(f"Suggestions: {', '.join(result['suggestions'][:5])}")
    
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
