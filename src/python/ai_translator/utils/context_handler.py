"""
Context Handler - Ambiguous Word & Multi-Meaning Translation System
Handles words with multiple meanings, asks for clarification via chatbot
Provides dictionary-style responses with ALL possible meanings
"""

import re
from typing import Dict, List, Optional, Tuple
from functools import lru_cache

class ContextHandler:
    """
    Manages ambiguous words and multi-meaning translations
    
    Key Features:
    - Detects when a word has multiple meanings
    - Requests context via chatbot when needed
    - Provides ALL possible translations (not just one)
    - Dictionary-style responses with examples
    - Integrates with translation_dictionaries.py for authoritative definitions
    """
    
    def __init__(self):
        # Load ambiguous words database
        self.ambiguous_words = {
            'en': self._load_english_ambiguous(),
            'es': self._load_spanish_ambiguous(),
        }
        
        # Track conversation context for follow-up clarifications
        self.conversation_context = {}
    
    # ============================================================================
    # ENGLISH AMBIGUOUS WORDS
    # ============================================================================
    
    def _load_english_ambiguous(self) -> Dict[str, Dict]:
        """
        English words with multiple meanings requiring context
        """
        return {
            "heart": {
                "anatomical": {
                    "es": "corazón (órgano)",
                    "pt": "coração (órgão)",
                    "definition": "The muscular organ that pumps blood",
                    "examples_en": [
                        "My heart is beating fast",
                        "Heart disease is common",
                        "The doctor listened to her heart"
                    ],
                    "examples_es": [
                        "Mi corazón está latiendo rápido",
                        "Las enfermedades del corazón son comunes",
                        "El doctor escuchó su corazón"
                    ]
                },
                "romantic": {
                    "es": "mi amor, corazón, mi cielo",
                    "pt": "meu amor, coração",
                    "definition": "Term of endearment for loved one",
                    "examples_en": [
                        "Good morning, my heart",
                        "You stole my heart",
                        "She's the queen of my heart"
                    ],
                    "examples_es": [
                        "Buenos días, mi amor",
                        "Robaste mi corazón",
                        "Ella es la reina de mi corazón"
                    ]
                },
                "figurative_courage": {
                    "es": "valor, coraje",
                    "pt": "coragem, ânimo",
                    "definition": "Courage or bravery",
                    "examples_en": [
                        "I don't have the heart to tell her",
                        "He lost heart after the failure",
                        "Take heart - things will get better"
                    ],
                    "examples_es": [
                        "No tengo el valor de decírselo",
                        "Perdió el ánimo después del fracaso",
                        "Ten valor - las cosas mejorarán"
                    ]
                },
                "figurative_center": {
                    "es": "centro, núcleo, corazón",
                    "pt": "centro, núcleo",
                    "definition": "The central or most important part",
                    "examples_en": [
                        "The heart of the city",
                        "At the heart of the matter",
                        "The heart of the problem"
                    ],
                    "examples_es": [
                        "El centro de la ciudad",
                        "En el corazón del asunto",
                        "El núcleo del problema"
                    ]
                }
            },
            
            "run": {
                "physical_movement": {
                    "es": "correr",
                    "pt": "correr",
                    "definition": "To move swiftly on foot",
                    "examples_en": [
                        "I run every morning",
                        "She runs marathons",
                        "The child ran to his mother"
                    ],
                    "examples_es": [
                        "Corro todas las mañanas",
                        "Ella corre maratones",
                        "El niño corrió hacia su madre"
                    ]
                },
                "operate_function": {
                    "es": "funcionar, operar",
                    "pt": "funcionar, operar",
                    "definition": "To operate or function",
                    "examples_en": [
                        "The machine runs smoothly",
                        "This software runs on Windows",
                        "The engine is running"
                    ],
                    "examples_es": [
                        "La máquina funciona sin problemas",
                        "Este software funciona en Windows",
                        "El motor está funcionando"
                    ]
                },
                "manage_control": {
                    "es": "dirigir, administrar, gestionar",
                    "pt": "dirigir, administrar",
                    "definition": "To manage or be in charge of",
                    "examples_en": [
                        "She runs the company",
                        "He runs a small business",
                        "They run the program efficiently"
                    ],
                    "examples_es": [
                        "Ella dirige la empresa",
                        "Él administra un pequeño negocio",
                        "Ellos gestionan el programa eficientemente"
                    ]
                },
                "flow_liquid": {
                    "es": "fluir, correr, gotear",
                    "pt": "fluir, correr, escorrer",
                    "definition": "To flow or drip (liquids)",
                    "examples_en": [
                        "Water runs from the tap",
                        "Tears ran down her face",
                        "The river runs to the sea"
                    ],
                    "examples_es": [
                        "El agua corre del grifo",
                        "Las lágrimas corrieron por su cara",
                        "El río fluye hacia el mar"
                    ]
                }
            },
            
            "bank": {
                "financial_institution": {
                    "es": "banco (institución financiera)",
                    "pt": "banco (instituição financeira)",
                    "definition": "A financial institution",
                    "examples_en": [
                        "I went to the bank today",
                        "The bank approved my loan",
                        "She works at a bank"
                    ],
                    "examples_es": [
                        "Fui al banco hoy",
                        "El banco aprobó mi préstamo",
                        "Ella trabaja en un banco"
                    ]
                },
                "river_edge": {
                    "es": "orilla, ribera",
                    "pt": "margem, beira",
                    "definition": "The edge of a river or stream",
                    "examples_en": [
                        "They sat on the river bank",
                        "The bank was muddy",
                        "Flowers grew along the bank"
                    ],
                    "examples_es": [
                        "Se sentaron en la orilla del río",
                        "La ribera estaba lodosa",
                        "Las flores crecían a lo largo de la orilla"
                    ]
                }
            },
            
            "change": {
                "alteration": {
                    "es": "cambio, modificación",
                    "pt": "mudança, alteração",
                    "definition": "To make or become different",
                    "examples_en": [
                        "I need to change my plans",
                        "The weather will change tomorrow",
                        "She changed her mind"
                    ],
                    "examples_es": [
                        "Necesito cambiar mis planes",
                        "El clima cambiará mañana",
                        "Ella cambió de opinión"
                    ]
                },
                "money_coins": {
                    "es": "cambio (dinero), monedas sueltas",
                    "pt": "troco, moedas",
                    "definition": "Money in small denominations or coins",
                    "examples_en": [
                        "Do you have change for a twenty?",
                        "Keep the change",
                        "I need change for the parking meter"
                    ],
                    "examples_es": [
                        "¿Tienes cambio de un billete de veinte?",
                        "Quédate con el cambio",
                        "Necesito monedas para el parquímetro"
                    ]
                }
            },
            
            "fair": {
                "just_equitable": {
                    "es": "justo, equitativo",
                    "pt": "justo, equitativo",
                    "definition": "Just, equitable, or impartial",
                    "examples_en": [
                        "That's not fair!",
                        "The judge made a fair decision",
                        "Everyone deserves fair treatment"
                    ],
                    "examples_es": [
                        "¡Eso no es justo!",
                        "El juez tomó una decisión justa",
                        "Todos merecen un trato equitativo"
                    ]
                },
                "light_complexion": {
                    "es": "claro, pálido (piel/cabello)",
                    "pt": "claro, pálido",
                    "definition": "Light-colored (skin or hair)",
                    "examples_en": [
                        "She has fair skin",
                        "Fair-haired children",
                        "His fair complexion"
                    ],
                    "examples_es": [
                        "Ella tiene piel clara",
                        "Niños de cabello claro",
                        "Su tez pálida"
                    ]
                },
                "carnival_event": {
                    "es": "feria, feria",
                    "pt": "feira",
                    "definition": "A gathering with entertainment and vendors",
                    "examples_en": [
                        "We went to the county fair",
                        "The fair has rides and games",
                        "There's a book fair this weekend"
                    ],
                    "examples_es": [
                        "Fuimos a la feria del condado",
                        "La feria tiene juegos mecánicos",
                        "Hay una feria del libro este fin de semana"
                    ]
                }
            },
            
            "date": {
                "calendar_day": {
                    "es": "fecha",
                    "pt": "data",
                    "definition": "A specific day in a calendar",
                    "examples_en": [
                        "What's today's date?",
                        "The due date is tomorrow",
                        "Please write the date on top"
                    ],
                    "examples_es": [
                        "¿Qué fecha es hoy?",
                        "La fecha límite es mañana",
                        "Por favor escribe la fecha arriba"
                    ]
                },
                "romantic_appointment": {
                    "es": "cita (romántica)",
                    "pt": "encontro (romântico)",
                    "definition": "A romantic appointment or outing",
                    "examples_en": [
                        "They went on a date",
                        "It was our first date",
                        "Would you like to go on a date with me?"
                    ],
                    "examples_es": [
                        "Salieron en una cita",
                        "Fue nuestra primera cita",
                        "¿Te gustaría salir en una cita conmigo?"
                    ]
                },
                "fruit": {
                    "es": "dátil (fruta)",
                    "pt": "tâmara (fruta)",
                    "definition": "Sweet fruit from a date palm",
                    "examples_en": [
                        "Dates are sweet",
                        "I love stuffed dates",
                        "Date palms grow in warm climates"
                    ],
                    "examples_es": [
                        "Los dátiles son dulces",
                        "Me encantan los dátiles rellenos",
                        "Las palmeras datileras crecen en climas cálidos"
                    ]
                }
            },
            
            # Add 100+ more ambiguous words...
        }
    
    def _load_spanish_ambiguous(self) -> Dict[str, Dict]:
        """
        Spanish words with multiple meanings
        """
        return {
            "banco": {
                "financial": {
                    "en": "bank (financial institution)",
                    "definition": "Institución financiera",
                    "examples_es": [
                        "Voy al banco a sacar dinero",
                        "Trabajo en un banco"
                    ],
                    "examples_en": [
                        "I'm going to the bank to withdraw money",
                        "I work at a bank"
                    ]
                },
                "bench": {
                    "en": "bench (seat)",
                    "definition": "Asiento largo",
                    "examples_es": [
                        "Me senté en el banco del parque",
                        "Hay un banco bajo el árbol"
                    ],
                    "examples_en": [
                        "I sat on the park bench",
                        "There's a bench under the tree"
                    ]
                },
                "school_fish": {
                    "en": "school (of fish)",
                    "definition": "Grupo de peces",
                    "examples_es": [
                        "Vi un banco de peces",
                        "El banco de atunes pasó cerca"
                    ],
                    "examples_en": [
                        "I saw a school of fish",
                        "The school of tuna passed by"
                    ]
                }
            },
            
            # Add more Spanish ambiguous words...
        }
    
    # ============================================================================
    # CORE METHODS
    # ============================================================================
    
    def is_ambiguous(self, word: str, language: str = 'en') -> bool:
        """Check if a word has multiple meanings"""
        word_lower = word.lower().strip()
        
        if language in self.ambiguous_words:
            return word_lower in self.ambiguous_words[language]
        
        return False
    
    def get_all_meanings(self, word: str, source_lang: str = 'en', 
                        target_lang: str = 'es') -> Optional[Dict]:
        """
        Get ALL possible meanings for an ambiguous word
        
        Returns dictionary with all meanings, examples, and translations
        """
        word_lower = word.lower().strip()
        
        if not self.is_ambiguous(word, source_lang):
            return None
        
        meanings = self.ambiguous_words[source_lang][word_lower]
        
        # Format response with all meanings
        response = {
            'word': word,
            'source_language': source_lang,
            'target_language': target_lang,
            'is_ambiguous': True,
            'meaning_count': len(meanings),
            'meanings': []
        }
        
        for meaning_key, meaning_data in meanings.items():
            meaning_entry = {
                'type': meaning_key.replace('_', ' ').title(),
                'translation': meaning_data.get(target_lang, ''),
                'definition': meaning_data.get('definition', ''),
                'examples_source': meaning_data.get(f'examples_{source_lang}', []),
                'examples_target': meaning_data.get(f'examples_{target_lang}', [])
            }
            response['meanings'].append(meaning_entry)
        
        return response
    
    def generate_clarification_request(self, word: str, source_lang: str = 'en',
                                      target_lang: str = 'es') -> str:
        """
        Generate a chatbot clarification request for ambiguous words
        
        Returns a user-friendly message asking for context
        """
        meanings_data = self.get_all_meanings(word, source_lang, target_lang)
        
        if not meanings_data:
            return None
        
        message = f"The word '{word}' has {meanings_data['meaning_count']} different meanings in {source_lang.upper()}. Which context do you need?\n\n"
        
        for i, meaning in enumerate(meanings_data['meanings'], 1):
            message += f"{i}. **{meaning['type']}** ({meaning['definition']})\n"
            message += f"   → {target_lang.upper()}: {meaning['translation']}\n"
            
            if meaning['examples_source']:
                message += f"   Example: \"{meaning['examples_source'][0]}\"\n"
                if meaning['examples_target']:
                    message += f"   Translation: \"{meaning['examples_target'][0]}\"\n"
            message += "\n"
        
        message += "💬 **Can you use it in a sentence so I can give you the best translation?**"
        
        return message
    
    def detect_meaning_from_sentence(self, sentence: str, word: str, 
                                    source_lang: str = 'en') -> Optional[str]:
        """
        Analyze sentence context to determine which meaning of ambiguous word is being used
        
        Uses keyword matching and context clues
        """
        sentence_lower = sentence.lower()
        word_lower = word.lower()
        
        if not self.is_ambiguous(word, source_lang):
            return None
        
        meanings = self.ambiguous_words[source_lang][word_lower]
        
        # Context clue keywords for each meaning
        context_clues = {
            "heart": {
                "anatomical": ["beat", "pump", "attack", "disease", "doctor", "hospital", "chest", "rate"],
                "romantic": ["love", "dear", "sweetheart", "darling", "mine", "yours"],
                "figurative_courage": ["have the", "lose", "take", "courage", "brave"],
                "figurative_center": ["of the", "city", "matter", "problem", "issue"]
            },
            "run": {
                "physical_movement": ["fast", "slow", "marathon", "jog", "exercise", "morning"],
                "operate_function": ["machine", "software", "engine", "computer", "program", "smoothly"],
                "manage_control": ["company", "business", "organization", "manage", "direct"],
                "flow_liquid": ["water", "tears", "river", "tap", "drain", "leak"]
            },
            "bank": {
                "financial_institution": ["money", "account", "loan", "deposit", "atm", "credit"],
                "river_edge": ["river", "water", "shore", "muddy", "fishing"]
            },
            # Add more context clues...
        }
        
        if word_lower in context_clues:
            meaning_scores = {}
            
            for meaning_type, keywords in context_clues[word_lower].items():
                score = sum(1 for keyword in keywords if keyword in sentence_lower)
                meaning_scores[meaning_type] = score
            
            # Return meaning with highest score
            if meaning_scores:
                best_meaning = max(meaning_scores, key=meaning_scores.get)
                if meaning_scores[best_meaning] > 0:
                    return best_meaning
        
        return None  # Could not determine meaning from context
    
    def translate_with_context(self, sentence: str, word: str, 
                              source_lang: str = 'en', target_lang: str = 'es') -> Dict:
        """
        Translate ambiguous word within sentence context
        
        Returns:
        - detected_meaning: Which meaning was detected
        - translation: The appropriate translation
        - confidence: How confident we are (0.0 to 1.0)
        """
        detected_meaning = self.detect_meaning_from_sentence(sentence, word, source_lang)
        
        if not detected_meaning:
            # Could not determine meaning - return all options
            return {
                'word': word,
                'detected_meaning': None,
                'translation': None,
                'confidence': 0.0,
                'all_meanings': self.get_all_meanings(word, source_lang, target_lang),
                'needs_clarification': True
            }
        
        # Get translation for detected meaning
        meanings_data = self.get_all_meanings(word, source_lang, target_lang)
        
        for meaning in meanings_data['meanings']:
            if meaning['type'].lower().replace(' ', '_') == detected_meaning:
                return {
                    'word': word,
                    'detected_meaning': detected_meaning,
                    'translation': meaning['translation'],
                    'confidence': 0.85,  # Good confidence from context clues
                    'definition': meaning['definition'],
                    'needs_clarification': False
                }
        
        # Fallback
        return {
            'word': word,
            'detected_meaning': None,
            'translation': None,
            'confidence': 0.0,
            'needs_clarification': True
        }


# ============================================================================
# GLOBAL INSTANCE
# ============================================================================
context_handler = ContextHandler()

# Test examples
if __name__ == "__main__":
    print("\n" + "="*60)
    print("CONTEXT HANDLER - AMBIGUOUS WORD SYSTEM")
    print("="*60)
    
    # Test 1: Single word translation (should request clarification)
    print("\n**TEST 1: Single word 'heart'**")
    clarification = context_handler.generate_clarification_request('heart', 'en', 'es')
    print(clarification)
    
    # Test 2: Sentence with context (should auto-detect meaning)
    print("\n**TEST 2: Sentence context detection**")
    result = context_handler.translate_with_context(
        "My heart is beating fast", 
        "heart", 
        'en', 
        'es'
    )
    print(f"Detected meaning: {result['detected_meaning']}")
    print(f"Translation: {result['translation']}")
    print(f"Confidence: {result['confidence']}")
    
    print("\n" + "="*60)
