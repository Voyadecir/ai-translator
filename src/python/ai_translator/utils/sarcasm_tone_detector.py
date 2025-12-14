"""
Sarcasm & Tone Detector - Preserves Emotional Intent
Detects sarcasm, irony, humor, and emotional tone
NEVER neutralizes tone - preserves the speaker's intended attitude

The hardest part of translation: Sarcasm doesn't always translate literally.
"Oh great, another bill. Just what I needed." ← Sarcasm
Literal translation loses the sarcasm. This module preserves it.
"""

import re
from typing import Dict, List, Optional, Tuple
from functools import lru_cache

class SarcasmToneDetector:
    """
    Detects and preserves sarcasm, irony, and emotional tone in translation
    
    Key Features:
    - Sarcasm detection (phrases + context analysis)
    - Tone classification (sincere, sarcastic, angry, playful, etc.)
    - Sarcasm markers for translation (so target language maintains tone)
    - Cultural adaptation (sarcasm works differently across cultures)
    
    Tone Categories:
    - Sarcastic/Ironic
    - Sincere/Genuine
    - Angry/Frustrated
    - Playful/Joking
    - Formal/Professional
    - Condescending/Patronizing
    """
    
    def __init__(self):
        # Sarcasm indicators
        self.sarcasm_phrases = self._load_sarcasm_phrases()
        
        # Tone markers
        self.tone_markers = self._load_tone_markers()
        
        # Punctuation patterns that indicate tone
        self.punctuation_patterns = self._compile_punctuation_patterns()
    
    # ============================================================================
    # SARCASM INDICATORS
    # ============================================================================
    
    def _load_sarcasm_phrases(self) -> Dict[str, Dict]:
        """
        Common sarcastic phrases and their translations
        """
        return {
            # CLASSIC SARCASM
            "oh great": {
                "sarcasm_probability": 0.95,
                "meaning": "This is bad/annoying (opposite of literal meaning)",
                "es": {
                    "sarcastic": "oh genial / qué bien",
                    "markers": ["(con sarcasmo)", "ironía"],
                    "notes": "Tone is everything - needs context"
                },
                "examples_en": [
                    "Oh great, another meeting.",
                    "Oh great, it's raining."
                ],
                "examples_es": [
                    "Oh genial, otra reunión.",
                    "Qué bien, está lloviendo."
                ]
            },
            
            "just what i needed": {
                "sarcasm_probability": 0.90,
                "meaning": "This is the opposite of what I wanted",
                "es": {
                    "sarcastic": "justo lo que necesitaba",
                    "markers": ["(irónico)", "con ironía"],
                    "notes": "Direct translation works, but tone must be preserved"
                },
                "examples_en": [
                    "A flat tire? Just what I needed!",
                    "Another bill. Just what I needed."
                ],
                "examples_es": [
                    "¿Una llanta ponchada? ¡Justo lo que necesitaba!",
                    "Otra factura. Justo lo que necesitaba."
                ]
            },
            
            "yeah right": {
                "sarcasm_probability": 0.98,
                "meaning": "I don't believe you / that's not true",
                "es": {
                    "sarcastic": "sí claro / sí cómo no",
                    "markers": ["(sarcástico)"],
                    "notes": "'Cómo no' is very sarcastic in Spanish"
                },
                "examples_en": [
                    "Yeah right, like that's going to happen.",
                    "You'll pay me back? Yeah right."
                ],
                "examples_es": [
                    "Sí claro, como si eso fuera a pasar.",
                    "¿Me vas a pagar? Sí cómo no."
                ]
            },
            
            "sure": {
                "sarcasm_probability": 0.70,
                "context_dependent": True,
                "meaning": "I don't believe you / I doubt it",
                "es": {
                    "sarcastic": "claro / seguro",
                    "sincere": "claro / por supuesto",
                    "markers": ["(con sarcasmo)", "tone is critical"],
                    "notes": "Context is EVERYTHING - same word, opposite meanings"
                },
                "examples_en_sarcastic": [
                    "You're the smartest person? Sure.",
                    "Sure, blame me for everything."
                ],
                "examples_en_sincere": [
                    "Can you help? Sure!",
                    "Sure, I'll be there."
                ],
                "examples_es_sarcastic": [
                    "¿Eres la persona más lista? Claro.",
                    "Claro, échame la culpa de todo."
                ],
                "examples_es_sincere": [
                    "¿Me ayudas? ¡Claro!",
                    "Claro, estaré ahí."
                ]
            },
            
            "fantastic": {
                "sarcasm_probability": 0.75,
                "context_dependent": True,
                "meaning": "This is terrible (when sarcastic) / This is great (when sincere)",
                "es": {
                    "sarcastic": "fantástico / maravilloso (con sarcasmo)",
                    "sincere": "fantástico / maravilloso",
                    "notes": "Check context - negative situation = sarcastic"
                },
                "examples_en_sarcastic": [
                    "I lost my job. Fantastic.",
                    "The car broke down. Just fantastic."
                ],
                "examples_en_sincere": [
                    "I got the promotion! Fantastic!",
                    "That's fantastic news!"
                ],
                "examples_es_sarcastic": [
                    "Perdí mi trabajo. Fantástico.",
                    "El carro se descompuso. Simplemente fantástico."
                ],
                "examples_es_sincere": [
                    "¡Conseguí el ascenso! ¡Fantástico!",
                    "¡Qué noticia fantástica!"
                ]
            },
            
            "perfect": {
                "sarcasm_probability": 0.70,
                "context_dependent": True,
                "meaning": "This is bad (sarcastic) / This is good (sincere)",
                "es": {
                    "sarcastic": "perfecto (con ironía)",
                    "sincere": "perfecto",
                    "notes": "Negative context = sarcasm"
                },
                "examples_en_sarcastic": [
                    "It's raining. Perfect.",
                    "I forgot my wallet. Perfect."
                ],
                "examples_es_sarcastic": [
                    "Está lloviendo. Perfecto.",
                    "Olvidé mi cartera. Perfecto."
                ]
            },
            
            "wonderful": {
                "sarcasm_probability": 0.70,
                "context_dependent": True,
                "meaning": "This is awful (sarcastic) / This is great (sincere)",
                "es": {
                    "sarcastic": "maravilloso (con sarcasmo)",
                    "sincere": "maravilloso"
                },
                "examples_en_sarcastic": [
                    "Traffic jam. Wonderful.",
                    "Another delay. Wonderful."
                ],
                "examples_es_sarcastic": [
                    "Embotellamiento. Maravilloso.",
                    "Otro retraso. Maravilloso."
                ]
            },
            
            "how nice": {
                "sarcasm_probability": 0.80,
                "meaning": "This is not nice at all",
                "es": {
                    "sarcastic": "qué lindo / qué bonito (con sarcasmo)",
                    "notes": "Very common sarcastic phrase"
                },
                "examples_en": [
                    "He canceled again. How nice.",
                    "They raised the price. How nice."
                ],
                "examples_es": [
                    "Canceló otra vez. Qué lindo.",
                    "Subieron el precio. Qué bonito."
                ]
            },
            
            "brilliant": {
                "sarcasm_probability": 0.75,
                "context_dependent": True,
                "meaning": "That's stupid (sarcastic) / That's smart (sincere)",
                "es": {
                    "sarcastic": "brillante (con sarcasmo)",
                    "sincere": "brillante / genial"
                },
                "examples_en_sarcastic": [
                    "You forgot the keys. Brilliant.",
                    "Brilliant idea, genius."
                ],
                "examples_es_sarcastic": [
                    "Olvidaste las llaves. Brillante.",
                    "Brillante idea, genio."
                ]
            },
            
            "well done": {
                "sarcasm_probability": 0.65,
                "context_dependent": True,
                "meaning": "You messed up (sarcastic) / You did well (sincere)",
                "es": {
                    "sarcastic": "bien hecho (con sarcasmo)",
                    "sincere": "bien hecho / buen trabajo"
                },
                "examples_en_sarcastic": [
                    "You broke it. Well done.",
                    "Well done, you ruined everything."
                ],
                "examples_es_sarcastic": [
                    "Lo rompiste. Bien hecho.",
                    "Bien hecho, arruinaste todo."
                ]
            },
            
            "thanks a lot": {
                "sarcasm_probability": 0.80,
                "context_dependent": True,
                "meaning": "I'm not thankful (sarcastic) / I'm thankful (sincere)",
                "es": {
                    "sarcastic": "muchas gracias (con sarcasmo)",
                    "sincere": "muchas gracias"
                },
                "examples_en_sarcastic": [
                    "You told everyone my secret. Thanks a lot.",
                    "Thanks a lot for the help. (sarcastic - they didn't help)"
                ],
                "examples_en_sincere": [
                    "You saved me hours of work. Thanks a lot!",
                    "Thanks a lot for your help!"
                ],
                "examples_es_sarcastic": [
                    "Le contaste mi secreto a todos. Muchas gracias.",
                    "Muchas gracias por la ayuda. (sarcástico)"
                ],
                "examples_es_sincere": [
                    "Me ahorraste horas de trabajo. ¡Muchas gracias!",
                    "¡Muchas gracias por tu ayuda!"
                ]
            },
            
            "obviously": {
                "sarcasm_probability": 0.70,
                "context_dependent": True,
                "meaning": "It's not obvious at all / you're stating the obvious",
                "es": {
                    "sarcastic": "obviamente (con sarcasmo)",
                    "sincere": "obviamente"
                },
                "examples_en_sarcastic": [
                    "Obviously, I'm thrilled to work overtime. (not thrilled)",
                    "Obviously. (eye roll - stating the obvious)"
                ],
                "examples_es_sarcastic": [
                    "Obviamente, estoy encantado de trabajar horas extra.",
                    "Obviamente. (con sarcasmo)"
                ]
            },
            
            "as if": {
                "sarcasm_probability": 0.95,
                "meaning": "That will never happen / I don't believe it",
                "es": {
                    "sarcastic": "como si / sí claro",
                    "notes": "Very dismissive/sarcastic"
                },
                "examples_en": [
                    "He'll change? As if.",
                    "As if that's going to happen."
                ],
                "examples_es": [
                    "¿Él va a cambiar? Sí claro.",
                    "Como si eso fuera a pasar."
                ]
            },
            
            # Add 100+ more sarcasm patterns...
        }
    
    # ============================================================================
    # TONE MARKERS
    # ============================================================================
    
    def _load_tone_markers(self) -> Dict[str, Dict]:
        """
        Words/phrases that indicate specific emotional tones
        """
        return {
            # ANGER/FRUSTRATION
            "anger": {
                "indicators": [
                    "pissed off", "angry", "furious", "livid", "fed up",
                    "sick of", "had enough", "ridiculous", "unacceptable"
                ],
                "intensity_words": ["extremely", "absolutely", "totally", "completely"],
                "punctuation": ["!", "!!", "!!!"],
                "es_markers": ["enojado", "furioso", "harto", "ridículo"]
            },
            
            # PLAYFUL/JOKING
            "playful": {
                "indicators": [
                    "haha", "lol", "jk", "just kidding", "joking",
                    "kidding", "messing with you", "teasing"
                ],
                "punctuation": ["😂", "😄", "😆", ":)", ";)"],
                "es_markers": ["jaja", "bromeo", "es broma"]
            },
            
            # CONDESCENDING/PATRONIZING
            "condescending": {
                "indicators": [
                    "sweetheart", "honey", "dear", "bless your heart",
                    "cute", "adorable", "precious" (in wrong context)
                ],
                "tone_note": "Often disguised as politeness but insulting",
                "es_markers": ["cariño (sarcástico)", "qué lindo (sarcástico)"]
            },
            
            # EXCITEMENT/ENTHUSIASM
            "excitement": {
                "indicators": [
                    "amazing", "awesome", "incredible", "can't wait",
                    "so excited", "thrilled", "love it"
                ],
                "punctuation": ["!", "!!", "!!!", "😍", "🔥"],
                "es_markers": ["increíble", "emocionado", "me encanta"]
            },
            
            # DISAPPOINTMENT
            "disappointment": {
                "indicators": [
                    "disappointed", "let down", "expected better",
                    "shame", "unfortunate", "too bad"
                ],
                "punctuation": ["...", "😞", "😔"],
                "es_markers": ["decepcionado", "lástima", "qué pena"]
            }
        }
    
    # ============================================================================
    # PUNCTUATION PATTERNS
    # ============================================================================
    
    def _compile_punctuation_patterns(self) -> Dict[str, float]:
        """
        Punctuation patterns that indicate sarcasm/tone
        
        Returns: {pattern: sarcasm_probability}
        """
        return {
            # Excessive punctuation = emotion
            r'\.{3,}': 0.50,  # Ellipsis (...) = trailing off, skepticism
            r'!{2,}': 0.60,   # Multiple ! = strong emotion
            r'\?{2,}': 0.55,  # Multiple ? = disbelief
            r'[A-Z\s]{5,}': 0.40,  # ALL CAPS = shouting or sarcasm
            
            # Mixed punctuation
            r'!\?': 0.65,     # !? = surprise/disbelief
            r'\?!': 0.65,     # ?! = incredulity
        }
    
    # ============================================================================
    # DETECTION METHODS
    # ============================================================================
    
    def detect_sarcasm(self, text: str, context: str = None) -> Dict:
        """
        Detect if text contains sarcasm
        
        Args:
            text: The text to analyze
            context: Optional context (helps with ambiguous cases)
        
        Returns:
            - is_sarcastic: bool
            - confidence: 0.0 to 1.0
            - indicators: List of sarcasm indicators found
            - tone: Detected tone (sarcastic, playful, angry, etc.)
        """
        text_lower = text.lower().strip()
        
        indicators_found = []
        sarcasm_scores = []
        
        # Check for explicit sarcasm phrases
        for phrase, data in self.sarcasm_phrases.items():
            if phrase in text_lower:
                indicators_found.append({
                    'phrase': phrase,
                    'probability': data['sarcasm_probability'],
                    'type': 'explicit_phrase'
                })
                sarcasm_scores.append(data['sarcasm_probability'])
        
        # Check punctuation patterns
        for pattern, probability in self.punctuation_patterns.items():
            if re.search(pattern, text):
                indicators_found.append({
                    'pattern': pattern,
                    'probability': probability,
                    'type': 'punctuation'
                })
                sarcasm_scores.append(probability)
        
        # Check for negative context + positive words (classic sarcasm)
        negative_context_words = ['lost', 'broke', 'failed', 'problem', 'issue', 
                                 'wrong', 'bad', 'terrible', 'awful', 'worst']
        positive_words = ['great', 'perfect', 'wonderful', 'fantastic', 'amazing', 
                         'brilliant', 'excellent']
        
        has_negative_context = any(word in text_lower for word in negative_context_words)
        has_positive_word = any(word in text_lower for word in positive_words)
        
        if has_negative_context and has_positive_word:
            indicators_found.append({
                'pattern': 'positive_word_negative_context',
                'probability': 0.85,
                'type': 'context_mismatch'
            })
            sarcasm_scores.append(0.85)
        
        # Calculate overall sarcasm probability
        if not sarcasm_scores:
            sarcasm_probability = 0.0
        else:
            # Average of top indicators (weighted)
            sarcasm_probability = sum(sarcasm_scores) / len(sarcasm_scores)
        
        is_sarcastic = sarcasm_probability > 0.60
        
        # Determine tone
        tone = self._determine_tone(text_lower, is_sarcastic)
        
        return {
            'is_sarcastic': is_sarcastic,
            'confidence': sarcasm_probability,
            'indicators': indicators_found,
            'tone': tone,
            'explanation': self._generate_sarcasm_explanation(is_sarcastic, indicators_found)
        }
    
    def _determine_tone(self, text: str, is_sarcastic: bool) -> str:
        """
        Determine overall emotional tone of text
        """
        if is_sarcastic:
            return 'sarcastic'
        
        # Check tone markers
        for tone_name, data in self.tone_markers.items():
            for indicator in data['indicators']:
                if indicator in text:
                    return tone_name
        
        # Default
        return 'neutral'
    
    def _generate_sarcasm_explanation(self, is_sarcastic: bool, 
                                     indicators: List[Dict]) -> str:
        """
        Generate explanation of why text was detected as sarcastic
        """
        if not is_sarcastic:
            return "Text appears sincere."
        
        explanation = "Sarcasm detected because: "
        reasons = []
        
        for indicator in indicators[:3]:  # Top 3 reasons
            if indicator['type'] == 'explicit_phrase':
                reasons.append(f"phrase '{indicator['phrase']}' is commonly sarcastic")
            elif indicator['type'] == 'punctuation':
                reasons.append(f"punctuation pattern indicates sarcasm")
            elif indicator['type'] == 'context_mismatch':
                reasons.append("positive word used in negative context")
        
        explanation += ", ".join(reasons) + "."
        return explanation
    
    # ============================================================================
    # TRANSLATION WITH TONE PRESERVATION
    # ============================================================================
    
    def translate_with_tone(self, text: str, source_lang: str = 'en',
                           target_lang: str = 'es') -> Dict:
        """
        Translate text while preserving sarcastic/emotional tone
        
        Returns:
            - translated_text: Translation with tone preserved
            - tone_detected: What tone was detected
            - sarcasm_markers_added: Markers added to preserve tone
            - notes: Explanation for user
        """
        # Detect sarcasm/tone
        analysis = self.detect_sarcasm(text)
        
        if not analysis['is_sarcastic']:
            return {
                'translated_text': text,  # Will be translated by main engine
                'tone_detected': analysis['tone'],
                'sarcasm_preserved': False,
                'notes': None
            }
        
        # Find sarcastic phrases in text
        sarcastic_phrases_found = []
        for indicator in analysis['indicators']:
            if indicator['type'] == 'explicit_phrase':
                phrase = indicator['phrase']
                if phrase in self.sarcasm_phrases:
                    sarcastic_phrases_found.append({
                        'original': phrase,
                        'data': self.sarcasm_phrases[phrase]
                    })
        
        # Generate translation notes
        notes = "⚠️ **Sarcasm detected**\n\n"
        notes += f"{analysis['explanation']}\n\n"
        notes += "I'll preserve the sarcastic tone in the translation.\n"
        
        if sarcastic_phrases_found:
            notes += "\n**Sarcastic phrases:**\n"
            for phrase_info in sarcastic_phrases_found:
                phrase = phrase_info['original']
                data = phrase_info['data']
                if target_lang in data:
                    notes += f"• '{phrase}' → '{data[target_lang]['sarcastic']}' (maintains sarcasm)\n"
        
        return {
            'original_text': text,
            'tone_detected': 'sarcastic',
            'sarcasm_preserved': True,
            'confidence': analysis['confidence'],
            'sarcastic_phrases': sarcastic_phrases_found,
            'notes': notes,
            'translation_guidance': "Preserve sarcastic tone - use ironic markers if needed"
        }


# ============================================================================
# GLOBAL INSTANCE
# ============================================================================
sarcasm_detector = SarcasmToneDetector()

# Test examples
if __name__ == "__main__":
    print("\n" + "="*60)
    print("SARCASM & TONE DETECTOR - PRESERVES INTENT")
    print("="*60)
    
    # Test 1: Obvious sarcasm
    print("\n**TEST 1: Obvious Sarcasm**")
    text1 = "Oh great, another bill. Just what I needed."
    result1 = sarcasm_detector.detect_sarcasm(text1)
    print(f"Text: {text1}")
    print(f"Sarcastic: {result1['is_sarcastic']}")
    print(f"Confidence: {result1['confidence']:.2f}")
    print(f"Explanation: {result1['explanation']}")
    
    # Test 2: Context-dependent sarcasm
    print("\n**TEST 2: Context-Dependent Sarcasm**")
    text2 = "I lost my job. Fantastic."
    result2 = sarcasm_detector.detect_sarcasm(text2)
    print(f"Text: {text2}")
    print(f"Sarcastic: {result2['is_sarcastic']}")
    print(f"Confidence: {result2['confidence']:.2f}")
    print(f"Explanation: {result2['explanation']}")
    
    # Test 3: Sincere text
    print("\n**TEST 3: Sincere (Not Sarcastic)**")
    text3 = "I got the promotion! Fantastic news!"
    result3 = sarcasm_detector.detect_sarcasm(text3)
    print(f"Text: {text3}")
    print(f"Sarcastic: {result3['is_sarcastic']}")
    print(f"Confidence: {result3['confidence']:.2f}")
    print(f"Tone: {result3['tone']}")
    
    # Test 4: Translation with tone preservation
    print("\n**TEST 4: Translation with Tone Preservation**")
    translation = sarcasm_detector.translate_with_tone(text1, 'en', 'es')
    print(f"Original: {text1}")
    print(f"Tone detected: {translation['tone_detected']}")
    print(f"Sarcasm preserved: {translation['sarcasm_preserved']}")
    print(f"\n{translation['notes']}")
    
    print("\n" + "="*60)
