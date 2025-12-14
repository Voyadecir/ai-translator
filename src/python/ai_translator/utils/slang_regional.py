"""
Regional Slang Database - Colloquial Language Handler
Translates slang and colloquialisms with regional awareness
Never waters down tone - preserves authenticity

Example:
"What's up, bro?" 
→ Mexico: "¿Qué onda, carnal?"
→ Spain: "¿Qué pasa, tío?"
→ Colombia: "¿Qué más, parcero?"
"""

import re
from typing import Dict, List, Optional, Tuple
from functools import lru_cache

class RegionalSlang:
    """
    Manages slang and colloquial expressions across regions
    
    Key Features:
    - Regional variations (Mexico, Spain, Colombia, Argentina, etc.)
    - Preserves tone intensity (never sanitizes)
    - Age-appropriate variants when needed
    - Street language authenticity
    - Cultural context awareness
    """
    
    def __init__(self):
        # Load slang databases by language and region
        self.slang = {
            'en': self._load_english_slang(),
            'es': self._load_spanish_slang(),
        }
        
        # Regional preferences (can be set by user)
        self.regional_preferences = {}
    
    # ============================================================================
    # ENGLISH SLANG
    # ============================================================================
    
    def _load_english_slang(self) -> Dict[str, Dict]:
        """
        English slang with regional Spanish equivalents
        """
        return {
            # GREETINGS & SOCIAL
            "what's up": {
                "formality": "very_informal",
                "intensity": "casual",
                "es": {
                    "mexico": {
                        "options": ["¿Qué onda?", "¿Qué pasó?", "¿Qué tranza?"],
                        "most_common": "¿Qué onda?",
                        "notes": "Qué onda is universal in Mexico"
                    },
                    "spain": {
                        "options": ["¿Qué pasa?", "¿Qué tal?", "¿Qué hay?"],
                        "most_common": "¿Qué pasa?",
                        "notes": "Qué tal is more neutral"
                    },
                    "colombia": {
                        "options": ["¿Qué más?", "¿Quihubo?", "¿Qué hubo?"],
                        "most_common": "¿Qué más?",
                        "notes": "Qué más is very casual"
                    },
                    "argentina": {
                        "options": ["¿Qué hacés?", "¿Todo bien?", "¿Cómo andás?"],
                        "most_common": "¿Qué hacés?",
                        "notes": "Use vos form in Argentina"
                    },
                    "chile": {
                        "options": ["¿Qué onda?", "¿Cómo estái?"],
                        "most_common": "¿Qué onda?",
                        "notes": "Chilean Spanish drops final 's'"
                    }
                },
                "examples_en": [
                    "What's up, man?",
                    "Hey, what's up?"
                ],
                "examples_es_mexico": [
                    "¿Qué onda, wey?",
                    "Oye, ¿qué onda?"
                ]
            },
            
            "bro / brother": {
                "formality": "very_informal",
                "intensity": "casual",
                "es": {
                    "mexico": {
                        "options": ["carnal", "cuate", "wey/güey", "compa"],
                        "most_common": "wey",
                        "notes": "Wey is extremely common among young people. Carnal is more affectionate."
                    },
                    "spain": {
                        "options": ["tío", "colega", "macho"],
                        "most_common": "tío",
                        "notes": "Tío literally means 'uncle' but used like 'dude'"
                    },
                    "colombia": {
                        "options": ["parcero", "parce", "hermano", "compa"],
                        "most_common": "parcero",
                        "notes": "Parcero/parce is distinctly Colombian"
                    },
                    "argentina": {
                        "options": ["che", "boludo", "hermano"],
                        "most_common": "boludo",
                        "notes": "Boludo can be affectionate or insulting depending on tone"
                    },
                    "puerto_rico": {
                        "options": ["bro", "pana", "mano"],
                        "most_common": "bro",
                        "notes": "Puerto Rico often keeps English 'bro'"
                    },
                    "central_america": {
                        "options": ["maje", "mano", "compa"],
                        "most_common": "mano",
                        "notes": "Mano is short for hermano"
                    }
                },
                "examples_en": [
                    "Thanks, bro!",
                    "What's wrong, brother?"
                ],
                "examples_es_mexico": [
                    "¡Gracias, carnal!",
                    "¿Qué pasa, wey?"
                ]
            },
            
            "cool / awesome": {
                "formality": "informal",
                "intensity": "positive",
                "es": {
                    "mexico": {
                        "options": ["chido", "padre", "genial", "chingón"],
                        "most_common": "chido",
                        "notes": "Chingón is stronger/vulgar. Padre is family-friendly."
                    },
                    "spain": {
                        "options": ["guay", "genial", "mola", "chulo"],
                        "most_common": "guay",
                        "notes": "Mola means 'it rocks'"
                    },
                    "colombia": {
                        "options": ["chévere", "bacano", "chimba"],
                        "most_common": "chévere",
                        "notes": "Chimba is very informal"
                    },
                    "argentina": {
                        "options": ["copado", "piola", "groso"],
                        "most_common": "copado",
                        "notes": "Groso means 'great'"
                    },
                    "chile": {
                        "options": ["bacán", "la raja", "filete"],
                        "most_common": "bacán",
                        "notes": "La raja is very casual"
                    },
                    "peru": {
                        "options": ["bacán", "chévere", "joya"],
                        "most_common": "chévere",
                        "notes": "Joya means 'jewel' = great"
                    }
                },
                "examples_en": [
                    "That's so cool!",
                    "Your car is awesome"
                ],
                "examples_es_mexico": [
                    "¡Qué chido!",
                    "Tu carro está bien chingón"
                ]
            },
            
            "dude / man": {
                "formality": "very_informal",
                "intensity": "casual",
                "es": {
                    "mexico": {
                        "options": ["wey", "güey", "compa", "carnal"],
                        "most_common": "wey",
                        "notes": "Universal in Mexican Spanish"
                    },
                    "spain": {
                        "options": ["tío", "tía (f)", "macho"],
                        "most_common": "tío",
                        "notes": "Tía for women"
                    },
                    "colombia": {
                        "options": ["man", "viejo", "parcero"],
                        "most_common": "man",
                        "notes": "Colombia often uses English 'man'"
                    },
                    "argentina": {
                        "options": ["che", "boludo", "loco"],
                        "most_common": "che",
                        "notes": "Che is iconic Argentinian"
                    }
                },
                "examples_en": [
                    "Dude, that's crazy!",
                    "Hey man, calm down"
                ],
                "examples_es_mexico": [
                    "¡Wey, eso está loco!",
                    "Oye wey, cálmate"
                ]
            },
            
            # EMOTIONAL EXPRESSIONS
            "damn / shit": {
                "formality": "informal",
                "intensity": "moderate_profanity",
                "es": {
                    "mexico": {
                        "options": ["chingados", "chin", "carajo", "verga"],
                        "most_common": "chin",
                        "notes": "Chin is softened version of chingados"
                    },
                    "spain": {
                        "options": ["joder", "coño", "mierda", "ostras"],
                        "most_common": "joder",
                        "notes": "Ostras is polite version"
                    },
                    "colombia": {
                        "options": ["mierda", "gonorrea", "jueputa"],
                        "most_common": "mierda",
                        "notes": "Gonorrea is very Colombian"
                    },
                    "argentina": {
                        "options": ["la concha", "mierda", "puta"],
                        "most_common": "la concha",
                        "notes": "Short for 'la concha de tu madre'"
                    }
                },
                "examples_en": [
                    "Damn, I forgot my keys!",
                    "Oh shit, we're late"
                ],
                "examples_es_mexico": [
                    "¡Chin, olvidé mis llaves!",
                    "¡Verga, llegamos tarde!"
                ]
            },
            
            "no way / for real": {
                "formality": "informal",
                "intensity": "surprise",
                "es": {
                    "mexico": {
                        "options": ["no manches", "a poco", "en serio", "neta"],
                        "most_common": "no manches",
                        "notes": "No manches is very Mexican. Neta means 'truth'"
                    },
                    "spain": {
                        "options": ["no me jodas", "en serio", "de verdad"],
                        "most_common": "en serio",
                        "notes": "No me jodas is vulgar but common"
                    },
                    "colombia": {
                        "options": ["¿en serio?", "¿de verdad?", "¿si?"],
                        "most_common": "¿en serio?",
                        "notes": "Colombia uses '¿si?' for confirmation"
                    },
                    "argentina": {
                        "options": ["¿en serio?", "¿posta?", "¿mal?"],
                        "most_common": "¿posta?",
                        "notes": "Posta is distinctly Argentinian"
                    }
                },
                "examples_en": [
                    "No way! You got the job?",
                    "For real? That's amazing!"
                ],
                "examples_es_mexico": [
                    "¡No manches! ¿Conseguiste el trabajo?",
                    "¿Neta? ¡Qué padre!"
                ]
            },
            
            # DESCRIBING PEOPLE
            "hot / attractive": {
                "formality": "informal",
                "intensity": "casual",
                "es": {
                    "mexico": {
                        "options": ["guapo/a", "bueno/a", "mamacita/papacito"],
                        "most_common": "guapo/a",
                        "notes": "Mamacita/papacito is objectifying"
                    },
                    "spain": {
                        "options": ["bueno/a", "macizo/a", "cañón"],
                        "most_common": "bueno/a",
                        "notes": "Está cañón = very hot"
                    },
                    "colombia": {
                        "options": ["bueno/a", "Rico/a", "divino/a"],
                        "most_common": "divino/a",
                        "notes": "Divino/a is common in Colombia"
                    },
                    "argentina": {
                        "options": ["lindo/a", "fachero/a", "zarpado/a"],
                        "most_common": "fachero/a",
                        "notes": "Zarpado means 'extreme'"
                    }
                },
                "examples_en": [
                    "She's really hot",
                    "That guy is attractive"
                ],
                "examples_es_mexico": [
                    "Está bien guapa",
                    "Ese wey está bueno"
                ]
            },
            
            "crazy / insane": {
                "formality": "informal",
                "intensity": "casual",
                "es": {
                    "mexico": {
                        "options": ["loco", "está de la verga", "está dlv"],
                        "most_common": "loco",
                        "notes": "De la verga is vulgar"
                    },
                    "spain": {
                        "options": ["loco", "flipado", "alucinante"],
                        "most_common": "flipado",
                        "notes": "Flipar = to flip out"
                    },
                    "colombia": {
                        "options": ["loco", "chimba", "una locura"],
                        "most_common": "loco",
                        "notes": "Chimba can mean crazy in context"
                    },
                    "argentina": {
                        "options": ["loco", "zarpado", "un delirio"],
                        "most_common": "zarpado",
                        "notes": "Zarpado = extreme/crazy"
                    }
                },
                "examples_en": [
                    "That party was crazy!",
                    "You're insane, man"
                ],
                "examples_es_mexico": [
                    "¡Esa fiesta estuvo loca!",
                    "Estás bien loco, wey"
                ]
            },
            
            # MONEY
            "broke / no money": {
                "formality": "informal",
                "intensity": "casual",
                "es": {
                    "mexico": {
                        "options": ["sin lana", "quebrado", "sin varo"],
                        "most_common": "sin lana",
                        "notes": "Lana = money in Mexico"
                    },
                    "spain": {
                        "options": ["sin pasta", "pelado", "sin blanca"],
                        "most_common": "sin pasta",
                        "notes": "Pasta = money in Spain"
                    },
                    "colombia": {
                        "options": ["sin plata", "quebrado", "arrancado"],
                        "most_common": "sin plata",
                        "notes": "Plata is standard in Colombia"
                    },
                    "argentina": {
                        "options": ["sin guita", "seco", "fundido"],
                        "most_common": "sin guita",
                        "notes": "Guita = money in Argentina"
                    }
                },
                "examples_en": [
                    "I'm broke until payday",
                    "Can't go out, I'm broke"
                ],
                "examples_es_mexico": [
                    "Estoy sin lana hasta que me paguen",
                    "No puedo salir, estoy quebrado"
                ]
            },
            
            "money / cash": {
                "formality": "informal",
                "intensity": "casual",
                "es": {
                    "mexico": {
                        "options": ["lana", "varo", "feria", "billetes"],
                        "most_common": "lana",
                        "notes": "Feria also means change"
                    },
                    "spain": {
                        "options": ["pasta", "pelas", "guita", "plata"],
                        "most_common": "pasta",
                        "notes": "Pelas is older slang"
                    },
                    "colombia": {
                        "options": ["plata", "billete", "mosca"],
                        "most_common": "plata",
                        "notes": "Standard across Colombia"
                    },
                    "argentina": {
                        "options": ["guita", "mango", "plata"],
                        "most_common": "guita",
                        "notes": "Mango = one peso"
                    }
                },
                "examples_en": [
                    "I need money for the bus",
                    "Do you have cash?"
                ],
                "examples_es_mexico": [
                    "Necesito lana para el camión",
                    "¿Tienes varo?"
                ]
            },
            
            # NEGATIVE EXPRESSIONS
            "sucks / terrible": {
                "formality": "informal",
                "intensity": "negative",
                "es": {
                    "mexico": {
                        "options": ["está de la verga", "está dlv", "apesta", "está gacho"],
                        "most_common": "está gacho",
                        "notes": "Gacho is milder than verga"
                    },
                    "spain": {
                        "options": ["es una mierda", "apesta", "es una basura"],
                        "most_common": "es una mierda",
                        "notes": "Direct and common"
                    },
                    "colombia": {
                        "options": ["es una mierda", "está maluco", "qué gonorrea"],
                        "most_common": "está maluco",
                        "notes": "Maluco = bad/sick"
                    },
                    "argentina": {
                        "options": ["es una mierda", "es una verga", "está para el orto"],
                        "most_common": "es una mierda",
                        "notes": "Para el orto is vulgar"
                    }
                },
                "examples_en": [
                    "This movie sucks",
                    "The weather is terrible"
                ],
                "examples_es_mexico": [
                    "Esta película está gacha",
                    "El clima está de la verga"
                ]
            },
            
            # POLICE & AUTHORITY
            "cops / police": {
                "formality": "informal",
                "intensity": "casual",
                "es": {
                    "mexico": {
                        "options": ["la tira", "los polis", "la chota", "los azules"],
                        "most_common": "los polis",
                        "notes": "La tira is street slang"
                    },
                    "spain": {
                        "options": ["la poli", "la pasma", "los maderos"],
                        "most_common": "la poli",
                        "notes": "Maderos is more derogatory"
                    },
                    "colombia": {
                        "options": ["los tombos", "la ley", "los polis"],
                        "most_common": "los tombos",
                        "notes": "Tombos is very Colombian"
                    },
                    "argentina": {
                        "options": ["la cana", "los canas", "la yuta"],
                        "most_common": "la cana",
                        "notes": "Yuta is very informal"
                    }
                },
                "examples_en": [
                    "The cops are coming!",
                    "Watch out for police"
                ],
                "examples_es_mexico": [
                    "¡Viene la tira!",
                    "Aguas con los polis"
                ]
            },
            
            # Add 500+ more slang terms...
        }
    
    # ============================================================================
    # SPANISH SLANG
    # ============================================================================
    
    def _load_spanish_slang(self) -> Dict[str, Dict]:
        """
        Spanish slang with English equivalents
        """
        return {
            # MEXICAN SLANG
            "güey/wey": {
                "region": "mexico",
                "formality": "very_informal",
                "en": {
                    "translation": "dude, bro, man",
                    "notes": "Extremely common in Mexico among all ages"
                },
                "examples_es": [
                    "¿Qué onda, wey?",
                    "No manches, wey"
                ],
                "examples_en": [
                    "What's up, dude?",
                    "No way, man"
                ]
            },
            
            "chido": {
                "region": "mexico",
                "formality": "informal",
                "en": {
                    "translation": "cool, awesome, great",
                    "notes": "Very Mexican, not used elsewhere"
                },
                "examples_es": [
                    "Está bien chido",
                    "Qué chido tu carro"
                ],
                "examples_en": [
                    "That's really cool",
                    "Your car is awesome"
                ]
            },
            
            "no manches": {
                "region": "mexico",
                "formality": "informal",
                "en": {
                    "translation": "no way, are you serious, wow",
                    "notes": "Euphemism for 'no mames' (vulgar)"
                },
                "examples_es": [
                    "¡No manches! ¿En serio?",
                    "No manches, qué padre"
                ],
                "examples_en": [
                    "No way! Really?",
                    "Wow, that's cool"
                ]
            },
            
            # SPANISH (SPAIN) SLANG
            "tío/tía": {
                "region": "spain",
                "formality": "very_informal",
                "en": {
                    "translation": "dude, guy, girl",
                    "notes": "Literally 'uncle/aunt' but used like 'dude'"
                },
                "examples_es": [
                    "¿Qué pasa, tío?",
                    "Esa tía es guay"
                ],
                "examples_en": [
                    "What's up, dude?",
                    "That girl is cool"
                ]
            },
            
            "guay": {
                "region": "spain",
                "formality": "informal",
                "en": {
                    "translation": "cool, great, awesome",
                    "notes": "Very Spanish, not used in Latin America"
                },
                "examples_es": [
                    "¡Qué guay!",
                    "Está muy guay"
                ],
                "examples_en": [
                    "How cool!",
                    "That's really cool"
                ]
            },
            
            "mola": {
                "region": "spain",
                "formality": "informal",
                "en": {
                    "translation": "it rocks, it's cool, I like it",
                    "notes": "From verb 'molar' = to be cool"
                },
                "examples_es": [
                    "Me mola tu estilo",
                    "Esa música mola"
                ],
                "examples_en": [
                    "I like your style",
                    "That music rocks"
                ]
            },
            
            # COLOMBIAN SLANG
            "parcero/parce": {
                "region": "colombia",
                "formality": "very_informal",
                "en": {
                    "translation": "buddy, pal, friend",
                    "notes": "Distinctly Colombian"
                },
                "examples_es": [
                    "¿Qué más, parcero?",
                    "Gracias, parce"
                ],
                "examples_en": [
                    "What's up, buddy?",
                    "Thanks, pal"
                ]
            },
            
            "chévere": {
                "region": "colombia",
                "formality": "informal",
                "en": {
                    "translation": "cool, great, nice",
                    "notes": "Common in Caribbean and Colombia"
                },
                "examples_es": [
                    "Qué chévere",
                    "Eso está chévere"
                ],
                "examples_en": [
                    "How cool",
                    "That's great"
                ]
            },
            
            # ARGENTINIAN SLANG
            "che": {
                "region": "argentina",
                "formality": "very_informal",
                "en": {
                    "translation": "hey, dude, man",
                    "notes": "Iconic Argentinian, like Che Guevara"
                },
                "examples_es": [
                    "¡Che, boludo!",
                    "Che, mirá esto"
                ],
                "examples_en": [
                    "Hey, dude!",
                    "Hey, look at this"
                ]
            },
            
            "boludo": {
                "region": "argentina",
                "formality": "very_informal",
                "en": {
                    "translation": "dude, idiot (affectionate or insulting)",
                    "notes": "Context determines if friendly or hostile"
                },
                "examples_es": [
                    "¿Qué hacés, boludo?",
                    "No seas boludo"
                ],
                "examples_en": [
                    "What's up, dude?",
                    "Don't be an idiot"
                ]
            },
            
            # Add 300+ more regional slang terms...
        }
    
    # ============================================================================
    # TRANSLATION METHODS
    # ============================================================================
    
    def translate_slang(self, slang_term: str, source_lang: str = 'en',
                       target_lang: str = 'es', region: str = None) -> Optional[Dict]:
        """
        Translate slang term to regional equivalent
        
        Args:
            slang_term: The slang word/phrase
            source_lang: Source language code
            target_lang: Target language code
            region: Preferred region (e.g., 'mexico', 'spain', 'colombia')
        
        Returns:
            Dictionary with regional translations and notes
        """
        slang_lower = slang_term.lower().strip()
        
        if source_lang not in self.slang:
            return None
        
        if slang_lower not in self.slang[source_lang]:
            return None
        
        slang_data = self.slang[source_lang][slang_lower]
        
        if target_lang not in slang_data:
            return None
        
        # Get all regional options
        regional_options = slang_data[target_lang]
        
        # If specific region requested and available, prioritize it
        if region and region in regional_options:
            preferred = regional_options[region]
            
            return {
                'original': slang_term,
                'source_language': source_lang,
                'target_language': target_lang,
                'preferred_region': region,
                'translation': preferred['most_common'],
                'all_options': preferred['options'],
                'regional_notes': preferred['notes'],
                'formality': slang_data.get('formality', 'informal'),
                'examples_source': slang_data.get(f'examples_{source_lang}', []),
                'examples_target': slang_data.get(f'examples_{target_lang}_{region}', []),
                'all_regions': list(regional_options.keys())
            }
        
        # Return all regional options if no preference
        return {
            'original': slang_term,
            'source_language': source_lang,
            'target_language': target_lang,
            'regional_variants': {
                reg: {
                    'most_common': data['most_common'],
                    'options': data['options'],
                    'notes': data['notes']
                }
                for reg, data in regional_options.items()
            },
            'formality': slang_data.get('formality', 'informal'),
            'needs_region_selection': True
        }
    
    def detect_slang(self, text: str, source_lang: str = 'en') -> List[Dict]:
        """
        Detect slang terms in text
        
        Returns list of detected slang with positions
        """
        detected = []
        
        if source_lang not in self.slang:
            return detected
        
        text_lower = text.lower()
        
        for slang_term in self.slang[source_lang].keys():
            # Simple word boundary detection
            pattern = r'\b' + re.escape(slang_term) + r'\b'
            matches = re.finditer(pattern, text_lower, re.IGNORECASE)
            
            for match in matches:
                detected.append({
                    'slang': slang_term,
                    'position': match.start(),
                    'matched_text': match.group(),
                    'data': self.slang[source_lang][slang_term]
                })
        
        return detected
    
    def generate_regional_comparison(self, slang_term: str, source_lang: str = 'en',
                                    target_lang: str = 'es') -> str:
        """
        Generate user-friendly comparison of regional variants
        
        Used by chatbot to show all regional options
        """
        translation = self.translate_slang(slang_term, source_lang, target_lang)
        
        if not translation:
            return None
        
        if 'needs_region_selection' not in translation:
            # Single region result
            msg = f"🗣️ **Slang: \"{slang_term}\"**\n\n"
            msg += f"**Regional Translation ({translation['preferred_region'].title()}):**\n"
            msg += f"Most common: **{translation['translation']}**\n"
            msg += f"Other options: {', '.join(translation['all_options'])}\n\n"
            msg += f"📝 {translation['regional_notes']}\n"
            return msg
        
        # Multiple regional options
        msg = f"🗣️ **Slang: \"{slang_term}\"**\n\n"
        msg += "This slang has different translations by region:\n\n"
        
        for region, data in translation['regional_variants'].items():
            msg += f"**{region.title()}:** {data['most_common']}\n"
            msg += f"  • Other options: {', '.join(data['options'])}\n"
            msg += f"  • Note: {data['notes']}\n\n"
        
        msg += "💬 **Which region should I use?** (Or I can pick the most common one)"
        
        return msg
    
    def set_regional_preference(self, user_id: str, region: str):
        """
        Store user's regional preference for consistent translations
        """
        self.regional_preferences[user_id] = region
    
    def get_regional_preference(self, user_id: str) -> Optional[str]:
        """
        Get user's stored regional preference
        """
        return self.regional_preferences.get(user_id)


# ============================================================================
# GLOBAL INSTANCE
# ============================================================================
slang_db = RegionalSlang()

# Test examples
if __name__ == "__main__":
    print("\n" + "="*60)
    print("REGIONAL SLANG DATABASE - COLLOQUIAL LANGUAGE HANDLER")
    print("="*60)
    
    # Test 1: Detect slang
    print("\n**TEST 1: Slang Detection**")
    text = "What's up, bro? That party was cool!"
    detected = slang_db.detect_slang(text, 'en')
    print(f"Text: {text}")
    print(f"Slang detected: {[d['slang'] for d in detected]}")
    
    # Test 2: Translate slang with region
    print("\n**TEST 2: Regional Translation (Mexico)**")
    translation = slang_db.translate_slang("bro", 'en', 'es', region='mexico')
    print(f"Original: {translation['original']}")
    print(f"Mexico: {translation['translation']}")
    print(f"All options: {translation['all_options']}")
    print(f"Notes: {translation['regional_notes']}")
    
    # Test 3: Regional comparison
    print("\n**TEST 3: Regional Comparison**")
    comparison = slang_db.generate_regional_comparison("cool", 'en', 'es')
    print(comparison)
    
    print("\n" + "="*60)
