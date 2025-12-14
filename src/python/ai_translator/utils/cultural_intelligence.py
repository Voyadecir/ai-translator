"""
Cultural Intelligence - Cross-Cultural Awareness System
Warns about cultural differences that could cause misunderstandings
Handles gestures, taboos, social norms, and sensitive topics

A professional interpreter doesn't just translate words - they bridge cultures.
This module prevents cultural mishaps by warning users about differences.

Example:
"Give a thumbs up" → ⚠️ WARNING: Offensive gesture in parts of Middle East
Better translation: "Show approval" or "Nod in agreement"
"""

import re
from typing import Dict, List, Optional, Tuple
from functools import lru_cache

class CulturalIntelligence:
    """
    Manages cultural awareness and cross-cultural communication
    
    Key Features:
    - Gesture warnings (what's OK in one culture, offensive in another)
    - Color symbolism (colors have different meanings across cultures)
    - Number superstitions (lucky/unlucky numbers vary)
    - Social norm differences (personal space, eye contact, etc.)
    - Religious sensitivity
    - Taboo topic awareness
    - Formality levels (tú vs usted, etc.)
    """
    
    def __init__(self):
        # Cultural databases
        self.gestures = self._load_gesture_database()
        self.colors = self._load_color_symbolism()
        self.numbers = self._load_number_superstitions()
        self.social_norms = self._load_social_norms()
        self.taboo_topics = self._load_taboo_topics()
        self.formality_rules = self._load_formality_rules()
    
    # ============================================================================
    # GESTURE DATABASE
    # ============================================================================
    
    def _load_gesture_database(self) -> Dict[str, Dict]:
        """
        Hand gestures and body language with cultural meanings
        """
        return {
            "thumbs up": {
                "generally_positive": ["USA", "Canada", "Western Europe", "Latin America"],
                "offensive_regions": ["Middle East", "West Africa", "parts of South America"],
                "meanings": {
                    "positive": "Good job, approval, OK",
                    "offensive": "Rude/vulgar gesture (equivalent to middle finger)"
                },
                "warning_level": "high",
                "safe_alternatives": {
                    "en": "Show approval, nod in agreement, say 'good job'",
                    "es": "Mostrar aprobación, asentir, decir 'buen trabajo'"
                },
                "cultural_note": "In Iran, Iraq, Afghanistan, parts of Italy and Greece, thumbs up is considered vulgar",
                "recommendation": "⚠️ Avoid describing this gesture when communicating with Middle Eastern cultures. Use verbal approval instead."
            },
            
            "ok hand sign": {
                "generally_positive": ["USA", "UK"],
                "offensive_regions": ["Brazil", "Turkey", "parts of Europe"],
                "meanings": {
                    "positive": "OK, everything is fine",
                    "offensive": "Vulgar gesture (sexual insult in Brazil)"
                },
                "warning_level": "high",
                "safe_alternatives": {
                    "en": "Say 'OK' verbally, nod, thumbs up (if appropriate)",
                    "es": "Decir 'OK' verbalmente, asentir"
                },
                "cultural_note": "In Brazil, this gesture is extremely offensive. In Turkey and some European countries, it's also considered rude.",
                "recommendation": "⚠️ NEVER use this gesture in Brazil or Turkey. Use verbal confirmation instead."
            },
            
            "beckoning with finger": {
                "generally_acceptable": ["USA", "Canada"],
                "offensive_regions": ["Philippines", "Japan", "Singapore", "parts of Asia"],
                "meanings": {
                    "neutral": "Come here",
                    "offensive": "Used only for animals or to insult someone"
                },
                "warning_level": "medium",
                "safe_alternatives": {
                    "en": "Wave entire hand palm-down, or say 'please come here'",
                    "es": "Hacer señas con toda la mano, palma hacia abajo"
                },
                "cultural_note": "In the Philippines, this gesture is used for dogs. In Japan, it's considered very rude to beckon with one finger.",
                "recommendation": "Use hand wave with palm down, or verbal invitation"
            },
            
            "crossed fingers": {
                "generally_positive": ["USA", "UK", "Western cultures"],
                "negative_regions": ["Vietnam"],
                "meanings": {
                    "positive": "Good luck, hoping for best outcome",
                    "offensive": "Represents female genitalia (Vietnam)"
                },
                "warning_level": "low",
                "safe_alternatives": {
                    "en": "Say 'good luck' or 'I hope so'",
                    "es": "Decir 'buena suerte' o 'espero que sí'"
                },
                "cultural_note": "Generally safe, but avoid in Vietnam"
            },
            
            "pointing with index finger": {
                "generally_acceptable": ["Western cultures"],
                "rude_regions": ["Japan", "Indonesia", "parts of Asia"],
                "meanings": {
                    "neutral": "Indicating direction or person",
                    "rude": "Aggressive or disrespectful"
                },
                "warning_level": "medium",
                "safe_alternatives": {
                    "en": "Point with entire hand, palm up; or use verbal directions",
                    "es": "Señalar con toda la mano, palma hacia arriba"
                },
                "cultural_note": "In Japan, pointing with index finger is considered rude. Use entire hand or point with chin.",
                "recommendation": "When communicating with Asian cultures, describe location verbally rather than mentioning pointing"
            },
            
            "showing sole of foot/shoe": {
                "generally_neutral": ["Western cultures"],
                "offensive_regions": ["Middle East", "Thailand", "India", "much of Asia"],
                "meanings": {
                    "neutral": "Casual sitting position",
                    "offensive": "Deep insult (feet are considered unclean)"
                },
                "warning_level": "high",
                "safe_alternatives": {
                    "en": "Keep feet on ground when sitting",
                    "es": "Mantener los pies en el suelo al sentarse"
                },
                "cultural_note": "In Middle Eastern and many Asian cultures, showing the sole of your foot or shoe is one of the worst insults.",
                "recommendation": "⚠️ When translating content for Middle Eastern audiences, avoid mentioning foot gestures"
            },
            
            "left hand use": {
                "generally_neutral": ["Western cultures"],
                "avoid_regions": ["Middle East", "India", "parts of Africa"],
                "meanings": {
                    "neutral": "Using non-dominant hand",
                    "offensive": "Left hand is for hygiene, not eating or greeting"
                },
                "warning_level": "high",
                "safe_alternatives": {
                    "en": "Always use right hand for eating, greeting, giving/receiving items",
                    "es": "Siempre usar la mano derecha para comer, saludar, dar/recibir"
                },
                "cultural_note": "In many cultures, the left hand is reserved for bathroom hygiene and is considered unclean. Never eat, shake hands, or pass items with left hand.",
                "recommendation": "When translating for Middle Eastern/Indian audiences, specify 'right hand' if hand use is mentioned"
            },
            
            "eye contact": {
                "expected": ["USA", "Canada", "Western Europe"],
                "disrespectful_regions": ["Japan", "Korea", "many Asian cultures", "some African cultures"],
                "meanings": {
                    "positive": "Confidence, honesty, engagement",
                    "negative": "Disrespectful, challenging authority"
                },
                "warning_level": "medium",
                "cultural_note": "In the West, lack of eye contact suggests dishonesty. In Asia, direct eye contact with elders or superiors is disrespectful.",
                "recommendation": "When translating communication advice, note cultural differences in eye contact expectations"
            },
            
            # Add 50+ more gestures...
        }
    
    # ============================================================================
    # COLOR SYMBOLISM
    # ============================================================================
    
    def _load_color_symbolism(self) -> Dict[str, Dict]:
        """
        Color meanings across cultures
        """
        return {
            "white": {
                "western": {
                    "meaning": "Purity, weddings, innocence, peace",
                    "context": "Positive, wedding color"
                },
                "eastern_asian": {
                    "meaning": "Death, mourning, funerals",
                    "context": "Worn at funerals, represents mourning",
                    "countries": ["China", "Japan", "Korea", "Vietnam"]
                },
                "warning": "⚠️ White wedding dresses are Western tradition. In China/Japan, white is for funerals.",
                "translation_note": "When translating wedding content for Asian audiences, clarify cultural context"
            },
            
            "red": {
                "western": {
                    "meaning": "Danger, stop, passion, love",
                    "context": "Warning color, Valentine's Day"
                },
                "chinese": {
                    "meaning": "Good luck, prosperity, celebration, weddings",
                    "context": "Traditional wedding color, Chinese New Year",
                    "countries": ["China", "Taiwan", "Singapore"]
                },
                "indian": {
                    "meaning": "Purity, weddings, fertility",
                    "context": "Brides wear red",
                    "countries": ["India", "Nepal"]
                },
                "south_african": {
                    "meaning": "Mourning",
                    "context": "Color of grief",
                    "countries": ["South Africa"]
                },
                "translation_note": "Red has opposite meanings: celebration (East) vs. danger (West)"
            },
            
            "yellow": {
                "western": {
                    "meaning": "Happiness, caution, cowardice",
                    "context": "Warning signs, cheerful color"
                },
                "chinese": {
                    "meaning": "Imperial, sacred, emperor's color",
                    "context": "Historically only emperors could wear yellow"
                },
                "egyptian": {
                    "meaning": "Mourning",
                    "context": "Color of death"
                },
                "translation_note": "Yellow ranges from imperial (China) to mourning (Egypt)"
            },
            
            "black": {
                "western": {
                    "meaning": "Mourning, formality, elegance",
                    "context": "Funerals, formal events, fashion"
                },
                "chinese": {
                    "meaning": "Bad luck, evil, mourning",
                    "context": "Avoid for celebrations"
                },
                "middle_eastern": {
                    "meaning": "Rebirth, mourning (context-dependent)",
                    "context": "Varies by country"
                },
                "translation_note": "Black is formal in West, but unlucky in Chinese culture"
            },
            
            "green": {
                "western": {
                    "meaning": "Nature, growth, money, envy",
                    "context": "Positive (environment), negative (jealousy)"
                },
                "islamic": {
                    "meaning": "Paradise, sacred, Islamic color",
                    "context": "Holy color, Prophet Muhammad's favorite"
                },
                "chinese": {
                    "meaning": "Infidelity (green hat metaphor)",
                    "context": "'Wearing a green hat' = being cuckolded"
                },
                "translation_note": "Green is sacred in Islam, but 'green hat' is an insult in China"
            },
            
            "purple": {
                "western": {
                    "meaning": "Royalty, luxury, spirituality",
                    "context": "Premium, high-end"
                },
                "thailand": {
                    "meaning": "Mourning (widows)",
                    "context": "Worn by widows in mourning"
                },
                "brazil": {
                    "meaning": "Death, mourning",
                    "context": "Funeral color"
                },
                "translation_note": "Purple is luxury in West, but mourning in Thailand/Brazil"
            },
            
            # Add 20+ more colors...
        }
    
    # ============================================================================
    # NUMBER SUPERSTITIONS
    # ============================================================================
    
    def _load_number_superstitions(self) -> Dict[str, Dict]:
        """
        Lucky and unlucky numbers across cultures
        """
        return {
            "4": {
                "cultures": {
                    "chinese_japanese_korean": {
                        "meaning": "Death",
                        "reason": "Pronounced same as 'death' (死, sǐ in Chinese)",
                        "avoidance": "Buildings skip 4th floor, hospitals skip room 4, avoid in phone numbers",
                        "severity": "extreme"
                    }
                },
                "warning": "⚠️ In East Asian cultures, 4 is like 13 in the West - extremely unlucky",
                "translation_note": "When translating addresses/room numbers for Chinese/Japanese audiences, note this superstition"
            },
            
            "8": {
                "cultures": {
                    "chinese": {
                        "meaning": "Prosperity, wealth, good fortune",
                        "reason": "Pronounced like 'prosper' (發, fā)",
                        "preference": "Phone numbers, license plates with 8 sell for premium prices",
                        "severity": "very_lucky"
                    }
                },
                "cultural_note": "In China, 8 is the luckiest number. Beijing Olympics started 08/08/08 at 8:08pm for this reason.",
                "translation_note": "Using 8 in Chinese contexts is seen as auspicious"
            },
            
            "13": {
                "cultures": {
                    "western": {
                        "meaning": "Bad luck, misfortune",
                        "reason": "Various religious and historical associations",
                        "avoidance": "Hotels skip 13th floor, airlines skip row 13",
                        "severity": "moderate_unlucky"
                    },
                    "italian": {
                        "meaning": "Good luck",
                        "reason": "Different cultural tradition",
                        "severity": "lucky"
                    }
                },
                "warning": "13 is unlucky in most Western countries, but lucky in Italy",
                "translation_note": "Context matters - Western vs. Italian"
            },
            
            "7": {
                "cultures": {
                    "western": {
                        "meaning": "Lucky, perfect",
                        "reason": "Religious significance (7 days of creation, etc.)",
                        "severity": "lucky"
                    },
                    "chinese": {
                        "meaning": "Togetherness (Qixi Festival - 7th day of 7th month)",
                        "reason": "Chinese Valentine's Day",
                        "severity": "romantic"
                    },
                    "thai": {
                        "meaning": "Unlucky",
                        "reason": "Cultural tradition",
                        "severity": "unlucky"
                    }
                },
                "cultural_note": "7 is lucky in West, romantic in China, unlucky in Thailand"
            },
            
            "9": {
                "cultures": {
                    "chinese": {
                        "meaning": "Longevity, eternity",
                        "reason": "Pronounced like 'long-lasting' (久, jiǔ)",
                        "severity": "very_lucky"
                    },
                    "japanese": {
                        "meaning": "Suffering",
                        "reason": "Pronounced like 'pain' (苦, ku)",
                        "severity": "unlucky"
                    }
                },
                "warning": "9 is lucky in China, unlucky in Japan - same region, opposite meanings"
            },
            
            "17": {
                "cultures": {
                    "italian": {
                        "meaning": "Very unlucky",
                        "reason": "Roman numerals XVII can be rearranged to spell VIXI ('I have lived' = I am dead)",
                        "avoidance": "Buildings skip 17th floor in Italy",
                        "severity": "unlucky"
                    }
                },
                "cultural_note": "17 is the Italian equivalent of 13 in other Western countries"
            },
            
            # Add 20+ more number superstitions...
        }
    
    # ============================================================================
    # SOCIAL NORMS
    # ============================================================================
    
    def _load_social_norms(self) -> Dict[str, Dict]:
        """
        Social behavior differences across cultures
        """
        return {
            "personal_space": {
                "large_distance": {
                    "cultures": ["USA", "Canada", "UK", "Northern Europe"],
                    "distance": "18-24 inches (arm's length)",
                    "note": "Standing too close feels invasive"
                },
                "small_distance": {
                    "cultures": ["Latin America", "Middle East", "Southern Europe"],
                    "distance": "12-15 inches or closer",
                    "note": "Standing far away feels cold/unfriendly"
                },
                "translation_note": "When translating social interaction advice, note regional norms"
            },
            
            "greeting_customs": {
                "handshake": {
                    "cultures": ["USA", "Europe", "Business contexts worldwide"],
                    "note": "Standard business greeting"
                },
                "bow": {
                    "cultures": ["Japan", "Korea"],
                    "note": "Depth of bow indicates respect level",
                    "warning": "⚠️ Don't bow and shake hands simultaneously in Japan"
                },
                "kiss_cheek": {
                    "cultures": ["France (2 kisses)", "Spain (2)", "Italy (2)", "Latin America (1-2)"],
                    "note": "Number of kisses varies by region",
                    "warning": "Not appropriate in business contexts in most countries"
                },
                "no_physical_contact": {
                    "cultures": ["Some Middle Eastern countries", "Orthodox Jewish communities"],
                    "note": "Men and women don't shake hands across genders",
                    "warning": "⚠️ Always wait for other person to initiate handshake"
                }
            },
            
            "gift_giving": {
                "avoid_clocks_china": {
                    "culture": "China",
                    "item": "Clocks",
                    "reason": "'Giving clock' sounds like 'attending a funeral' in Chinese",
                    "severity": "extremely_offensive",
                    "warning": "⚠️ NEVER give clocks as gifts in China"
                },
                "avoid_yellow_flowers_latin_america": {
                    "culture": "Latin America",
                    "item": "Yellow flowers",
                    "reason": "Associated with death and mourning",
                    "severity": "offensive"
                },
                "avoid_sharp_objects_china": {
                    "culture": "China, Korea, Japan",
                    "item": "Knives, scissors (sharp objects)",
                    "reason": "Symbolizes cutting relationship",
                    "severity": "offensive"
                },
                "unwrap_immediately_usa": {
                    "culture": "USA, Western cultures",
                    "custom": "Open gifts immediately in front of giver",
                    "reason": "Shows appreciation"
                },
                "dont_unwrap_china_japan": {
                    "culture": "China, Japan",
                    "custom": "DON'T open gifts immediately",
                    "reason": "Considered greedy/impolite to open in front of giver"
                }
            },
            
            "dining_etiquette": {
                "burping_china": {
                    "culture": "China (traditionally)",
                    "action": "Burping after meal",
                    "meaning": "Compliment to chef (traditional, less common now)",
                    "western_meaning": "Rude"
                },
                "slurping_japan": {
                    "culture": "Japan",
                    "action": "Slurping noodles",
                    "meaning": "Compliment, shows enjoyment",
                    "western_meaning": "Rude"
                },
                "finishing_plate_china": {
                    "culture": "China",
                    "action": "Finishing all food on plate",
                    "meaning": "Host didn't provide enough food (implies poverty)",
                    "western_meaning": "Polite, shows appreciation"
                },
                "tipping_usa": {
                    "culture": "USA",
                    "action": "Tipping 15-20%",
                    "meaning": "Expected, part of server wages",
                    "contrast": "Japan - tipping is OFFENSIVE"
                },
                "no_tipping_japan": {
                    "culture": "Japan",
                    "action": "Tipping",
                    "meaning": "Insulting (implies they need charity)",
                    "warning": "⚠️ NEVER tip in Japan - it's considered rude"
                }
            },
            
            # Add 50+ more social norms...
        }
    
    # ============================================================================
    # TABOO TOPICS
    # ============================================================================
    
    def _load_taboo_topics(self) -> Dict[str, Dict]:
        """
        Topics that are sensitive or taboo in certain cultures
        """
        return {
            "money_salary": {
                "taboo_cultures": ["USA", "UK", "many Western cultures"],
                "acceptable_cultures": ["China", "some Asian cultures"],
                "note": "In the West, asking about salary is very rude. In China, it's normal small talk.",
                "translation_guidance": "When translating salary discussions for Western audiences, add cultural context"
            },
            
            "age": {
                "taboo_cultures": ["Western cultures (especially asking women)"],
                "acceptable_cultures": ["China", "Korea", "many Asian cultures"],
                "note": "In Western cultures, asking a woman's age is rude. In Asian cultures, age determines social hierarchy and forms of address.",
                "translation_guidance": "Age questions normal in Asian contexts, rude in Western"
            },
            
            "politics_religion": {
                "taboo_cultures": ["USA (in polite conversation)", "many Western countries"],
                "note": "Religion and politics are considered too divisive for casual conversation",
                "translation_guidance": "Mark as sensitive topic when translating for mixed audiences"
            },
            
            "death_mortality": {
                "taboo_cultures": ["Western cultures (avoid direct discussion)"],
                "acceptable_cultures": ["Mexico (Day of the Dead celebrations)", "Some Asian cultures"],
                "note": "Western cultures avoid discussing death directly. Mexican culture celebrates death openly.",
                "translation_guidance": "Consider cultural attitudes toward mortality"
            },
            
            # Add 30+ more taboo topics...
        }
    
    # ============================================================================
    # FORMALITY RULES
    # ============================================================================
    
    def _load_formality_rules(self) -> Dict[str, Dict]:
        """
        Formality and address rules across languages
        """
        return {
            "spanish_tu_vs_usted": {
                "informal": {
                    "form": "tú",
                    "usage": "Friends, family, peers, children",
                    "verb_form": "second person singular"
                },
                "formal": {
                    "form": "usted",
                    "usage": "Elders, strangers, authority figures, professional contexts",
                    "verb_form": "third person singular"
                },
                "regional_differences": {
                    "spain": "Tú is increasingly common, even with strangers",
                    "latin_america": "Usted shows more respect, used more frequently",
                    "argentina": "Use 'vos' instead of 'tú' for informal"
                },
                "translation_guidance": "Always default to 'usted' unless context clearly indicates familiarity",
                "importance": "HIGH - using wrong form can be insulting"
            },
            
            "french_tu_vs_vous": {
                "informal": {
                    "form": "tu",
                    "usage": "Friends, family, children"
                },
                "formal": {
                    "form": "vous",
                    "usage": "Strangers, elders, professional contexts, showing respect"
                },
                "note": "French is stricter than Spanish about formality",
                "translation_guidance": "Default to 'vous' - better to be too formal than too informal"
            },
            
            "german_du_vs_sie": {
                "informal": {
                    "form": "du",
                    "usage": "Friends, family, young people among peers"
                },
                "formal": {
                    "form": "Sie",
                    "usage": "Professional contexts, strangers, showing respect"
                },
                "note": "Very strict formality rules in German business culture",
                "translation_guidance": "Always use 'Sie' in professional contexts"
            },
            
            "japanese_honorifics": {
                "system": "Complex honorific system",
                "forms": {
                    "san": "Mr./Mrs./Ms. - neutral respect",
                    "sama": "High respect, customers, deity",
                    "kun": "Young males, juniors",
                    "chan": "Children, close friends, cute"
                },
                "translation_guidance": "Japanese has multiple levels of formality built into grammar itself",
                "importance": "CRITICAL - wrong honorific can be very offensive"
            },
            
            # Add 20+ more formality systems...
        }
    
    # ============================================================================
    # WARNING & GUIDANCE METHODS
    # ============================================================================
    
    def check_gesture_warning(self, text: str, target_culture: str = None) -> Optional[Dict]:
        """
        Check if text mentions a gesture that could be offensive in target culture
        
        Returns warning if gesture found
        """
        warnings = []
        
        text_lower = text.lower()
        
        for gesture, data in self.gestures.items():
            if gesture in text_lower:
                # Check if offensive in target culture
                if target_culture:
                    if target_culture in data.get('offensive_regions', []):
                        warnings.append({
                            'gesture': gesture,
                            'warning_level': data['warning_level'],
                            'reason': data['cultural_note'],
                            'recommendation': data['recommendation'],
                            'safe_alternatives': data['safe_alternatives']
                        })
                else:
                    # General warning if target culture not specified
                    if data.get('offensive_regions'):
                        warnings.append({
                            'gesture': gesture,
                            'warning_level': data['warning_level'],
                            'potentially_offensive_in': data['offensive_regions'],
                            'reason': data['cultural_note'],
                            'recommendation': data['recommendation']
                        })
        
        return warnings if warnings else None
    
    def generate_cultural_warning(self, warnings: List[Dict]) -> str:
        """
        Generate user-friendly cultural warning message
        """
        if not warnings:
            return None
        
        message = "🌍 **CULTURAL AWARENESS ALERT**\n\n"
        message += f"This content contains {len(warnings)} potential cultural issue(s):\n\n"
        
        for i, warning in enumerate(warnings, 1):
            message += f"**{i}. {warning['gesture'].title()}**\n"
            message += f"⚠️ Warning Level: {warning['warning_level'].upper()}\n"
            message += f"**Issue:** {warning['reason']}\n"
            
            if 'recommendation' in warning:
                message += f"**Recommendation:** {warning['recommendation']}\n"
            
            if 'safe_alternatives' in warning:
                alts = warning['safe_alternatives']
                message += f"**Safe Alternative:** {alts.get('en', 'See recommendation')}\n"
            
            message += "\n"
        
        return message


# ============================================================================
# GLOBAL INSTANCE
# ============================================================================
cultural_intel = CulturalIntelligence()

# Test examples
if __name__ == "__main__":
    print("\n" + "="*60)
    print("CULTURAL INTELLIGENCE - CROSS-CULTURAL AWARENESS")
    print("="*60)
    
    # Test 1: Gesture warning
    print("\n**TEST 1: Gesture Warning**")
    text = "Give me a thumbs up when you're ready."
    warnings = cultural_intel.check_gesture_warning(text, target_culture="Middle East")
    if warnings:
        warning_msg = cultural_intel.generate_cultural_warning(warnings)
        print(warning_msg)
    
    # Test 2: Color symbolism
    print("\n**TEST 2: Color Symbolism**")
    white_meaning = cultural_intel.colors['white']
    print(f"White in Western culture: {white_meaning['western']['meaning']}")
    print(f"White in East Asian culture: {white_meaning['eastern_asian']['meaning']}")
    print(f"Warning: {white_meaning['warning']}")
    
    # Test 3: Number superstitions
    print("\n**TEST 3: Number Superstitions**")
    four_meaning = cultural_intel.numbers['4']
    print(f"Number 4 in Chinese/Japanese/Korean:")
    print(f"Meaning: {four_meaning['cultures']['chinese_japanese_korean']['meaning']}")
    print(f"Warning: {four_meaning['warning']}")
    
    print("\n" + "="*60)
