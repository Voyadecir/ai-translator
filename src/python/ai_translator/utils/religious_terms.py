"""
Religious Terms - Theologically Accurate Translations
Based on jw.org methodology: Triple-checked, doctrinally precise translations
Handles Christian, Islamic, Jewish, Hindu, Buddhist, and other religious terminology

Philosophy from jw.org:
1. Theological accuracy is paramount
2. Cultural sensitivity is essential
3. Consistency across all materials
4. Never insert interpretation - translate meaning accurately

Example:
"baptism" → NOT just "bautismo" (too vague)
"baptism" → "bautismo por inmersión en agua" (doctrinally precise when context requires)
"""

import re
from typing import Dict, List, Optional, Tuple
from functools import lru_cache

class ReligiousTerms:
    """
    Manages theologically accurate religious terminology
    
    Key Principles (from jw.org methodology):
    - Accuracy: Preserve theological meaning precisely
    - Consistency: Same term = same translation throughout
    - Clarity: Explain concepts unfamiliar in target culture
    - Respect: Handle all faiths with equal care
    - Context: Denominational differences matter
    
    Coverage:
    - Christianity (Catholic, Protestant, Orthodox, various denominations)
    - Islam
    - Judaism
    - Hinduism
    - Buddhism
    - Sikhism
    - Other world religions
    """
    
    def __init__(self):
        # Religious terminology databases
        self.christian_terms = self._load_christian_terms()
        self.islamic_terms = self._load_islamic_terms()
        self.jewish_terms = self._load_jewish_terms()
        self.hindu_terms = self._load_hindu_terms()
        self.buddhist_terms = self._load_buddhist_terms()
        
        # Cross-reference database (terms shared across religions)
        self.shared_terms = self._load_shared_terms()
    
    # ============================================================================
    # CHRISTIAN TERMINOLOGY
    # ============================================================================
    
    def _load_christian_terms(self) -> Dict[str, Dict]:
        """
        Christian theological terms with precise translations
        Based on jw.org and other authoritative Christian translation standards
        """
        return {
            # FOUNDATIONAL CONCEPTS
            "God": {
                "theological_meaning": "Supreme Being, Creator, monotheistic deity",
                "es": {
                    "translation": "Dios",
                    "notes": "Universal Christian term in Spanish",
                    "context": "Capitalized to show reverence"
                },
                "pt": {"translation": "Deus"},
                "fr": {"translation": "Dieu"},
                "ar": {"translation": "الله (Allah)", "note": "Same word used by Arabic Christians and Muslims"},
                "denominational_notes": "All Christian denominations agree on this translation",
                "reverence_note": "Always capitalize in translation to show respect"
            },
            
            "Jesus Christ": {
                "theological_meaning": "Central figure of Christianity, believed to be Son of God and Messiah",
                "es": {
                    "translation": "Jesucristo",
                    "alternative": "Jesús Cristo (two words)",
                    "notes": "Both forms acceptable"
                },
                "pt": {"translation": "Jesus Cristo"},
                "fr": {"translation": "Jésus-Christ"},
                "ar": {"translation": "يسوع المسيح (Yasu' al-Masih)"},
                "hebrew": {"translation": "ישוע המשיח (Yeshua HaMashiach)"},
                "denominational_notes": "All Christian denominations agree",
                "translation_principle": "Preserve both titles: Jesus (personal name) + Christ (title meaning 'anointed one')"
            },
            
            "Holy Spirit": {
                "theological_meaning": "Third person of Christian Trinity; Spirit of God",
                "es": {
                    "translation": "Espíritu Santo",
                    "capitalization": "Both words capitalized",
                    "notes": "Universal Christian term"
                },
                "pt": {"translation": "Espírito Santo"},
                "fr": {"translation": "Saint-Esprit"},
                "denominational_differences": {
                    "catholic_orthodox": "Emphasize as Person of Trinity",
                    "some_protestant": "Emphasize as God's active force",
                    "translation_note": "Term itself is consistent; theology varies"
                },
                "translation_principle": "Always capitalize both words to show divinity"
            },
            
            "Trinity": {
                "theological_meaning": "Christian doctrine: God exists as three persons (Father, Son, Holy Spirit) in one Being",
                "es": {
                    "translation": "Trinidad",
                    "full_explanation": "La Trinidad - Padre, Hijo y Espíritu Santo en un solo Dios"
                },
                "pt": {"translation": "Trindade"},
                "fr": {"translation": "Trinité"},
                "denominational_differences": {
                    "catholic_orthodox_most_protestant": "Core doctrine",
                    "jehovahs_witnesses_unitarians": "Reject this doctrine",
                    "translation_note": "Translate term accurately; acknowledge theological differences"
                },
                "sensitivity_note": "Some denominations don't accept this concept - translate neutrally"
            },
            
            # SALVATION & REDEMPTION
            "salvation": {
                "theological_meaning": "Deliverance from sin and its consequences; eternal life with God",
                "es": {
                    "translation": "salvación",
                    "context_examples": [
                        "salvation through faith = salvación por fe",
                        "salvation by grace = salvación por gracia"
                    ]
                },
                "pt": {"translation": "salvação"},
                "fr": {"translation": "salut"},
                "denominational_differences": {
                    "catholic": "Faith + works + sacraments",
                    "protestant": "Faith alone (sola fide)",
                    "orthodox": "Theosis (becoming like God)",
                    "translation_note": "Term is consistent; path to salvation varies by denomination"
                },
                "translation_principle": "Translate term precisely; don't insert theological interpretation"
            },
            
            "grace": {
                "theological_meaning": "Unmerited favor and love of God toward humanity",
                "es": {
                    "translation": "gracia",
                    "full_phrase": "la gracia de Dios"
                },
                "pt": {"translation": "graça"},
                "fr": {"translation": "grâce"},
                "theological_precision": "Not just 'favor' - specifically UNMERITED favor",
                "translation_note": "Context often requires 'gracia divina' or 'gracia de Dios' for clarity"
            },
            
            "faith": {
                "theological_meaning": "Trust and belief in God; confidence in divine promises",
                "es": {
                    "translation": "fe",
                    "vs_belief": "fe (faith - deeper) vs. creencia (belief - intellectual)"
                },
                "pt": {"translation": "fé"},
                "fr": {"translation": "foi"},
                "translation_distinction": "Faith (fe) is deeper than mere belief (creencia) - implies trust and commitment",
                "jw_org_principle": "Distinguish 'faith' from 'belief' when theologically significant"
            },
            
            "sin": {
                "theological_meaning": "Transgression against God's law; moral wrongdoing",
                "es": {
                    "translation": "pecado",
                    "singular": "pecado",
                    "plural": "pecados"
                },
                "pt": {"translation": "pecado"},
                "fr": {"translation": "péché"},
                "theological_nuances": {
                    "original_sin": "pecado original",
                    "mortal_sin": "pecado mortal (Catholic)",
                    "venial_sin": "pecado venial (Catholic)"
                },
                "translation_note": "Catholic theology distinguishes mortal vs. venial sins; Protestant theology generally does not"
            },
            
            "redemption": {
                "theological_meaning": "Act of being saved from sin through Christ's sacrifice",
                "es": {
                    "translation": "redención",
                    "related_terms": "rescate (ransom)"
                },
                "pt": {"translation": "redenção"},
                "fr": {"translation": "rédemption"},
                "theological_depth": "Implies 'buying back' or 'ransom' - Christ paid price for humanity's sins"
            },
            
            # SACRAMENTS & ORDINANCES
            "baptism": {
                "theological_meaning": "Christian initiation rite involving water",
                "es": {
                    "translation": "bautismo",
                    "basic": "bautismo",
                    "precise": "bautismo por inmersión en agua (if method matters)"
                },
                "pt": {"translation": "batismo"},
                "fr": {"translation": "baptême"},
                "denominational_differences": {
                    "baptist_churches": "Full immersion of believers only",
                    "catholic_orthodox": "Infant baptism, sprinkling or immersion",
                    "methodist_presbyterian": "Infant or adult, sprinkling/pouring/immersion",
                    "translation_note": "Basic term is consistent; method and age vary"
                },
                "jw_org_precision": "When method matters doctrinally, specify 'bautismo por inmersión completa'"
            },
            
            "communion": {
                "theological_meaning": "Christian ritual remembering Christ's Last Supper",
                "es": {
                    "translation": "comunión",
                    "alternatives": {
                        "catholic": "Eucaristía (Eucharist)",
                        "protestant": "Santa Cena (Lord's Supper)",
                        "general": "comunión"
                    }
                },
                "pt": {"translation": "comunhão"},
                "fr": {"translation": "communion"},
                "denominational_terminology": {
                    "catholic": "Eucharist (Eucaristía) - literal transformation",
                    "lutheran": "Lord's Supper - real presence",
                    "reformed": "Lord's Supper - symbolic memorial",
                    "translation_note": "Terminology reveals theology - be precise"
                },
                "translation_principle": "Use denomination's preferred term when known"
            },
            
            "confession": {
                "theological_meaning": "Acknowledgment of sins; seeking forgiveness",
                "es": {
                    "translation": "confesión",
                    "catholic_specific": "sacramento de la reconciliación"
                },
                "pt": {"translation": "confissão"},
                "fr": {"translation": "confession"},
                "denominational_differences": {
                    "catholic_orthodox": "Sacrament requiring priest",
                    "protestant": "Direct to God, no intermediary",
                    "translation_note": "Same word, different practice"
                }
            },
            
            # CHURCH & MINISTRY
            "church": {
                "theological_meaning": "1) Body of believers, 2) Building for worship",
                "es": {
                    "building": "iglesia (edificio)",
                    "people": "iglesia (congregación)",
                    "universal": "Iglesia (con mayúscula - universal body of Christ)"
                },
                "pt": {"translation": "igreja"},
                "fr": {"translation": "église"},
                "capitalization_rule": {
                    "uppercase": "Iglesia - universal Church",
                    "lowercase": "iglesia - local church or building"
                },
                "jw_org_principle": "Distinguish 'Church' (universal) from 'church' (local/building)"
            },
            
            "pastor": {
                "theological_meaning": "Spiritual leader/shepherd of congregation",
                "es": {
                    "translation": "pastor",
                    "alternatives": {
                        "protestant": "pastor",
                        "catholic": "padre / sacerdote",
                        "pentecostal": "pastor / reverendo"
                    }
                },
                "pt": {"translation": "pastor"},
                "fr": {"translation": "pasteur"},
                "denominational_terms": "Catholic = 'padre', Protestant = 'pastor'",
                "translation_note": "Use terminology matching denomination"
            },
            
            "priest": {
                "theological_meaning": "Ordained minister authorized to perform sacraments",
                "es": {
                    "translation": "sacerdote",
                    "informal": "padre (Father)"
                },
                "pt": {"translation": "sacerdote"},
                "fr": {"translation": "prêtre"},
                "denominational_usage": {
                    "catholic_orthodox": "sacerdote",
                    "protestant": "Generally don't use this term",
                    "high_anglican": "priest/sacerdote"
                }
            },
            
            "worship": {
                "theological_meaning": "Reverent honor and devotion to God",
                "es": {
                    "translation": "adoración",
                    "vs_veneration": "adoración (worship - only to God) vs. veneración (veneration - to saints)"
                },
                "pt": {"translation": "adoração"},
                "fr": {"translation": "adoration"},
                "theological_distinction": {
                    "catholic": "Worship (adoración) to God only; veneration (veneración) to saints",
                    "protestant": "Worship to God alone",
                    "translation_note": "Critical distinction in Catholic theology"
                },
                "jw_org_precision": "Never confuse adoración with veneración"
            },
            
            # SCRIPTURE & REVELATION
            "Bible": {
                "theological_meaning": "Sacred scriptures of Christianity",
                "es": {
                    "translation": "Biblia",
                    "capitalization": "Always capitalized"
                },
                "pt": {"translation": "Bíblia"},
                "fr": {"translation": "Bible"},
                "denominational_differences": {
                    "protestant": "66 books",
                    "catholic": "73 books (includes Deuterocanonical/Apocrypha)",
                    "orthodox": "Varies by tradition",
                    "translation_note": "Canon differs; term is consistent"
                }
            },
            
            "gospel": {
                "theological_meaning": "1) Good news of salvation, 2) First four books of New Testament",
                "es": {
                    "good_news": "evangelio (buenas nuevas)",
                    "book": "Evangelio de [Mateo/Marcos/Lucas/Juan]",
                    "capitalization": "Evangelio (book) vs. evangelio (message)"
                },
                "pt": {"translation": "evangelho"},
                "fr": {"translation": "évangile"},
                "jw_org_capitalization": "Capitalize when referring to books; lowercase for 'good news'"
            },
            
            "revelation": {
                "theological_meaning": "God's disclosure of truth to humanity",
                "es": {
                    "concept": "revelación",
                    "book": "Apocalipsis / Revelación (book of Bible)"
                },
                "pt": {"translation": "revelação"},
                "fr": {"translation": "révélation"},
                "translation_note": "In Spanish, the book is often called 'Apocalipsis' rather than 'Revelación'"
            },
            
            # ESCHATOLOGY (END TIMES)
            "heaven": {
                "theological_meaning": "Eternal dwelling place with God",
                "es": {
                    "translation": "cielo",
                    "capitalization": "Cielo (Heaven) vs. cielo (sky)"
                },
                "pt": {"translation": "céu"},
                "fr": {"translation": "ciel / paradis"},
                "jw_org_principle": "Capitalize when referring to spiritual dwelling place"
            },
            
            "hell": {
                "theological_meaning": "Place/state of eternal punishment or separation from God",
                "es": {
                    "translation": "infierno",
                    "theological_variants": {
                        "gehenna": "Gehena (final punishment)",
                        "hades": "Hades (grave/underworld)",
                        "sheol": "Seol (Hebrew concept)"
                    }
                },
                "pt": {"translation": "inferno"},
                "fr": {"translation": "enfer"},
                "jw_org_precision": "Distinguish Gehenna (final punishment) from Hades (grave) when context requires",
                "denominational_note": "Some denominations reject literal hell"
            },
            
            "rapture": {
                "theological_meaning": "Belief that Christians will be taken to heaven before tribulation",
                "es": {
                    "translation": "arrebatamiento",
                    "alternative": "rapto (also used)"
                },
                "pt": {"translation": "arrebatamento"},
                "fr": {"translation": "enlèvement"},
                "denominational_differences": {
                    "evangelical_fundamentalist": "Core belief",
                    "catholic_orthodox_mainline": "Generally not taught",
                    "translation_note": "Not universally accepted doctrine"
                },
                "sensitivity_note": "Some denominations don't believe in rapture - translate accurately but neutrally"
            },
            
            # Add 200+ more Christian terms...
        }
    
    # ============================================================================
    # ISLAMIC TERMINOLOGY
    # ============================================================================
    
    def _load_islamic_terms(self) -> Dict[str, Dict]:
        """
        Islamic theological terms with precise translations
        """
        return {
            "Allah": {
                "theological_meaning": "God in Islam (same God as Judaism/Christianity in Islamic belief)",
                "es": {
                    "translation": "Alá",
                    "notes": "Keep Arabic name, Spanish phonetic spelling"
                },
                "pt": {"translation": "Alá"},
                "fr": {"translation": "Allah"},
                "translation_principle": "Keep Arabic name 'Allah' in most languages; it's a proper name, not generic 'god'",
                "cultural_note": "Arabic Christians also use 'Allah' for God"
            },
            
            "Quran / Koran": {
                "theological_meaning": "Holy book of Islam, believed to be word of Allah revealed to Muhammad",
                "es": {
                    "translation": "Corán",
                    "alternative": "Alcorán (older spelling)",
                    "capitalization": "Always capitalized"
                },
                "pt": {"translation": "Alcorão"},
                "fr": {"translation": "Coran"},
                "reverence_note": "Always capitalize and handle with respect in translation"
            },
            
            "Muhammad / Mohammed": {
                "theological_meaning": "Final prophet of Islam",
                "es": {
                    "translation": "Mahoma",
                    "alternative": "Muhammad (transliterated)"
                },
                "pt": {"translation": "Maomé"},
                "fr": {"translation": "Mahomet"},
                "reverence_phrase": {
                    "arabic": "صلى الله عليه وسلم (peace be upon him)",
                    "es": "la paz sea con él",
                    "abbreviation": "PBUH"
                },
                "translation_note": "Muslims traditionally add 'peace be upon him' after the Prophet's name"
            },
            
            "salah / salat": {
                "theological_meaning": "Islamic ritual prayer (5 times daily)",
                "es": {
                    "translation": "salat",
                    "explanation": "oración ritual islámica"
                },
                "pt": {"translation": "salat"},
                "fr": {"translation": "salat"},
                "translation_principle": "Keep Arabic term 'salat'; it's specific to Islamic prayer ritual"
            },
            
            "hajj": {
                "theological_meaning": "Pilgrimage to Mecca; one of Five Pillars of Islam",
                "es": {
                    "translation": "hajj / hach",
                    "explanation": "peregrinación a La Meca"
                },
                "pt": {"translation": "hajj"},
                "fr": {"translation": "hajj"},
                "translation_note": "Keep Arabic term; add explanation if needed"
            },
            
            "jihad": {
                "theological_meaning": "Struggle/striving in the way of Allah (often spiritual struggle, not just military)",
                "es": {
                    "translation": "yihad",
                    "full_meaning": "esfuerzo en el camino de Alá"
                },
                "pt": {"translation": "jihad"},
                "fr": {"translation": "djihad"},
                "sensitivity_note": "Primary meaning is spiritual struggle, not 'holy war' (Western misunderstanding)",
                "translation_principle": "Translate accurately; don't reinforce misconceptions"
            },
            
            "imam": {
                "theological_meaning": "Islamic religious leader; prayer leader",
                "es": {
                    "translation": "imán",
                    "notes": "NOT to be confused with 'imán' (magnet)"
                },
                "pt": {"translation": "imã"},
                "fr": {"translation": "imam"}
            },
            
            "mosque": {
                "theological_meaning": "Islamic house of worship",
                "es": {
                    "translation": "mezquita"
                },
                "pt": {"translation": "mesquita"},
                "fr": {"translation": "mosquée"},
                "arabic_term": "masjid"
            },
            
            "Ramadan": {
                "theological_meaning": "Islamic holy month of fasting",
                "es": {
                    "translation": "Ramadán",
                    "capitalization": "Always capitalized"
                },
                "pt": {"translation": "Ramadã"},
                "fr": {"translation": "Ramadan"},
                "cultural_context": "Month of fasting from dawn to sunset; one of Five Pillars"
            },
            
            # Add 100+ more Islamic terms...
        }
    
    # ============================================================================
    # JEWISH TERMINOLOGY
    # ============================================================================
    
    def _load_jewish_terms(self) -> Dict[str, Dict]:
        """
        Jewish theological terms with precise translations
        """
        return {
            "Torah": {
                "theological_meaning": "First five books of Hebrew Bible; Jewish law and teaching",
                "es": {
                    "translation": "Torá",
                    "keep_hebrew": "Keep Hebrew name",
                    "capitalization": "Always capitalized"
                },
                "pt": {"translation": "Torá"},
                "fr": {"translation": "Torah"},
                "reverence_note": "Sacred text; handle with respect in translation"
            },
            
            "rabbi": {
                "theological_meaning": "Jewish religious teacher and leader",
                "es": {
                    "translation": "rabino",
                    "feminine": "rabina (female rabbi, Reform/Conservative Judaism)"
                },
                "pt": {"translation": "rabino"},
                "fr": {"translation": "rabbin"}
            },
            
            "synagogue": {
                "theological_meaning": "Jewish house of worship and study",
                "es": {
                    "translation": "sinagoga"
                },
                "pt": {"translation": "sinagoga"},
                "fr": {"translation": "synagogue"},
                "hebrew_term": "beit knesset"
            },
            
            "kosher": {
                "theological_meaning": "Food permissible under Jewish dietary laws",
                "es": {
                    "translation": "kosher / casher",
                    "explanation": "permitido según las leyes dietéticas judías"
                },
                "pt": {"translation": "kosher"},
                "fr": {"translation": "casher / kosher"}
            },
            
            "Sabbath / Shabbat": {
                "theological_meaning": "Jewish day of rest (Friday evening to Saturday evening)",
                "es": {
                    "translation": "Sabbat / Shabat",
                    "alternative": "día de reposo"
                },
                "pt": {"translation": "Shabat"},
                "fr": {"translation": "Shabbat / Sabbat"},
                "time": "From Friday sunset to Saturday sunset"
            },
            
            "bar mitzvah": {
                "theological_meaning": "Jewish coming-of-age ceremony for boys at 13",
                "es": {
                    "translation": "bar mitzvá",
                    "keep_hebrew": "Keep Hebrew term",
                    "explanation": "ceremonia de mayoría de edad judía"
                },
                "pt": {"translation": "bar mitzvá"},
                "fr": {"translation": "bar-mitsva"},
                "female_equivalent": "bat mitzvah (girls at 12-13)"
            },
            
            # Add 100+ more Jewish terms...
        }
    
    # ============================================================================
    # HINDU & BUDDHIST TERMINOLOGY
    # ============================================================================
    
    def _load_hindu_terms(self) -> Dict[str, Dict]:
        """Hindu theological terms"""
        return {
            "karma": {
                "theological_meaning": "Law of cause and effect; actions determine future",
                "es": {"translation": "karma"},
                "pt": {"translation": "carma"},
                "fr": {"translation": "karma"},
                "translation_note": "Keep Sanskrit term; widely understood"
            },
            
            "dharma": {
                "theological_meaning": "Cosmic law and order; duty, righteousness",
                "es": {"translation": "dharma"},
                "pt": {"translation": "darma"},
                "fr": {"translation": "dharma"},
                "translation_note": "Complex concept; keep Sanskrit term"
            },
            
            # Add 50+ more Hindu terms...
        }
    
    def _load_buddhist_terms(self) -> Dict[str, Dict]:
        """Buddhist theological terms"""
        return {
            "Buddha": {
                "theological_meaning": "The Enlightened One; Siddhartha Gautama",
                "es": {"translation": "Buda"},
                "pt": {"translation": "Buda"},
                "fr": {"translation": "Bouddha"}
            },
            
            "nirvana": {
                "theological_meaning": "State of liberation from suffering and rebirth cycle",
                "es": {"translation": "nirvana"},
                "pt": {"translation": "nirvana"},
                "fr": {"translation": "nirvana"}
            },
            
            # Add 50+ more Buddhist terms...
        }
    
    # ============================================================================
    # SHARED TERMS (Cross-Religious)
    # ============================================================================
    
    def _load_shared_terms(self) -> Dict[str, Dict]:
        """
        Terms shared across multiple religions
        """
        return {
            "prayer": {
                "general_meaning": "Communication with the divine",
                "es": {"translation": "oración"},
                "religious_specific": {
                    "christian": "oración",
                    "islamic": "salat (ritual prayer), dua (supplication)",
                    "jewish": "tefilá",
                    "hindu": "puja"
                },
                "translation_note": "Generic term works, but some religions have specific prayer types"
            },
            
            "prophet": {
                "general_meaning": "One who speaks for God/divine",
                "es": {"translation": "profeta"},
                "religious_usage": {
                    "christian": "prophet - Old Testament figures",
                    "islamic": "prophet - includes Muhammad (final prophet)",
                    "jewish": "prophet - navi"
                }
            },
            
            # Add 30+ more shared terms...
        }
    
    # ============================================================================
    # TRANSLATION METHODS
    # ============================================================================
    
    def translate_religious_term(self, term: str, source_lang: str = 'en',
                                 target_lang: str = 'es',
                                 religion: str = None,
                                 denomination: str = None) -> Optional[Dict]:
        """
        Translate religious term with theological precision
        
        Args:
            term: Religious term to translate
            source_lang: Source language
            target_lang: Target language
            religion: Optional religion context (christian, islamic, jewish, etc.)
            denomination: Optional denomination (catholic, protestant, sunni, etc.)
        
        Returns:
            Theologically accurate translation with notes
        """
        term_lower = term.lower().strip()
        
        # Search in appropriate database
        databases = []
        
        if religion:
            if religion == 'christian':
                databases.append(('christian', self.christian_terms))
            elif religion == 'islamic':
                databases.append(('islamic', self.islamic_terms))
            elif religion == 'jewish':
                databases.append(('jewish', self.jewish_terms))
            elif religion == 'hindu':
                databases.append(('hindu', self.hindu_terms))
            elif religion == 'buddhist':
                databases.append(('buddhist', self.buddhist_terms))
        else:
            # Search all databases
            databases = [
                ('christian', self.christian_terms),
                ('islamic', self.islamic_terms),
                ('jewish', self.jewish_terms),
                ('hindu', self.hindu_terms),
                ('buddhist', self.buddhist_terms)
            ]
        
        # Search databases
        for db_name, database in databases:
            if term_lower in database:
                term_data = database[term_lower]
                
                if target_lang in term_data:
                    translation_data = term_data[target_lang]
                    
                    result = {
                        'original_term': term,
                        'religion': db_name,
                        'theological_meaning': term_data.get('theological_meaning', ''),
                        'translation': translation_data.get('translation', ''),
                        'alternatives': translation_data.get('alternatives', {}),
                        'notes': translation_data.get('notes', ''),
                        'reverence_note': term_data.get('reverence_note', ''),
                        'denominational_differences': term_data.get('denominational_differences', {}),
                        'jw_org_precision': term_data.get('jw_org_precision', ''),
                        'sensitivity_note': term_data.get('sensitivity_note', '')
                    }
                    
                    # Add denomination-specific info if provided
                    if denomination and 'denominational_differences' in term_data:
                        if denomination in term_data['denominational_differences']:
                            result['denomination_specific'] = term_data['denominational_differences'][denomination]
                    
                    return result
        
        return None


# ============================================================================
# GLOBAL INSTANCE
# ============================================================================
religious_terms = ReligiousTerms()

# Test examples
if __name__ == "__main__":
    print("\n" + "="*60)
    print("RELIGIOUS TERMS - THEOLOGICALLY ACCURATE TRANSLATIONS")
    print("="*60)
    
    # Test 1: Christian term
    print("\n**TEST 1: Christian Term - 'baptism'**")
    result1 = religious_terms.translate_religious_term('baptism', 'en', 'es', religion='christian')
    print(f"Term: {result1['original_term']}")
    print(f"Meaning: {result1['theological_meaning']}")
    print(f"Translation: {result1['translation']}")
    if result1['denominational_differences']:
        print(f"Denominational differences: {result1['denominational_differences']}")
    
    # Test 2: Islamic term
    print("\n**TEST 2: Islamic Term - 'Allah'**")
    result2 = religious_terms.translate_religious_term('Allah', 'en', 'es', religion='islamic')
    print(f"Term: {result2['original_term']}")
    print(f"Meaning: {result2['theological_meaning']}")
    print(f"Translation: {result2['translation']}")
    
    # Test 3: Jewish term
    print("\n**TEST 3: Jewish Term - 'Torah'**")
    result3 = religious_terms.translate_religious_term('Torah', 'en', 'es', religion='jewish')
    print(f"Term: {result3['original_term']}")
    print(f"Meaning: {result3['theological_meaning']}")
    print(f"Translation: {result3['translation']}")
    print(f"Reverence note: {result3['reverence_note']}")
    
    print("\n" + "="*60)
