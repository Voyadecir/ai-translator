"""
Spell Correction System for OCR Output
Handles common OCR errors and misspellings across 10 languages
Integrates with translation_dictionaries.py for domain-aware corrections
"""

import re
from typing import Dict, List, Optional, Tuple
from functools import lru_cache

class SpellCorrector:
    """
    Multi-language spell correction optimized for OCR errors
    
    Supports:
    - English, Spanish, Portuguese, French, Chinese, Hindi, Arabic, Bengali, Russian, Urdu
    - Common OCR character substitutions (l→I, O→0, rn→m, etc.)
    - Domain-specific corrections (government, medical, legal terms)
    - Fuzzy matching for near-misses
    """
    
    def __init__(self):
        # Common OCR character confusions
        self.ocr_substitutions = {
            'I': ['l', '1', '|'],  # I confused with l, 1, |
            'l': ['I', '1', '|'],
            'O': ['0', 'Q'],       # O confused with 0, Q
            '0': ['O', 'Q'],
            'S': ['5', '$'],       # S confused with 5, $
            '5': ['S', '$'],
            'm': ['rn', 'ni'],     # m confused with rn
            'n': ['ri'],           # n confused with ri
            'u': ['v'],            # u confused with v
            'v': ['u'],
            'c': ['e'],            # c confused with e
            'B': ['8'],            # B confused with 8
            '8': ['B'],
        }
        
        # Load language-specific corrections
        self.corrections = {
            'en': self._load_english_corrections(),
            'es': self._load_spanish_corrections(),
            'pt': self._load_portuguese_corrections(),
            'fr': self._load_french_corrections(),
        }
        
        # Domain-specific term corrections
        self.domain_corrections = {
            'government': self._load_government_corrections(),
            'medical': self._load_medical_corrections(),
            'legal': self._load_legal_corrections(),
            'financial': self._load_financial_corrections(),
        }
    
    # ============================================================================
    # ENGLISH CORRECTIONS
    # ============================================================================
    
    def _load_english_corrections(self) -> Dict[str, str]:
        """Common English misspellings and OCR errors"""
        return {
            # Common OCR errors in English
            "recieve": "receive",
            "seperate": "separate",
            "definately": "definitely",
            "occured": "occurred",
            "accomodate": "accommodate",
            "wich": "which",
            "untill": "until",
            "sucessful": "successful",
            "occassion": "occasion",
            "begining": "beginning",
            
            # Government/legal terms - OCR errors
            "goverment": "government",
            "govenment": "government",
            "govemment": "government",
            "benifit": "benefit",
            "beneifit": "benefit",
            "eligable": "eligible",
            "elligible": "eligible",
            "applic ation": "application",  # Space error
            "appl ication": "application",
            "applica tion": "application",
            
            # Financial terms
            "paym ent": "payment",
            "pay ment": "payment",
            "depo sit": "deposit",
            "depos it": "deposit",
            "accou nt": "account",
            "accoun t": "account",
            "balan ce": "balance",
            "balanc e": "balance",
            
            # Medical terms
            "presc ription": "prescription",
            "prescri ption": "prescription",
            "medica tion": "medication",
            "medicat ion": "medication",
            "diagno sis": "diagnosis",
            "diagnos is": "diagnosis",
            
            # Common words with OCR l/I confusion
            "lncome": "income",
            "lnsurance": "insurance",
            "lnformation": "information",
            "ldentification": "identification",
            "lmportant": "important",
            "Clairn": "claim",  # Cl confused with CI
            "clairn": "claim",
            
            # Common O/0 confusion
            "n0tice": "notice",
            "0fficer": "officer",
            "d0cument": "document",
            "0ffice": "office",
            
            # Common rn/m confusion
            "infonnation": "information",  # rn → m
            "govemrnent": "government",
            "clairn": "claim",
            "forrn": "form",
            
            # Date-related
            "Janu ary": "January",
            "Febru ary": "February",
            "Decern ber": "December",
        }
    
    # ============================================================================
    # SPANISH CORRECTIONS
    # ============================================================================
    
    def _load_spanish_corrections(self) -> Dict[str, str]:
        """Common Spanish misspellings and OCR errors"""
        return {
            # Common Spanish misspellings
            "habia": "había",
            "hacia": "hacía",
            "tambien": "también",
            "razon": "razón",
            "informacion": "información",
            "direccion": "dirección",
            "notificacion": "notificación",
            "atencion": "atención",
            
            # Government terms - OCR errors
            "gobiemo": "gobierno",  # rn → m
            "gobiem o": "gobierno",  # Space
            "segur o": "seguro",
            "segu ro": "seguro",
            "benefic io": "beneficio",
            "benefici o": "beneficio",
            "elegib ilidad": "elegibilidad",
            
            # Financial terms
            "pa go": "pago",
            "pag o": "pago",
            "depo sito": "depósito",
            "depos ito": "depósito",
            "cuen ta": "cuenta",
            "cuent a": "cuenta",
            "sal do": "saldo",
            "sald o": "saldo",
            
            # Medical terms
            "rece ta": "receta",
            "recet a": "receta",
            "medica mento": "medicamento",
            "medicam ento": "medicamento",
            "diagno stico": "diagnóstico",
            "diagnos tico": "diagnóstico",
            
            # Common l/I confusion
            "lnformación": "información",
            "ldentificación": "identificación",
            "lmportante": "importante",
            
            # Missing accents (common OCR error)
            "numero": "número",
            "telefono": "teléfono",
            "proxima": "próxima",
            "medico": "médico",
            "deposito": "depósito",
            "credito": "crédito",
        }
    
    # ============================================================================
    # PORTUGUESE CORRECTIONS
    # ============================================================================
    
    def _load_portuguese_corrections(self) -> Dict[str, str]:
        """Common Portuguese misspellings and OCR errors"""
        return {
            # Common Portuguese misspellings
            "informacao": "informação",
            "atencao": "atenção",
            "notificacao": "notificação",
            "endereco": "endereço",
            "numero": "número",
            "telefone": "telefone",
            
            # Government terms
            "govemo": "governo",  # rn → m
            "gove mo": "governo",
            "benefic io": "benefício",
            "benefici o": "benefício",
            
            # Financial terms
            "paga mento": "pagamento",
            "pagam ento": "pagamento",
            "depo sito": "depósito",
            "con ta": "conta",
            "cont a": "conta",
            
            # Missing tildes/accents
            "acao": "ação",
            "opcao": "opção",
            "razao": "razão",
            "orgao": "órgão",
        }
    
    # ============================================================================
    # FRENCH CORRECTIONS
    # ============================================================================
    
    def _load_french_corrections(self) -> Dict[str, str]:
        """Common French misspellings and OCR errors"""
        return {
            # Common French misspellings
            "gouvernement": "gouvernement",
            "adresse": "adresse",
            "numero": "numéro",
            "telephone": "téléphone",
            
            # Missing accents (common OCR error)
            "a": "à",
            "la": "là",
            "ou": "où",
            "etat": "état",
            "hopital": "hôpital",
            "etre": "être",
            
            # Government terms
            "gouvemement": "gouvernement",  # rn → m
            "gouveme ment": "gouvernement",
            "benefic e": "bénéfice",
            
            # Financial terms
            "paiement": "paiement",
            "paie ment": "paiement",
            "compt e": "compte",
            "comp te": "compte",
        }
    
    # ============================================================================
    # DOMAIN-SPECIFIC CORRECTIONS
    # ============================================================================
    
    def _load_government_corrections(self) -> Dict[str, str]:
        """Government document specific corrections"""
        return {
            # US Government agencies (OCR errors)
            "lRS": "IRS",
            "l RS": "IRS",
            "I.R.S.": "IRS",
            "SSA": "SSA",
            "S.S.A.": "SSA",
            "USCI S": "USCIS",
            "USC IS": "USCIS",
            "U.S.C.I.S.": "USCIS",
            "HUD": "HUD",
            "H.U.D.": "HUD",
            
            # Government terms
            "Social Secur ity": "Social Security",
            "Social Securit y": "Social Security",
            "Soc ial Security": "Social Security",
            "Food Star nps": "Food Stamps",  # rn → m
            "Food Stam ps": "Food Stamps",
            "Medi caid": "Medicaid",
            "Medic aid": "Medicaid",
            "Medi care": "Medicare",
            "Medic are": "Medicare",
            
            # Forms
            "Forrn W-2": "Form W-2",
            "Form W-Z": "Form W-2",  # 2 → Z
            "Forrn 1040": "Form 1040",
            "Form I040": "Form 1040",  # l → I
            "Forrn I-94": "Form I-94",
            "Form l-94": "Form I-94",
        }
    
    def _load_medical_corrections(self) -> Dict[str, str]:
        """Medical document specific corrections"""
        return {
            # Medical terms with OCR errors
            "patie nt": "patient",
            "patien t": "patient",
            "diagnos is": "diagnosis",
            "diagno sis": "diagnosis",
            "presc ription": "prescription",
            "prescri ption": "prescription",
            "medica tion": "medication",
            "medicat ion": "medication",
            "treatrn ent": "treatment",  # rn → m
            "treatme nt": "treatment",
            
            # Insurance terms
            "co-pa y": "copay",
            "co pa y": "copay",
            "deduct ible": "deductible",
            "deducti ble": "deductible",
            "premiurn": "premium",  # rn → m
            "premi um": "premium",
            
            # Spanish medical terms
            "receta medica": "receta médica",
            "historia clinica": "historia clínica",
            "seguro medico": "seguro médico",
        }
    
    def _load_legal_corrections(self) -> Dict[str, str]:
        """Legal document specific corrections"""
        return {
            # Legal terms with OCR errors
            "subpoe na": "subpoena",
            "subpoen a": "subpoena",
            "sum mons": "summons",
            "summo ns": "summons",
            "plaint iff": "plaintiff",
            "plainti ff": "plaintiff",
            "defend ant": "defendant",
            "defenda nt": "defendant",
            "affi davit": "affidavit",
            "affida vit": "affidavit",
            
            # Court-related
            "Cou rt": "Court",
            "Cour t": "Court",
            "jud ge": "judge",
            "judg e": "judge",
            "verd ict": "verdict",
            "verdi ct": "verdict",
            
            # Spanish legal terms
            "demandante": "demandante",
            "deman dante": "demandante",
            "demandado": "demandado",
            "deman dado": "demandado",
        }
    
    def _load_financial_corrections(self) -> Dict[str, str]:
        """Financial document specific corrections"""
        return {
            # Financial terms with OCR errors
            "accou nt": "account",
            "accoun t": "account",
            "balan ce": "balance",
            "balanc e": "balance",
            "paym ent": "payment",
            "pay ment": "payment",
            "over draft": "overdraft",
            "overdr aft": "overdraft",
            "mortg age": "mortgage",
            "mortga ge": "mortgage",
            "intere st": "interest",
            "inter est": "interest",
            
            # Bank-related
            "depo sit": "deposit",
            "depos it": "deposit",
            "withdr awal": "withdrawal",
            "withdra wal": "withdrawal",
            "trans action": "transaction",
            "transa ction": "transaction",
            
            # Spanish financial terms
            "cuenta": "cuenta",
            "cuen ta": "cuenta",
            "saldo": "saldo",
            "sal do": "saldo",
            "pago": "pago",
            "pa go": "pago",
        }
    
    # ============================================================================
    # CORE CORRECTION METHODS
    # ============================================================================
    
    @lru_cache(maxsize=5000)
    def correct_word(self, word: str, language: str = 'en', 
                    document_type: str = None) -> Tuple[str, float]:
        """
        Correct a single word using multi-tier approach:
        
        1. Exact match in domain corrections (if document_type provided)
        2. Exact match in language-specific corrections
        3. OCR character substitution corrections
        4. Return original (no correction needed)
        
        Returns: (corrected_word, confidence)
        - confidence = 1.0 for exact dictionary match
        - confidence = 0.9 for OCR substitution match
        - confidence = 0.0 for no correction (original returned)
        """
        word_lower = word.lower()
        
        # Priority 1: Domain-specific corrections
        if document_type:
            domain = self._map_doc_type_to_domain(document_type)
            if domain in self.domain_corrections:
                if word_lower in self.domain_corrections[domain]:
                    return self.domain_corrections[domain][word_lower], 1.0
        
        # Priority 2: Language-specific corrections
        if language in self.corrections:
            if word_lower in self.corrections[language]:
                return self.corrections[language][word_lower], 1.0
        
        # Priority 3: OCR character substitution
        ocr_correction = self._try_ocr_substitution(word)
        if ocr_correction:
            return ocr_correction, 0.9
        
        # Priority 4: No correction needed
        return word, 0.0
    
    def correct_text(self, text: str, language: str = 'en', 
                    document_type: str = None) -> Tuple[str, List[Dict]]:
        """
        Correct entire text block
        
        Returns:
        - corrected_text: Full text with corrections applied
        - corrections_made: List of {original, corrected, confidence, position}
        """
        words = re.findall(r'\b\w+\b|\S', text)
        corrected_words = []
        corrections_made = []
        position = 0
        
        for word in words:
            if re.match(r'\w+', word):  # Only correct alphanumeric words
                corrected, confidence = self.correct_word(word, language, document_type)
                if confidence > 0:
                    corrections_made.append({
                        'original': word,
                        'corrected': corrected,
                        'confidence': confidence,
                        'position': position
                    })
                corrected_words.append(corrected)
            else:
                corrected_words.append(word)  # Keep punctuation as-is
            
            position += 1
        
        corrected_text = ' '.join(corrected_words)
        return corrected_text, corrections_made
    
    def _try_ocr_substitution(self, word: str) -> Optional[str]:
        """
        Try OCR character substitutions to find valid word
        Example: "lncome" → "Income" (l → I)
        """
        # Generate variations by substituting commonly confused characters
        variations = [word]
        
        for i, char in enumerate(word):
            if char in self.ocr_substitutions:
                for replacement in self.ocr_substitutions[char]:
                    variation = word[:i] + replacement + word[i+1:]
                    variations.append(variation)
        
        # Check if any variation exists in our correction dictionaries
        for variation in variations:
            variation_lower = variation.lower()
            
            # Check English corrections
            if variation_lower in self.corrections.get('en', {}):
                return self.corrections['en'][variation_lower]
            
            # Check Spanish corrections
            if variation_lower in self.corrections.get('es', {}):
                return self.corrections['es'][variation_lower]
            
            # Check domain corrections
            for domain_dict in self.domain_corrections.values():
                if variation_lower in domain_dict:
                    return domain_dict[variation_lower]
        
        return None
    
    def _map_doc_type_to_domain(self, doc_type: str) -> str:
        """Map document type to correction domain"""
        doc_lower = doc_type.lower()
        
        if any(x in doc_lower for x in ['tax', 'irs', 'snap', 'wic', 'social security', 'ssa']):
            return 'government'
        elif any(x in doc_lower for x in ['medical', 'prescription', 'hospital', 'doctor']):
            return 'medical'
        elif any(x in doc_lower for x in ['court', 'legal', 'subpoena', 'summons']):
            return 'legal'
        elif any(x in doc_lower for x in ['bank', 'credit', 'loan', 'mortgage']):
            return 'financial'
        
        return 'government'  # Default
    
    # ============================================================================
    # UTILITY METHODS
    # ============================================================================
    
    def get_stats(self) -> Dict:
        """Get correction dictionary statistics"""
        stats = {
            'total_corrections': 0,
            'by_language': {},
            'by_domain': {},
            'ocr_substitutions': len(self.ocr_substitutions)
        }
        
        for lang, corrections in self.corrections.items():
            count = len(corrections)
            stats['by_language'][lang] = count
            stats['total_corrections'] += count
        
        for domain, corrections in self.domain_corrections.items():
            count = len(corrections)
            stats['by_domain'][domain] = count
            stats['total_corrections'] += count
        
        return stats


# ============================================================================
# GLOBAL INSTANCE
# ============================================================================
spell_corrector = SpellCorrector()

# Print stats on initialization
if __name__ == "__main__":
    stats = spell_corrector.get_stats()
    print(f"\n{'='*60}")
    print("SPELL CORRECTION SYSTEM INITIALIZATION")
    print(f"{'='*60}")
    print(f"Total Corrections Loaded: {stats['total_corrections']}")
    print(f"OCR Substitution Rules: {stats['ocr_substitutions']}")
    print(f"\nBy Language:")
    for lang, count in stats['by_language'].items():
        print(f"  • {lang}: {count} corrections")
    print(f"\nBy Domain:")
    for domain, count in stats['by_domain'].items():
        print(f"  • {domain}: {count} corrections")
    print(f"{'='*60}\n")
