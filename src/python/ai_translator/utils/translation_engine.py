"""
Translation Engine - Orchestrates All Translation Systems
The brain that coordinates all 15 utility files into one cohesive translation pipeline

This is where everything comes together:
- Files 1-15: Individual capabilities (idioms, slang, profanity, etc.)
- File 16 (THIS FILE): Orchestrates them intelligently
- File 17 (mailbills_agent.py): Uses this engine for document translation

Pipeline:
1. Receive text (from OCR or direct input)
2. Detect language
3. Apply spell correction (File 2)
4. Detect idioms (File 4)
5. Detect slang (File 5)
6. Detect profanity (File 6)
7. Detect sarcasm (File 7)
8. Check cultural warnings (File 8)
9. Identify religious terms (File 9)
10. Identify road signs (File 10)
11. Handle ambiguous words (File 3)
12. Translate with GPT-4o-mini
13. Apply professional dictionaries (Files 13-14)
14. Return enriched translation

NOT just translation - UNDERSTANDING.
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
from openai import AzureOpenAI
import os

# Import all utility modules
from .spell_correction import spell_corrector
from .context_handler import context_handler
from .idiom_database import idiom_db
from .slang_regional import slang_db
from .profanity_handler import profanity_handler
from .sarcasm_tone_detector import sarcasm_detector
from .cultural_intelligence import cultural_intel
from .religious_terms import religious_terms
from .road_signs_eli5 import road_signs
from .translation_dictionaries import get_translation
from .merriam_webster_api import mw_api
from .rae_scraper import rae_scraper
from .dictionary_cache import dictionary_cache

logger = logging.getLogger(__name__)

class TranslationEngine:
    """
    Orchestrates all translation systems into unified pipeline
    
    Capabilities:
    - Spell correction before translation
    - Idiom detection and cultural adaptation
    - Slang translation with regional variants
    - Profanity intensity preservation
    - Sarcasm tone detection
    - Cultural warnings (gestures, colors, etc.)
    - Religious term accuracy
    - Road sign explanations
    - Ambiguous word handling
    - Dictionary enrichment
    
    Output:
    - Translated text
    - Confidence score
    - Warnings/notes for user
    - Alternative translations
    - Cultural context
    """
    
    def __init__(self):
        """Initialize translation engine with Azure OpenAI"""
        # Azure OpenAI for main translation
        self.client = AzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version="2024-02-15-preview",
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
        )
        
        # Model configuration
        self.model = "gpt-4o-mini"
        self.max_tokens = 2000
        self.temperature = 0.3  # Lower = more consistent translations
        
        # User preferences (can be set per-request)
        self.default_preferences = {
            'preserve_profanity': True,
            'preserve_sarcasm': True,
            'regional_variant': None,  # e.g., 'mexico', 'spain'
            'include_alternatives': True,
            'include_cultural_notes': True,
        }
    
    # ============================================================================
    # MAIN TRANSLATION PIPELINE
    # ============================================================================
    
    def translate(self, 
                 text: str,
                 source_lang: str = 'en',
                 target_lang: str = 'es',
                 document_type: Optional[str] = None,
                 user_preferences: Optional[Dict] = None) -> Dict:
        """
        Main translation method - orchestrates entire pipeline
        
        Args:
            text: Text to translate
            source_lang: Source language code (en, es, pt, fr)
            target_lang: Target language code
            document_type: Optional document type (irs, uscis, medical, etc.)
            user_preferences: Override default preferences
        
        Returns:
            {
                'original_text': str,
                'translated_text': str,
                'confidence_score': float (0-1),
                'warnings': List[str],
                'cultural_notes': List[str],
                'alternatives': List[Dict],
                'enrichment': Dict,
                'metadata': Dict
            }
        """
        # Merge preferences
        prefs = {**self.default_preferences, **(user_preferences or {})}
        
        # Initialize result structure
        result = {
            'original_text': text,
            'translated_text': '',
            'confidence_score': 0.0,
            'warnings': [],
            'cultural_notes': [],
            'alternatives': [],
            'enrichment': {},
            'metadata': {
                'source_lang': source_lang,
                'target_lang': target_lang,
                'document_type': document_type,
                'pipeline_steps': []
            }
        }
        
        if not text or not text.strip():
            result['warnings'].append('Empty input text')
            return result
        
        # STEP 1: Spell correction (File 2)
        corrected_text, spell_corrections = self._apply_spell_correction(
            text, source_lang, document_type
        )
        if spell_corrections:
            result['metadata']['pipeline_steps'].append('spell_correction')
            result['metadata']['spell_corrections'] = spell_corrections
        
        # STEP 2: Detect idioms (File 4)
        idioms_found = self._detect_idioms(corrected_text, source_lang, target_lang)
        if idioms_found:
            result['metadata']['pipeline_steps'].append('idiom_detection')
            result['enrichment']['idioms'] = idioms_found
            result['cultural_notes'].extend([i['cultural_note'] for i in idioms_found if 'cultural_note' in i])
        
        # STEP 3: Detect slang (File 5)
        slang_found = self._detect_slang(corrected_text, source_lang, target_lang, prefs.get('regional_variant'))
        if slang_found:
            result['metadata']['pipeline_steps'].append('slang_detection')
            result['enrichment']['slang'] = slang_found
        
        # STEP 4: Detect profanity (File 6)
        profanity_analysis = self._analyze_profanity(
            corrected_text, source_lang, target_lang, 
            prefs.get('preserve_profanity', True)
        )
        if profanity_analysis['contains_profanity']:
            result['metadata']['pipeline_steps'].append('profanity_detection')
            result['enrichment']['profanity'] = profanity_analysis
            if profanity_analysis.get('warning'):
                result['warnings'].append(profanity_analysis['warning'])
        
        # STEP 5: Detect sarcasm/tone (File 7)
        tone_analysis = self._analyze_tone(corrected_text)
        if tone_analysis['is_sarcastic']:
            result['metadata']['pipeline_steps'].append('sarcasm_detection')
            result['enrichment']['tone'] = tone_analysis
            if prefs.get('preserve_sarcasm', True):
                result['cultural_notes'].append(tone_analysis['explanation'])
        
        # STEP 6: Cultural warnings (File 8)
        cultural_warnings = self._check_cultural_warnings(corrected_text, target_lang)
        if cultural_warnings:
            result['metadata']['pipeline_steps'].append('cultural_check')
            result['warnings'].extend(cultural_warnings)
        
        # STEP 7: Religious terms (File 9)
        religious_detected = self._detect_religious_terms(corrected_text, source_lang, target_lang)
        if religious_detected:
            result['metadata']['pipeline_steps'].append('religious_terms')
            result['enrichment']['religious_terms'] = religious_detected
        
        # STEP 8: Road signs (File 10)
        road_signs_detected = self._detect_road_signs(corrected_text, target_lang)
        if road_signs_detected:
            result['metadata']['pipeline_steps'].append('road_signs')
            result['enrichment']['road_signs'] = road_signs_detected
        
        # STEP 9: Detect ambiguous words (File 3)
        ambiguous_words = self._detect_ambiguous_words(corrected_text, source_lang)
        if ambiguous_words:
            result['metadata']['pipeline_steps'].append('ambiguity_detection')
            result['enrichment']['ambiguous_words'] = ambiguous_words
            result['warnings'].append(f"Found {len(ambiguous_words)} ambiguous word(s) - may need clarification")
        
        # STEP 10: Professional dictionary lookup (Files 13-14)
        dictionary_enrichment = self._enrich_with_dictionaries(
            corrected_text, source_lang, target_lang
        )
        if dictionary_enrichment:
            result['metadata']['pipeline_steps'].append('dictionary_enrichment')
            result['enrichment']['dictionary_data'] = dictionary_enrichment
        
        # STEP 11: Build translation prompt with context
        translation_prompt = self._build_translation_prompt(
            corrected_text,
            source_lang,
            target_lang,
            document_type,
            result['enrichment'],
            prefs
        )
        
        # STEP 12: Translate with GPT-4o-mini
        translated_text = self._translate_with_gpt(
            translation_prompt,
            source_lang,
            target_lang
        )
        
        if not translated_text:
            result['warnings'].append('Translation failed')
            result['confidence_score'] = 0.0
            return result
        
        result['translated_text'] = translated_text
        result['metadata']['pipeline_steps'].append('gpt_translation')
        
        # STEP 13: Calculate confidence score
        result['confidence_score'] = self._calculate_confidence(
            text,
            translated_text,
            result['enrichment'],
            result['warnings']
        )
        
        # STEP 14: Generate alternatives (if requested)
        if prefs.get('include_alternatives', True):
            result['alternatives'] = self._generate_alternatives(
                text, source_lang, target_lang, result['enrichment']
            )
        
        logger.info(f"Translation complete: {len(result['metadata']['pipeline_steps'])} steps, confidence: {result['confidence_score']:.2f}")
        
        return result
    
    # ============================================================================
    # PIPELINE STEP METHODS
    # ============================================================================
    
    def _apply_spell_correction(self, text: str, lang: str, 
                                doc_type: Optional[str]) -> Tuple[str, List[Dict]]:
        """Apply spell correction (File 2)"""
        try:
            corrected = spell_corrector.correct_text(text, lang, doc_type)
            return corrected['corrected_text'], corrected.get('corrections', [])
        except Exception as e:
            logger.error(f"Spell correction error: {e}")
            return text, []
    
    def _detect_idioms(self, text: str, source_lang: str, 
                      target_lang: str) -> List[Dict]:
        """Detect idioms (File 4)"""
        try:
            detected = idiom_db.detect_idioms(text, source_lang)
            
            idioms_with_translations = []
            for idiom_info in detected:
                translation = idiom_db.translate_idiom(
                    idiom_info['idiom'],
                    source_lang,
                    target_lang
                )
                if translation:
                    idioms_with_translations.append({
                        'original': idiom_info['idiom'],
                        'translation': translation['cultural_equivalent'],
                        'literal_meaning': translation.get('literal_meaning', ''),
                        'cultural_note': translation.get('explanation', '')
                    })
            
            return idioms_with_translations
        except Exception as e:
            logger.error(f"Idiom detection error: {e}")
            return []
    
    def _detect_slang(self, text: str, source_lang: str, target_lang: str,
                     region: Optional[str]) -> List[Dict]:
        """Detect slang (File 5)"""
        try:
            detected = slang_db.detect_slang(text, source_lang)
            
            slang_with_translations = []
            for slang_info in detected:
                translation = slang_db.translate_slang(
                    slang_info['slang'],
                    source_lang,
                    target_lang,
                    region
                )
                if translation:
                    slang_with_translations.append({
                        'original': slang_info['slang'],
                        'translation': translation.get('translation', ''),
                        'regional_variants': translation.get('regional_variants', {})
                    })
            
            return slang_with_translations
        except Exception as e:
            logger.error(f"Slang detection error: {e}")
            return []
    
    def _analyze_profanity(self, text: str, source_lang: str, target_lang: str,
                          preserve_intensity: bool) -> Dict:
        """Analyze profanity (File 6)"""
        try:
            return profanity_handler.translate_text_with_profanity(
                text,
                source_lang,
                target_lang,
                preserve_intensity=preserve_intensity
            )
        except Exception as e:
            logger.error(f"Profanity analysis error: {e}")
            return {'contains_profanity': False}
    
    def _analyze_tone(self, text: str) -> Dict:
        """Analyze tone/sarcasm (File 7)"""
        try:
            return sarcasm_detector.detect_sarcasm(text)
        except Exception as e:
            logger.error(f"Tone analysis error: {e}")
            return {'is_sarcastic': False, 'tone': 'neutral'}
    
    def _check_cultural_warnings(self, text: str, target_culture: str) -> List[str]:
        """Check cultural warnings (File 8)"""
        try:
            warnings = cultural_intel.check_gesture_warning(text, target_culture)
            if warnings:
                return [cultural_intel.generate_cultural_warning(warnings)]
            return []
        except Exception as e:
            logger.error(f"Cultural check error: {e}")
            return []
    
    def _detect_religious_terms(self, text: str, source_lang: str, 
                               target_lang: str) -> List[Dict]:
        """Detect religious terms (File 9)"""
        try:
            # Simple word tokenization
            words = text.split()
            religious_found = []
            
            for word in words:
                clean_word = word.strip('.,!?;:').lower()
                translation = religious_terms.translate_religious_term(
                    clean_word, source_lang, target_lang
                )
                if translation:
                    religious_found.append({
                        'term': clean_word,
                        'translation': translation['translation'],
                        'theological_meaning': translation.get('theological_meaning', '')
                    })
            
            return religious_found
        except Exception as e:
            logger.error(f"Religious term detection error: {e}")
            return []
    
    def _detect_road_signs(self, text: str, target_lang: str) -> List[Dict]:
        """Detect road signs (File 10)"""
        try:
            # Check if text contains common road sign keywords
            road_sign_keywords = ['stop', 'yield', 'speed limit', 'no parking', 
                                 'one way', 'do not enter', 'school zone']
            
            signs_found = []
            text_upper = text.upper()
            
            for keyword in road_sign_keywords:
                if keyword.upper() in text_upper:
                    sign_info = road_signs.get_sign_info(keyword, target_lang)
                    if sign_info:
                        signs_found.append({
                            'sign': keyword,
                            'translation': sign_info['translation'],
                            'explanation': sign_info['eli5_explanation'],
                            'what_to_do': sign_info.get('what_to_do', [])
                        })
            
            return signs_found
        except Exception as e:
            logger.error(f"Road sign detection error: {e}")
            return []
    
    def _detect_ambiguous_words(self, text: str, source_lang: str) -> List[Dict]:
        """Detect ambiguous words (File 3)"""
        try:
            words = text.split()
            ambiguous = []
            
            for word in words:
                clean_word = word.strip('.,!?;:').lower()
                if context_handler.is_ambiguous(clean_word, source_lang):
                    meanings = context_handler.get_all_meanings(clean_word, source_lang)
                    if meanings:
                        ambiguous.append({
                            'word': clean_word,
                            'meanings': meanings,
                            'needs_clarification': True
                        })
            
            return ambiguous
        except Exception as e:
            logger.error(f"Ambiguous word detection error: {e}")
            return []
    
    def _enrich_with_dictionaries(self, text: str, source_lang: str,
                                  target_lang: str) -> Dict:
        """Enrich with professional dictionaries (Files 13-14)"""
        enrichment = {
            'definitions_added': 0,
            'words_looked_up': []
        }
        
        try:
            # Extract key content words (nouns, verbs, adjectives)
            # Simple heuristic: words longer than 4 characters
            words = [w.strip('.,!?;:').lower() for w in text.split() if len(w) > 4]
            unique_words = list(set(words))[:5]  # Limit to 5 words to save API quota
            
            for word in unique_words:
                # Try cache first
                cached = dictionary_cache.get(word, 'mw' if source_lang == 'en' else 'rae', source_lang)
                
                if cached:
                    enrichment['words_looked_up'].append({
                        'word': word,
                        'source': 'cache',
                        'definition': cached.get('entries', [{}])[0].get('definitions', [{}])[0].get('definition', '')
                    })
                else:
                    # Lookup in dictionary
                    if source_lang == 'en':
                        definition = mw_api.get_simple_definition(word)
                        if definition:
                            enrichment['words_looked_up'].append({
                                'word': word,
                                'source': 'merriam-webster',
                                'definition': definition
                            })
                    elif source_lang == 'es':
                        definition = rae_scraper.get_simple_definition(word)
                        if definition:
                            enrichment['words_looked_up'].append({
                                'word': word,
                                'source': 'rae',
                                'definition': definition
                            })
            
            enrichment['definitions_added'] = len(enrichment['words_looked_up'])
            
        except Exception as e:
            logger.error(f"Dictionary enrichment error: {e}")
        
        return enrichment
    
    # ============================================================================
    # GPT TRANSLATION
    # ============================================================================
    
    def _build_translation_prompt(self, text: str, source_lang: str, target_lang: str,
                                 doc_type: Optional[str], enrichment: Dict,
                                 prefs: Dict) -> str:
        """Build comprehensive translation prompt with all context"""
        
        prompt = f"""You are a professional human translator specializing in {source_lang} to {target_lang} translation.

TRANSLATION TASK:
Translate the following text from {source_lang} to {target_lang}.

ORIGINAL TEXT:
{text}

CRITICAL INSTRUCTIONS:
"""
        
        # Add document type context
        if doc_type:
            prompt += f"\n- Document type: {doc_type.upper()}"
            prompt += f"\n- Use appropriate terminology for {doc_type} documents"
        
        # Add idiom context
        if enrichment.get('idioms'):
            prompt += "\n\nIDIOMS DETECTED:"
            for idiom in enrichment['idioms']:
                prompt += f"\n- '{idiom['original']}' should be translated as '{idiom['translation']}' (NOT literal)"
        
        # Add slang context
        if enrichment.get('slang'):
            prompt += "\n\nSLANG DETECTED:"
            for slang in enrichment['slang']:
                prompt += f"\n- '{slang['original']}' → '{slang['translation']}'"
                if prefs.get('regional_variant') and slang.get('regional_variants'):
                    prompt += f" (Regional: {prefs['regional_variant']})"
        
        # Add profanity context
        if enrichment.get('profanity', {}).get('contains_profanity'):
            if prefs.get('preserve_profanity'):
                prompt += "\n\nPROFANITY: Preserve intensity exactly. Do NOT water down curse words."
            else:
                prompt += "\n\nPROFANITY: Use family-friendly alternatives."
        
        # Add sarcasm context
        if enrichment.get('tone', {}).get('is_sarcastic'):
            if prefs.get('preserve_sarcasm'):
                prompt += "\n\nTONE: This text is SARCASTIC. Preserve the sarcastic tone in translation."
        
        # Add religious terms context
        if enrichment.get('religious_terms'):
            prompt += "\n\nRELIGIOUS TERMS:"
            for term in enrichment['religious_terms']:
                prompt += f"\n- '{term['term']}' → '{term['translation']}' ({term['theological_meaning']})"
        
        # Add road signs context
        if enrichment.get('road_signs'):
            prompt += "\n\nROAD SIGNS: Include simple explanations (ELI5 style)"
        
        prompt += f"\n\nTRANSLATION:"
        
        return prompt
    
    def _translate_with_gpt(self, prompt: str, source_lang: str, 
                           target_lang: str) -> Optional[str]:
        """Execute translation with GPT-4o-mini"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": f"You are a professional translator from {source_lang} to {target_lang}."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            
            translation = response.choices[0].message.content.strip()
            return translation
            
        except Exception as e:
            logger.error(f"GPT translation error: {e}")
            return None
    
    # ============================================================================
    # CONFIDENCE & ALTERNATIVES
    # ============================================================================
    
    def _calculate_confidence(self, original: str, translated: str,
                             enrichment: Dict, warnings: List[str]) -> float:
        """Calculate translation confidence score (0-1)"""
        base_confidence = 0.85
        
        # Deduct for warnings
        confidence = base_confidence - (len(warnings) * 0.05)
        
        # Deduct for ambiguous words
        if enrichment.get('ambiguous_words'):
            confidence -= len(enrichment['ambiguous_words']) * 0.03
        
        # Add for enrichment
        if enrichment.get('idioms'):
            confidence += 0.05
        if enrichment.get('dictionary_data', {}).get('definitions_added', 0) > 0:
            confidence += 0.03
        
        # Ensure bounds
        return max(0.0, min(1.0, confidence))
    
    def _generate_alternatives(self, text: str, source_lang: str,
                              target_lang: str, enrichment: Dict) -> List[Dict]:
        """Generate alternative translations"""
        alternatives = []
        
        # If profanity detected, offer clean version as alternative
        if enrichment.get('profanity', {}).get('contains_profanity'):
            alternatives.append({
                'type': 'clean_version',
                'description': 'Family-friendly version (no profanity)',
                'note': 'Use clean_version=True in preferences'
            })
        
        # If regional slang detected, offer other regions
        if enrichment.get('slang'):
            alternatives.append({
                'type': 'regional_variants',
                'description': 'Different Spanish regional variants available',
                'options': ['mexico', 'spain', 'colombia', 'argentina']
            })
        
        return alternatives


# ============================================================================
# GLOBAL INSTANCE
# ============================================================================
translation_engine = TranslationEngine()

# Convenience function
def translate_text(text: str, source_lang: str = 'en', target_lang: str = 'es',
                  document_type: Optional[str] = None,
                  user_preferences: Optional[Dict] = None) -> Dict:
    """
    Convenience function: Translate text with full pipeline
    
    Args:
        text: Text to translate
        source_lang: Source language (en, es, pt, fr)
        target_lang: Target language
        document_type: Optional (irs, uscis, medical, utility)
        user_preferences: Optional preferences dict
    
    Returns:
        Full translation result with enrichment
    """
    return translation_engine.translate(
        text, source_lang, target_lang, document_type, user_preferences
    )


# Test example
if __name__ == "__main__":
    print("\n" + "="*60)
    print("TRANSLATION ENGINE - THE ORCHESTRATOR")
    print("="*60)
    
    # Test translation
    test_text = "Oh great, another bill. Just what I needed!"
    
    print(f"\n**Original Text:**")
    print(test_text)
    
    result = translate_text(test_text, 'en', 'es')
    
    print(f"\n**Translated Text:**")
    print(result['translated_text'])
    
    print(f"\n**Confidence Score:** {result['confidence_score']:.2f}")
    
    print(f"\n**Pipeline Steps:**")
    for step in result['metadata']['pipeline_steps']:
        print(f"  ✓ {step}")
    
    if result['warnings']:
        print(f"\n**Warnings:**")
        for warning in result['warnings']:
            print(f"  ⚠️ {warning}")
    
    if result['enrichment']:
        print(f"\n**Enrichment Data:**")
        for key, value in result['enrichment'].items():
            print(f"  • {key}: {value}")
    
    print("\n" + "="*60)
