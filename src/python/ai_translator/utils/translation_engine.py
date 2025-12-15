"""
Translation Engine - Orchestrates All Translation Systems
The brain that coordinates all utility files into one cohesive translation pipeline.

This version adds a fallback to the standard OpenAI API.  It will use Azure OpenAI
only if both `AZURE_OPENAI_API_KEY` and `AZURE_OPENAI_ENDPOINT` environment
variables are present; otherwise it falls back to the regular OpenAI client
using `OPENAI_API_KEY`.  If no API key is available, translations will not
be performed and a warning will be logged.
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
import os
import openai
from openai import AzureOpenAI

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
    Orchestrates all translation systems into a unified pipeline.

    This class coordinates spell correction, idiom and slang detection,
    profanity handling, sarcasm detection, cultural warnings, religious terms,
    road sign identification, ambiguous word handling, and dictionary
    enrichment before finally translating the text using GPT models.

    It supports both Azure OpenAI and standard OpenAI backends.  Azure will
    be used if the required environment variables are present; otherwise it
    falls back to OpenAI with the `OPENAI_API_KEY` variable.
    """

    def __init__(self):
        """Initialize the translation engine and underlying GPT client."""
        # Determine which client to use
        azure_key = os.getenv("AZURE_OPENAI_API_KEY")
        azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        if azure_key and azure_endpoint:
            try:
                self.client = AzureOpenAI(
                    api_key=azure_key,
                    api_version="2024-02-15-preview",
                    azure_endpoint=azure_endpoint,
                )
                self._use_azure = True
                logger.info("Using Azure OpenAI for translation.")
            except Exception as e:
                logger.warning(f"Failed to initialize AzureOpenAI client: {e}")
                self.client = None
                self._use_azure = False
        else:
            # Fall back to standard OpenAI client
            openai_key = os.getenv("OPENAI_API_KEY")
            if openai_key:
                try:
                    self.client = openai.OpenAI(api_key=openai_key)
                    self._use_azure = False
                    logger.info("Using standard OpenAI for translation.")
                except Exception as e:
                    logger.warning(f"Failed to initialize OpenAI client: {e}")
                    self.client = None
                    self._use_azure = False
            else:
                logger.warning(
                    "No OpenAI credentials found. Translation will be disabled."
                )
                self.client = None
                self._use_azure = False

        # Model configuration (both Azure and standard clients accept this name)
        self.model = "gpt-4o-mini"
        self.max_tokens = 2000
        self.temperature = 0.3  # Lower = more consistent translations

        # Default user preferences
        self.default_preferences = {
            'preserve_profanity': True,
            'preserve_sarcasm': True,
            'regional_variant': None,  # e.g., 'mexico', 'spain'
            'include_alternatives': True,
            'include_cultural_notes': True,
        }

    # =====================================================================
    # MAIN TRANSLATION PIPELINE
    # =====================================================================
    def translate(
        self,
        text: str,
        source_lang: str = 'en',
        target_lang: str = 'es',
        document_type: Optional[str] = None,
        user_preferences: Optional[Dict] = None,
    ) -> Dict:
        """
        Perform a full translation with all enrichment steps.

        Args:
            text: The text to translate.
            source_lang: Source language code (en, es, pt, fr).
            target_lang: Target language code.
            document_type: Optional document type (irs, uscis, medical, etc.).
            user_preferences: Optional preferences overriding defaults.

        Returns:
            A dictionary containing the original and translated text, confidence
            score, warnings, cultural notes, alternatives, enrichment data, and
            metadata about the translation process.
        """
        prefs = {**self.default_preferences, **(user_preferences or {})}

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
                'pipeline_steps': [],
            },
        }

        if not text or not text.strip():
            result['warnings'].append('Empty input text')
            return result

        # STEP 1: Spell correction
        corrected_text, spell_corrections = self._apply_spell_correction(
            text, source_lang, document_type
        )
        if spell_corrections:
            result['metadata']['pipeline_steps'].append('spell_correction')
            result['metadata']['spell_corrections'] = spell_corrections

        # STEP 2: Idiom detection
        idioms_found = self._detect_idioms(corrected_text, source_lang, target_lang)
        if idioms_found:
            result['metadata']['pipeline_steps'].append('idiom_detection')
            result['enrichment']['idioms'] = idioms_found
            result['cultural_notes'].extend(
                [i.get('cultural_note', '') for i in idioms_found]
            )

        # STEP 3: Slang detection
        slang_found = self._detect_slang(
            corrected_text,
            source_lang,
            target_lang,
            prefs.get('regional_variant'),
        )
        if slang_found:
            result['metadata']['pipeline_steps'].append('slang_detection')
            result['enrichment']['slang'] = slang_found

        # STEP 4: Profanity handling
        profanity_analysis = self._analyze_profanity(
            corrected_text,
            source_lang,
            target_lang,
            prefs.get('preserve_profanity', True),
        )
        if profanity_analysis.get('contains_profanity'):
            result['metadata']['pipeline_steps'].append('profanity_detection')
            result['enrichment']['profanity'] = profanity_analysis
            if profanity_analysis.get('warning'):
                result['warnings'].append(profanity_analysis['warning'])

        # STEP 5: Sarcasm/tone detection
        tone_analysis = self._analyze_tone(corrected_text)
        if tone_analysis.get('is_sarcastic'):
            result['metadata']['pipeline_steps'].append('sarcasm_detection')
            result['enrichment']['tone'] = tone_analysis
            if prefs.get('preserve_sarcasm', True):
                result['cultural_notes'].append(tone_analysis['explanation'])

        # STEP 6: Cultural warnings
        cultural_warnings = self._check_cultural_warnings(corrected_text, target_lang)
        if cultural_warnings:
            result['metadata']['pipeline_steps'].append('cultural_check')
            result['warnings'].extend(cultural_warnings)

        # STEP 7: Religious terms
        religious_detected = self._detect_religious_terms(
            corrected_text, source_lang, target_lang
        )
        if religious_detected:
            result['metadata']['pipeline_steps'].append('religious_terms')
            result['enrichment']['religious_terms'] = religious_detected

        # STEP 8: Road signs
        road_signs_detected = self._detect_road_signs(corrected_text, target_lang)
        if road_signs_detected:
            result['metadata']['pipeline_steps'].append('road_signs')
            result['enrichment']['road_signs'] = road_signs_detected

        # STEP 9: Ambiguous words
        ambiguous_words = self._detect_ambiguous_words(corrected_text, source_lang)
        if ambiguous_words:
            result['metadata']['pipeline_steps'].append('ambiguity_detection')
            result['enrichment']['ambiguous_words'] = ambiguous_words
            result['warnings'].append(
                f"Found {len(ambiguous_words)} ambiguous word(s) - may need clarification"
            )

        # STEP 10: Dictionary enrichment
        dictionary_enrichment = self._enrich_with_dictionaries(
            corrected_text, source_lang, target_lang
        )
        if dictionary_enrichment:
            result['metadata']['pipeline_steps'].append('dictionary_enrichment')
            result['enrichment']['dictionary_data'] = dictionary_enrichment

        # STEP 11: Build translation prompt
        translation_prompt = self._build_translation_prompt(
            corrected_text,
            source_lang,
            target_lang,
            document_type,
            result['enrichment'],
            prefs,
        )

        # STEP 12: Translate with GPT
        translated_text = self._translate_with_gpt(
            translation_prompt, source_lang, target_lang
        )
        if not translated_text:
            result['warnings'].append('Translation failed')
            result['confidence_score'] = 0.0
            return result

        result['translated_text'] = translated_text
        result['metadata']['pipeline_steps'].append('gpt_translation')

        # STEP 13: Calculate confidence
        result['confidence_score'] = self._calculate_confidence(
            text, translated_text, result['enrichment'], result['warnings']
        )

        # STEP 14: Generate alternatives
        if prefs.get('include_alternatives', True):
            result['alternatives'] = self._generate_alternatives(
                text, source_lang, target_lang, result['enrichment']
            )

        logger.info(
            f"Translation complete: {len(result['metadata']['pipeline_steps'])} steps, "
            f"confidence: {result['confidence_score']:.2f}"
        )
        return result

    # =====================================================================
    # PIPELINE STEP METHODS
    # =====================================================================
    def _apply_spell_correction(
        self, text: str, lang: str, doc_type: Optional[str]
    ) -> Tuple[str, List[Dict]]:
        try:
            corrected = spell_corrector.correct_text(text, lang, doc_type)
            return corrected['corrected_text'], corrected.get('corrections', [])
        except Exception as e:
            logger.error(f"Spell correction error: {e}")
            return text, []

    def _detect_idioms(
        self, text: str, source_lang: str, target_lang: str
    ) -> List[Dict]:
        try:
            detected = idiom_db.detect_idioms(text, source_lang)
            idioms_with_translations = []
            for idiom_info in detected:
                translation = idiom_db.translate_idiom(
                    idiom_info['idiom'], source_lang, target_lang
                )
                if translation:
                    idioms_with_translations.append({
                        'original': idiom_info['idiom'],
                        'translation': translation['cultural_equivalent'],
                        'literal_meaning': translation.get('literal_meaning', ''),
                        'cultural_note': translation.get('explanation', ''),
                    })
            return idioms_with_translations
        except Exception as e:
            logger.error(f"Idiom detection error: {e}")
            return []

    def _detect_slang(
        self, text: str, source_lang: str, target_lang: str, region: Optional[str]
    ) -> List[Dict]:
        try:
            detected = slang_db.detect_slang(text, source_lang)
            slang_with_translations = []
            for slang_info in detected:
                translation = slang_db.translate_slang(
                    slang_info['slang'], source_lang, target_lang, region
                )
                if translation:
                    slang_with_translations.append({
                        'original': slang_info['slang'],
                        'translation': translation.get('translation', ''),
                        'regional_variants': translation.get('regional_variants', {}),
                    })
            return slang_with_translations
        except Exception as e:
            logger.error(f"Slang detection error: {e}")
            return []

    def _analyze_profanity(
        self, text: str, source_lang: str, target_lang: str, preserve_intensity: bool
    ) -> Dict:
        try:
            return profanity_handler.translate_text_with_profanity(
                text, source_lang, target_lang, preserve_intensity=preserve_intensity
            )
        except Exception as e:
            logger.error(f"Profanity analysis error: {e}")
            return {'contains_profanity': False}

    def _analyze_tone(self, text: str) -> Dict:
        try:
            return sarcasm_detector.detect_sarcasm(text)
        except Exception as e:
            logger.error(f"Tone analysis error: {e}")
            return {'is_sarcastic': False, 'tone': 'neutral'}

    def _check_cultural_warnings(self, text: str, target_culture: str) -> List[str]:
        try:
            warnings = cultural_intel.check_gesture_warning(text, target_culture)
            if warnings:
                return [cultural_intel.generate_cultural_warning(warnings)]
            return []
        except Exception as e:
            logger.error(f"Cultural check error: {e}")
            return []

    def _detect_religious_terms(
        self, text: str, source_lang: str, target_lang: str
    ) -> List[Dict]:
        try:
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
                        'theological_meaning': translation.get('theological_meaning', ''),
                    })
            return religious_found
        except Exception as e:
            logger.error(f"Religious term detection error: {e}")
            return []

    def _detect_road_signs(self, text: str, target_lang: str) -> List[Dict]:
        try:
            road_sign_keywords = [
                'stop', 'yield', 'speed limit', 'no parking', 'one way',
                'do not enter', 'school zone'
            ]
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
                            'what_to_do': sign_info.get('what_to_do', []),
                        })
            return signs_found
        except Exception as e:
            logger.error(f"Road sign detection error: {e}")
            return []

    def _detect_ambiguous_words(self, text: str, source_lang: str) -> List[Dict]:
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
                            'needs_clarification': True,
                        })
            return ambiguous
        except Exception as e:
            logger.error(f"Ambiguous word detection error: {e}")
            return []

    def _enrich_with_dictionaries(
        self, text: str, source_lang: str, target_lang: str
    ) -> Dict:
        enrichment = {
            'definitions_added': 0,
            'words_looked_up': [],
        }
        try:
            # Heuristic: look up up to 5 unique words longer than 4 characters
            words = [w.strip('.,!?;:').lower() for w in text.split() if len(w) > 4]
            unique_words = list(set(words))[:5]
            for word in unique_words:
                cached = dictionary_cache.get(
                    word, 'mw' if source_lang == 'en' else 'rae', source_lang
                )
                if cached:
                    enrichment['words_looked_up'].append({
                        'word': word,
                        'source': 'cache',
                        'definition': cached.get('entries', [{}])[0]
                        .get('definitions', [{}])[0]
                        .get('definition', ''),
                    })
                else:
                    # Lookup from dictionary
                    if source_lang == 'en':
                        definition = mw_api.get_simple_definition(word)
                        if definition:
                            enrichment['words_looked_up'].append({
                                'word': word,
                                'source': 'merriam-webster',
                                'definition': definition,
                            })
                    elif source_lang == 'es':
                        definition = rae_scraper.get_simple_definition(word)
                        if definition:
                            enrichment['words_looked_up'].append({
                                'word': word,
                                'source': 'rae',
                                'definition': definition,
                            })
            enrichment['definitions_added'] = len(enrichment['words_looked_up'])
        except Exception as e:
            logger.error(f"Dictionary enrichment error: {e}")
        return enrichment

    # =====================================================================
    # GPT TRANSLATION
    # =====================================================================
    def _build_translation_prompt(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        doc_type: Optional[str],
        enrichment: Dict,
        prefs: Dict,
    ) -> str:
        prompt = (
            f"You are a professional human translator specializing in {source_lang} to {target_lang} translation.\n\n"
            "TRANSLATION TASK:\n"
            f"Translate the following text from {source_lang} to {target_lang}.\n\n"
            "ORIGINAL TEXT:\n"
            f"{text}\n\n"
            "CRITICAL INSTRUCTIONS:\n"
        )
        # Document type context
        if doc_type:
            prompt += (
                f"\n- Document type: {doc_type.upper()}"
                f"\n- Use appropriate terminology for {doc_type} documents"
            )
        # Idioms context
        if enrichment.get('idioms'):
            prompt += "\n\nIDIOMS DETECTED:"
            for idiom in enrichment['idioms']:
                prompt += (
                    f"\n- '{idiom['original']}' should be translated as "
                    f"'{idiom['translation']}' (NOT literal)"
                )
        # Slang context
        if enrichment.get('slang'):
            prompt += "\n\nSLANG DETECTED:"
            for slang in enrichment['slang']:
                prompt += f"\n- '{slang['original']}' → '{slang['translation']}'"
                if prefs.get('regional_variant') and slang.get('regional_variants'):
                    prompt += f" (Regional: {prefs['regional_variant']})"
        # Profanity context
        if enrichment.get('profanity', {}).get('contains_profanity'):
            if prefs.get('preserve_profanity'):
                prompt += "\n\nPROFANITY: Preserve intensity exactly. Do NOT water down curse words."
            else:
                prompt += "\n\nPROFANITY: Use family-friendly alternatives."
        # Sarcasm context
        if enrichment.get('tone', {}).get('is_sarcastic'):
            if prefs.get('preserve_sarcasm'):
                prompt += "\n\nTONE: This text is SARCASTIC. Preserve the sarcastic tone in translation."
        # Religious terms context
        if enrichment.get('religious_terms'):
            prompt += "\n\nRELIGIOUS TERMS:"
            for term in enrichment['religious_terms']:
                prompt += (
                    f"\n- '{term['term']}' → '{term['translation']}' "
                    f"({term['theological_meaning']})"
                )
        # Road signs context
        if enrichment.get('road_signs'):
            prompt += "\n\nROAD SIGNS: Include simple explanations (ELI5 style)"
        prompt += "\n\nTRANSLATION:"
        return prompt

    def _translate_with_gpt(
        self, prompt: str, source_lang: str, target_lang: str
    ) -> Optional[str]:
        """Execute translation using the configured GPT client."""
        if not self.client:
            logger.warning("No GPT client available; cannot perform translation.")
            return None
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": f"You are a professional translator from {source_lang} to {target_lang}.",
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature,
            )
            translation = response.choices[0].message.content.strip()
            return translation
        except Exception as e:
            logger.error(f"GPT translation error: {e}")
            return None

    # =====================================================================
    # CONFIDENCE & ALTERNATIVES
    # =====================================================================
    def _calculate_confidence(
        self, original: str, translated: str, enrichment: Dict, warnings: List[str]
    ) -> float:
        base_confidence = 0.85
        confidence = base_confidence - (len(warnings) * 0.05)
        if enrichment.get('ambiguous_words'):
            confidence -= len(enrichment['ambiguous_words']) * 0.03
        if enrichment.get('idioms'):
            confidence += 0.05
        if enrichment.get('dictionary_data', {}).get('definitions_added', 0) > 0:
            confidence += 0.03
        return max(0.0, min(1.0, confidence))

    def _generate_alternatives(
        self, text: str, source_lang: str, target_lang: str, enrichment: Dict
    ) -> List[Dict]:
        alternatives = []
        if enrichment.get('profanity', {}).get('contains_profanity'):
            alternatives.append({
                'type': 'clean_version',
                'description': 'Family-friendly version (no profanity)',
                'note': 'Use clean_version=True in preferences',
            })
        if enrichment.get('slang'):
            alternatives.append({
                'type': 'regional_variants',
                'description': 'Different regional variants available',
                'options': ['mexico', 'spain', 'colombia', 'argentina'],
            })
        return alternatives


# =====================================================================
# GLOBAL INSTANCE
# =====================================================================
translation_engine = TranslationEngine()


def translate_text(
    text: str,
    source_lang: str = 'en',
    target_lang: str = 'es',
    document_type: Optional[str] = None,
    user_preferences: Optional[Dict] = None,
) -> Dict:
    """Convenience function to translate text using the global instance."""
    return translation_engine.translate(text, source_lang, target_lang, document_type, user_preferences)
