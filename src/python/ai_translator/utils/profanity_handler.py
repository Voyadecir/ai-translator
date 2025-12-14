"""
Profanity Handler - Intensity-Matched Translation
NEVER waters down curse words - preserves exact emotional intensity
Translates profanity with cultural and intensity awareness

Philosophy: A professional interpreter NEVER censors. They translate tone accurately.
If someone says "This is fucking ridiculous!" → Don't translate as "This is very ridiculous"
Translate as: "¡Esto es jodidamente ridículo!" (same intensity)

Users get CHOICE: Keep intensity or soften it. But default = preserve authenticity.
"""

import re
from typing import Dict, List, Optional, Tuple
from functools import lru_cache

class ProfanityHandler:
    """
    Manages profanity translation with intensity preservation
    
    Key Principles:
    1. NEVER automatically censor or soften
    2. Match intensity level precisely
    3. Provide clean alternatives ONLY when user requests
    4. Preserve emotional context
    5. Warn user about strong language (don't hide it)
    
    Intensity Levels:
    1 = Mild (damn, crap, hell)
    2 = Moderate (shit, ass, bitch)
    3 = Strong (fuck, motherfucker, cunt)
    4 = Extreme (combinations, severe slurs)
    """
    
    def __init__(self):
        # Load profanity databases
        self.profanity = {
            'en': self._load_english_profanity(),
            'es': self._load_spanish_profanity(),
        }
        
        # Detection patterns
        self.profanity_patterns = self._compile_profanity_patterns()
    
    # ============================================================================
    # ENGLISH PROFANITY
    # ============================================================================
    
    def _load_english_profanity(self) -> Dict[str, Dict]:
        """
        English profanity with intensity-matched Spanish equivalents
        """
        return {
            # LEVEL 1: MILD
            "damn": {
                "intensity": 1,
                "category": "exclamation",
                "es": {
                    "intensity_match": "maldición",
                    "alternatives": ["demonios", "carajo (mild)", "rayos"],
                    "clean_version": "demonios",
                    "mexico": "chin",
                    "spain": "joder (mild)",
                    "notes": "Damn is mild in English but translations vary"
                },
                "pt": {
                    "intensity_match": "droga",
                    "alternatives": ["caramba", "raios"],
                    "clean_version": "caramba"
                },
                "examples_en": [
                    "Damn, I forgot my wallet",
                    "Damn it!"
                ],
                "examples_es": [
                    "Maldición, olvidé mi cartera",
                    "¡Chin!"
                ]
            },
            
            "crap": {
                "intensity": 1,
                "category": "exclamation",
                "es": {
                    "intensity_match": "mierda (mild)",
                    "alternatives": ["porquería", "basura"],
                    "clean_version": "porquería",
                    "notes": "Crap is mild, but Spanish 'mierda' can be stronger"
                },
                "pt": {
                    "intensity_match": "porcaria",
                    "alternatives": ["droga", "merda (mild)"],
                    "clean_version": "porcaria"
                },
                "examples_en": [
                    "This is crap",
                    "Oh crap, we're late"
                ],
                "examples_es": [
                    "Esto es una porquería",
                    "Oh mierda, llegamos tarde"
                ]
            },
            
            "hell": {
                "intensity": 1,
                "category": "exclamation",
                "es": {
                    "intensity_match": "demonios",
                    "alternatives": ["infierno", "diablos"],
                    "clean_version": "rayos",
                    "notes": "Often used in phrases like 'what the hell'"
                },
                "pt": {
                    "intensity_match": "inferno",
                    "alternatives": ["diabos"],
                    "clean_version": "caramba"
                },
                "examples_en": [
                    "What the hell?",
                    "Go to hell"
                ],
                "examples_es": [
                    "¿Qué demonios?",
                    "Vete al infierno"
                ]
            },
            
            # LEVEL 2: MODERATE
            "shit": {
                "intensity": 2,
                "category": "exclamation",
                "es": {
                    "intensity_match": "mierda",
                    "alternatives": ["cagada", "porquería"],
                    "clean_version": "porquería",
                    "regional_variants": {
                        "mexico": "mierda",
                        "spain": "mierda",
                        "colombia": "mierda",
                        "argentina": "mierda"
                    },
                    "notes": "Universal across Spanish-speaking countries"
                },
                "pt": {
                    "intensity_match": "merda",
                    "alternatives": ["bosta"],
                    "clean_version": "porcaria"
                },
                "examples_en": [
                    "Oh shit!",
                    "This is shit",
                    "Holy shit"
                ],
                "examples_es": [
                    "¡Oh mierda!",
                    "Esto es una mierda",
                    "¡Santa mierda!"
                ]
            },
            
            "ass": {
                "intensity": 2,
                "category": "body_part",
                "es": {
                    "intensity_match": "culo",
                    "alternatives": ["trasero", "nalgas"],
                    "clean_version": "trasero",
                    "mexico": "culo",
                    "spain": "culo",
                    "notes": "Culo is moderate profanity"
                },
                "pt": {
                    "intensity_match": "cu",
                    "alternatives": ["bunda", "traseiro"],
                    "clean_version": "traseiro"
                },
                "examples_en": [
                    "Kiss my ass",
                    "Get your ass over here",
                    "Pain in the ass"
                ],
                "examples_es": [
                    "Bésame el culo",
                    "Trae tu culo para acá",
                    "Es un dolor en el culo"
                ]
            },
            
           "bitch": {
    "intensity": 2,
    "category": "insult",
    "context_dependent": True,
    "es": {
        "intensity_match": "perra",
        "alternatives": ["zorra", "cabrona"],
        "clean_version": "pesada",
        "mexico": "perra / cabrona",
        "spain": "zorra / puta",
        "notes": "Intensity varies by context - can be playful or severe"
    },
    "pt": {
        "intensity_match": "vadia",
        "alternatives": ["puta", "cachorra"],
        "clean_version": "chata"
    },
    "examples_en": [
        "She's a bitch (mean)",
        "Life's a bitch (expression)",
        "Quit bitching (complaining)"
    ],
    "examples_es": [
        "Es una perra (mean)",
        "La vida es una perra (expression)",
        "Deja de quejarte"
    ]
},
            
            "asshole": {
                "intensity": 2,
                "category": "insult",
                "es": {
                    "intensity_match": "pendejo",
                    "alternatives": ["imbécil", "cabrón", "hijo de puta (stronger)"],
                    "clean_version": "imbécil",
                    "mexico": "pendejo",
                    "spain": "gilipollas",
                    "colombia": "hijueputa",
                    "argentina": "boludo (mild) / pelotudo",
                    "notes": "Gilipollas is very Spanish, pendejo is Mexican"
                },
                "pt": {
                    "intensity_match": "babaca",
                    "alternatives": ["fdp (filho da puta)", "cuzão"],
                    "clean_version": "idiota"
                },
                "examples_en": [
                    "He's an asshole",
                    "Don't be an asshole"
                ],
                "examples_es": [
                    "Es un pendejo",
                    "No seas pendejo"
                ]
            },
            
            # LEVEL 3: STRONG
            "fuck": {
                "intensity": 3,
                "category": "strong_profanity",
                "es": {
                    "intensity_match": "joder / chingar",
                    "alternatives": ["follar (literal sex)", "coger (Mexico)", "verga"],
                    "clean_version": "fastidiar",
                    "regional_variants": {
                        "mexico": "chingar",
                        "spain": "joder",
                        "colombia": "follar / joder",
                        "argentina": "coger / joder"
                    },
                    "notes": "Chingar is very Mexican. Joder is Spanish. Coger in Argentina = fuck, elsewhere = to grab"
                },
                "pt": {
                    "intensity_match": "foder",
                    "alternatives": ["fudeu", "ferrou"],
                    "clean_version": "estragar"
                },
                "examples_en": [
                    "Fuck!",
                    "Fuck this",
                    "What the fuck?",
                    "Fuck off"
                ],
                "examples_es": [
                    "¡Chingados! (Mexico) / ¡Joder! (Spain)",
                    "A la verga esto (Mexico) / Que se joda esto (Spain)",
                    "¿Qué chingados? (Mexico) / ¿Qué coño? (Spain)",
                    "Vete a la verga (Mexico) / Vete a la mierda (Universal)"
                ]
            },
            
            "fucking": {
                "intensity": 3,
                "category": "intensifier",
                "es": {
                    "intensity_match": "puto / pinche / jodido",
                    "alternatives": ["maldito"],
                    "clean_version": "maldito",
                    "mexico": "pinche / puto",
                    "spain": "puto / jodido",
                    "notes": "Used as intensifier: 'fucking car' = 'pinche carro' (Mexico)"
                },
                "pt": {
                    "intensity_match": "porra / merda de",
                    "alternatives": ["maldito"],
                    "clean_version": "maldito"
                },
                "examples_en": [
                    "This fucking car",
                    "That's fucking amazing",
                    "Fucking hell"
                ],
                "examples_es": [
                    "Este pinche carro (Mexico)",
                    "Eso está de puta madre (Spain - positive!)",
                    "¡Puta madre! (exclamation)"
                ]
            },
            
            "motherfucker": {
                "intensity": 3,
                "category": "strong_insult",
                "es": {
                    "intensity_match": "hijo de puta",
                    "alternatives": ["hijueputa", "malparido"],
                    "clean_version": "desgraciado",
                    "mexico": "hijo de puta / hijo de tu pinche madre",
                    "spain": "hijo de puta",
                    "colombia": "hijueputa / malparido",
                    "notes": "Hijo de puta is universal, hijueputa is Colombian"
                },
                "pt": {
                    "intensity_match": "filho da puta",
                    "alternatives": ["fdp", "desgraçado"],
                    "clean_version": "desgraçado"
                },
                "examples_en": [
                    "That motherfucker",
                    "You motherfucker"
                ],
                "examples_es": [
                    "Ese hijo de puta",
                    "Tú, hijo de puta"
                ]
            },
            
            "bastard": {
                "intensity": 2,
                "category": "insult",
                "es": {
                    "intensity_match": "cabrón",
                    "alternatives": ["hijo de puta", "bastardo"],
                    "clean_version": "desgraciado",
                    "mexico": "cabrón",
                    "spain": "cabrón / hijoputa",
                    "notes": "Cabrón can be friendly or hostile depending on tone"
                },
                "pt": {
                    "intensity_match": "bastardo",
                    "alternatives": ["sacana", "desgraçado"],
                    "clean_version": "safado"
                },
                "examples_en": [
                    "You bastard!",
                    "That lucky bastard"
                ],
                "examples_es": [
                    "¡Cabrón!",
                    "Ese cabrón afortunado"
                ]
            },
            
            # LEVEL 4: EXTREME (combinations)
            "piece of shit": {
                "intensity": 3,
                "category": "strong_insult",
                "es": {
                    "intensity_match": "pedazo de mierda",
                    "alternatives": ["basura", "porquería"],
                    "clean_version": "basura",
                    "notes": "Direct translation works and maintains intensity"
                },
                "pt": {
                    "intensity_match": "pedaço de merda",
                    "alternatives": ["lixo"],
                    "clean_version": "lixo"
                },
                "examples_en": [
                    "This car is a piece of shit",
                    "You piece of shit"
                ],
                "examples_es": [
                    "Este carro es un pedazo de mierda",
                    "Pedazo de mierda"
                ]
            },
            
            "son of a bitch": {
                "intensity": 3,
                "category": "strong_insult",
                "es": {
                    "intensity_match": "hijo de puta",
                    "alternatives": ["hijo de perra"],
                    "clean_version": "desgraciado",
                    "notes": "Same as motherfucker in Spanish"
                },
                "pt": {
                    "intensity_match": "filho da puta",
                    "alternatives": ["fdp"],
                    "clean_version": "miserável"
                },
                "examples_en": [
                    "That son of a bitch!",
                    "You son of a bitch"
                ],
                "examples_es": [
                    "¡Ese hijo de puta!",
                    "Hijo de puta"
                ]
            },
            
            # SPECIALTY PHRASES
            "what the fuck": {
                "intensity": 3,
                "category": "exclamation",
                "es": {
                    "intensity_match": "¿qué verga? / ¿qué chingados? / ¿qué coño?",
                    "clean_version": "¿qué demonios?",
                    "mexico": "¿Qué chingados?",
                    "spain": "¿Qué coño?",
                    "colombia": "¿Qué carajo?",
                    "argentina": "¿Qué mierda?",
                    "notes": "Regional variations common"
                },
                "pt": {
                    "intensity_match": "que porra?",
                    "clean_version": "que diabos?"
                },
                "examples_en": [
                    "What the fuck is this?",
                    "What the fuck are you doing?"
                ],
                "examples_es": [
                    "¿Qué chingados es esto? (Mexico)",
                    "¿Qué coño estás haciendo? (Spain)"
                ]
            },
            
            "holy shit": {
                "intensity": 2,
                "category": "exclamation",
                "es": {
                    "intensity_match": "santa mierda",
                    "alternatives": ["madre mía", "hostia (Spain)"],
                    "clean_version": "cielos",
                    "spain": "¡Hostia!",
                    "notes": "Hostia is very Spanish (literally 'communion wafer')"
                },
                "pt": {
                    "intensity_match": "puta merda",
                    "clean_version": "nossa"
                },
                "examples_en": [
                    "Holy shit, that's crazy!",
                    "Holy shit!"
                ],
                "examples_es": [
                    "¡Santa mierda, eso está loco!",
                    "¡Hostia! (Spain)"
                ]
            },
            
            # Add 100+ more profanity terms...
        }
    
    # ============================================================================
    # SPANISH PROFANITY
    # ============================================================================
    
    def _load_spanish_profanity(self) -> Dict[str, Dict]:
        """
        Spanish profanity with English intensity matches
        """
        return {
            "chingar": {
                "intensity": 3,
                "region": "mexico",
                "category": "strong_profanity",
                "en": {
                    "intensity_match": "fuck",
                    "clean_version": "mess with",
                    "notes": "Very Mexican, extremely versatile verb"
                },
                "examples_es": [
                    "¡Chinga tu madre!",
                    "Me chingaron",
                    "¡Vete a la chingada!"
                ],
                "examples_en": [
                    "Fuck your mother!",
                    "They fucked me over",
                    "Go fuck yourself!"
                ]
            },
            
            "joder": {
                "intensity": 3,
                "region": "spain",
                "category": "strong_profanity",
                "en": {
                    "intensity_match": "fuck",
                    "clean_version": "damn",
                    "notes": "Very Spanish, universal exclamation"
                },
                "examples_es": [
                    "¡Joder!",
                    "No me jodas",
                    "Qué jodido"
                ],
                "examples_en": [
                    "Fuck!",
                    "Don't fuck with me",
                    "How fucked up"
                ]
            },
            
            "coño": {
                "intensity": 3,
                "region": "spain",
                "category": "strong_profanity",
                "en": {
                    "intensity_match": "fuck / cunt",
                    "clean_version": "damn",
                    "notes": "Spanish exclamation, vulgar origin but common usage"
                },
                "examples_es": [
                    "¡Coño!",
                    "¿Qué coño?",
                    "Me importa un coño"
                ],
                "examples_en": [
                    "Fuck!",
                    "What the fuck?",
                    "I don't give a fuck"
                ]
            },
            
            "verga": {
                "intensity": 3,
                "region": "mexico",
                "category": "strong_profanity",
                "en": {
                    "intensity_match": "fuck / dick",
                    "clean_version": "damn",
                    "notes": "Mexican, very common exclamation"
                },
                "examples_es": [
                    "¡A la verga!",
                    "Me vale verga",
                    "¿Qué verga?"
                ],
                "examples_en": [
                    "Fuck it!",
                    "I don't give a fuck",
                    "What the fuck?"
                ]
            },
            
            "mierda": {
                "intensity": 2,
                "region": "universal",
                "category": "exclamation",
                "en": {
                    "intensity_match": "shit",
                    "clean_version": "crap",
                    "notes": "Universal across all Spanish"
                },
                "examples_es": [
                    "¡Mierda!",
                    "Esto es una mierda",
                    "¡Qué mierda!"
                ],
                "examples_en": [
                    "Shit!",
                    "This is shit",
                    "What shit!"
                ]
            },
            
            "hijo de puta": {
                "intensity": 3,
                "region": "universal",
                "category": "strong_insult",
                "en": {
                    "intensity_match": "son of a bitch / motherfucker",
                    "clean_version": "jerk",
                    "notes": "Universal, very strong insult"
                },
                "examples_es": [
                    "Ese hijo de puta",
                    "¡Hijo de puta!"
                ],
                "examples_en": [
                    "That son of a bitch",
                    "Motherfucker!"
                ]
            },
            
            "pendejo": {
                "intensity": 2,
                "region": "mexico",
                "category": "insult",
                "en": {
                    "intensity_match": "asshole / idiot",
                    "clean_version": "dummy",
                    "notes": "Very Mexican, common insult"
                },
                "examples_es": [
                    "No seas pendejo",
                    "Eres un pendejo"
                ],
                "examples_en": [
                    "Don't be an asshole",
                    "You're an asshole"
                ]
            },
            
            "cabrón": {
                "intensity": 2,
                "region": "mexico_spain",
                "category": "insult",
                "context_dependent": True,
                "en": {
                    "intensity_match": "bastard / asshole (can be friendly)",
                    "clean_version": "guy",
                    "notes": "Can be affectionate or insulting based on tone"
                },
                "examples_es": [
                    "¡Qué pasa, cabrón!",
                    "Eres un cabrón"
                ],
                "examples_en": [
                    "What's up, buddy!",
                    "You're a bastard"
                ]
            },
            
            # Add 100+ more Spanish profanity...
        }
    
    # ============================================================================
    # DETECTION & TRANSLATION
    # ============================================================================
    
    def _compile_profanity_patterns(self) -> Dict[str, List]:
        """Compile regex patterns for profanity detection"""
        patterns = {}
        
        for lang, terms in self.profanity.items():
            patterns[lang] = []
            for term in terms.keys():
                # Create flexible pattern
                pattern = re.compile(r'\b' + re.escape(term) + r'\w*\b', re.IGNORECASE)
                patterns[lang].append((term, pattern))
        
        return patterns
    
    def detect_profanity(self, text: str, source_lang: str = 'en') -> List[Dict]:
        """
        Detect profanity in text
        
        Returns list with profanity found, intensity, and positions
        """
        detected = []
        
        if source_lang not in self.profanity_patterns:
            return detected
        
        for term, pattern in self.profanity_patterns[source_lang]:
            matches = pattern.finditer(text)
            for match in matches:
                detected.append({
                    'term': term,
                    'matched_text': match.group(),
                    'position': match.start(),
                    'intensity': self.profanity[source_lang][term]['intensity'],
                    'data': self.profanity[source_lang][term]
                })
        
        return detected
    
    def translate_profanity(self, term: str, source_lang: str = 'en',
                           target_lang: str = 'es', preserve_intensity: bool = True,
                           region: str = None) -> Optional[Dict]:
        """
        Translate profanity with intensity matching
        
        Args:
            term: The profane word/phrase
            source_lang: Source language
            target_lang: Target language
            preserve_intensity: If True, match intensity. If False, use clean version
            region: Preferred region (e.g., 'mexico', 'spain')
        
        Returns:
            Translation with intensity match or clean alternative
        """
        term_lower = term.lower().strip()
        
        if source_lang not in self.profanity:
            return None
        
        if term_lower not in self.profanity[source_lang]:
            return None
        
        profanity_data = self.profanity[source_lang][term_lower]
        
        if target_lang not in profanity_data:
            return None
        
        target_data = profanity_data[target_lang]
        
        # Choose translation based on preserve_intensity flag
        if preserve_intensity:
            # Check for regional variant first
            if region and region in target_data.get('regional_variants', {}):
                translation = target_data['regional_variants'][region]
            elif region and region in target_data:
                translation = target_data[region]
            else:
                translation = target_data['intensity_match']
        else:
            translation = target_data['clean_version']
        
        return {
            'original': term,
            'translation': translation,
            'intensity': profanity_data['intensity'],
            'category': profanity_data['category'],
            'preserved_intensity': preserve_intensity,
            'alternatives': target_data.get('alternatives', []),
            'clean_version': target_data['clean_version'],
            'regional_notes': target_data.get('notes', ''),
            'examples_source': profanity_data.get(f'examples_{source_lang}', []),
            'examples_target': profanity_data.get(f'examples_{target_lang}', [])
        }
    
    def generate_profanity_warning(self, detected_profanity: List[Dict],
                                  target_lang: str = 'es') -> str:
        """
        Generate user warning about profanity in text
        
        Used by chatbot to inform user about strong language
        """
        if not detected_profanity:
            return None
        
        max_intensity = max(p['intensity'] for p in detected_profanity)
        
        if max_intensity == 1:
            warning = "⚠️ **Mild language detected**\n\n"
        elif max_intensity == 2:
            warning = "⚠️ **Moderate profanity detected**\n\n"
        else:
            warning = "🔞 **STRONG PROFANITY DETECTED**\n\n"
        
        warning += f"This text contains {len(detected_profanity)} profane word(s).\n\n"
        warning += "**Translation options:**\n"
        warning += "1. ✅ **Preserve intensity** (recommended) - Translate with same emotional impact\n"
        warning += "2. ☀️ **Clean version** - Use family-friendly alternatives\n\n"
        warning += "I'll preserve the tone by default (option 1), but you can ask for the clean version.\n\n"
        warning += "**Detected terms:**\n"
        
        for p in detected_profanity[:5]:  # Show first 5
            warning += f"• `{p['matched_text']}` (intensity: {p['intensity']}/3)\n"
        
        if len(detected_profanity) > 5:
            warning += f"• ...and {len(detected_profanity) - 5} more\n"
        
        return warning
    
    def translate_text_with_profanity(self, text: str, source_lang: str = 'en',
                                     target_lang: str = 'es',
                                     preserve_intensity: bool = True,
                                     region: str = None) -> Dict:
        """
        Translate entire text, handling profanity appropriately
        
        Returns:
            - translated_text: Full translation
            - profanity_detected: List of profane words found
            - intensity_preserved: Whether intensity was preserved
            - warning: User warning about content
        """
        detected = self.detect_profanity(text, source_lang)
        
        if not detected:
            return {
                'text': text,
                'profanity_detected': [],
                'contains_profanity': False,
                'warning': None
            }
        
        # Sort by position (reverse) for replacement
        detected.sort(key=lambda x: x['position'], reverse=True)
        
        translated_text = text
        replacements = []
        
        for prof in detected:
            translation = self.translate_profanity(
                prof['term'],
                source_lang,
                target_lang,
                preserve_intensity,
                region
            )
            
            if translation:
                # Replace in text
                start = prof['position']
                end = start + len(prof['matched_text'])
                translated_text = translated_text[:start] + translation['translation'] + translated_text[end:]
                
                replacements.append({
                    'original': prof['matched_text'],
                    'translation': translation['translation'],
                    'intensity': translation['intensity'],
                    'position': start
                })
        
        return {
            'translated_text': translated_text,
            'profanity_detected': [p['matched_text'] for p in detected],
            'contains_profanity': True,
            'intensity_preserved': preserve_intensity,
            'replacements': replacements,
            'warning': self.generate_profanity_warning(detected, target_lang),
            'max_intensity': max(p['intensity'] for p in detected)
        }


# ============================================================================
# GLOBAL INSTANCE
# ============================================================================
profanity_handler = ProfanityHandler()

# Test examples
if __name__ == "__main__":
    print("\n" + "="*60)
    print("PROFANITY HANDLER - INTENSITY-MATCHED TRANSLATION")
    print("="*60)
    
    # Test 1: Detect profanity
    print("\n**TEST 1: Profanity Detection**")
    text = "This fucking car is a piece of shit!"
    detected = profanity_handler.detect_profanity(text, 'en')
    print(f"Text: {text}")
    print(f"Profanity detected: {[d['matched_text'] for d in detected]}")
    print(f"Intensities: {[d['intensity'] for d in detected]}")
    
    # Test 2: Translate with intensity preserved
    print("\n**TEST 2: Intensity-Preserved Translation**")
    translation = profanity_handler.translate_profanity("fuck", 'en', 'es', 
                                                        preserve_intensity=True, 
                                                        region='mexico')
    print(f"Original: {translation['original']}")
    print(f"Translation (Mexico): {translation['translation']}")
    print(f"Intensity: {translation['intensity']}/3")
    
    # Test 3: Clean version
    print("\n**TEST 3: Clean Version Translation**")
    translation_clean = profanity_handler.translate_profanity("fuck", 'en', 'es', 
                                                              preserve_intensity=False)
    print(f"Original: fuck")
    print(f"Clean version: {translation_clean['translation']}")
    
    # Test 4: Full text translation
    print("\n**TEST 4: Full Text Translation**")
    result = profanity_handler.translate_text_with_profanity(text, 'en', 'es', 
                                                             preserve_intensity=True,
                                                             region='mexico')
    print(f"Original: {text}")
    print(f"Translated: {result['translated_text']}")
    print(f"Max intensity: {result['max_intensity']}/3")
    
    # Test 5: Warning message
    print("\n**TEST 5: User Warning**")
    print(result['warning'])
    
    print("\n" + "="*60)
