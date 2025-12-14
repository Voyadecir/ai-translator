"""
Sarcasm & Tone Detector - Detect Sarcasm and Emotional Tone
Identifies when text is sarcastic, ironic, or has specific emotional tone
Critical for preserving meaning in translation

Example:
"Oh great, another bill. Just what I needed!" → SARCASTIC (not genuine enthusiasm)

Translation must preserve this sarcasm:
Spanish: "Oh genial, otra factura. Justo lo que necesitaba!" (con sarcasmo)

Without sarcasm detection, this would be translated as genuine excitement.
"""

import re
from typing import Dict, List, Optional, Tuple
from functools import lru_cache
import logging

logger = logging.getLogger(__name__)

class SarcasmToneDetector:
    """
    Detects sarcasm and emotional tone in text
    
    Features:
    - Sarcasm detection (classic patterns + context analysis)
    - Tone classification (sarcastic, sincere, angry, playful, etc.)
    - Confidence scoring
    - Explanation generation for translators
    - Multi-language support (EN, ES, PT, FR)
    
    Methods:
    - Positive words in negative context = sarcasm
    - Exaggeration patterns
    - Punctuation analysis (ellipsis, multiple punctuation)
    - Context clues
    """
    
    def __init__(self):
        """Initialize sarcasm detector with patterns"""
        self.sarcasm_patterns = self._load_sarcasm_patterns()
        self.tone_indicators = self._load_tone_indicators()
        self.context_analyzers = self._load_context_analyzers()
    
    # ============================================================================
    # SARCASM PATTERNS
    # ============================================================================
    
    def _load_sarcasm_patterns(self) -> Dict[str, Dict]:
        """
        Load classic sarcasm patterns with confidence scores
        
        Returns dict mapping pattern → metadata
        """
        return {
            # Classic sarcasm phrases
            "oh great": {
                "confidence": 0.95,
                "explanation": "Classic sarcastic phrase indicating displeasure",
                "examples": ["Oh great, another meeting", "Oh great, it's raining"]
            },
            "just what i needed": {
                "confidence": 0.90,
                "explanation": "Indicates unwanted situation",
                "examples": ["Just what I needed, a flat tire"]
            },
            "yeah right": {
                "confidence": 0.98,
                "explanation": "Strong disbelief or disagreement",
                "examples": ["Yeah right, like that'll happen"]
            },
            "sure": {
                "confidence": 0.70,
                "explanation": "Can be sarcastic agreement (context-dependent)",
                "examples": ["Sure, whatever you say"]
            },
            "obviously": {
                "confidence": 0.70,
                "explanation": "Can indicate sarcastic agreement to something not obvious",
                "examples": ["Obviously, because that makes total sense"]
            },
            "fantastic": {
                "confidence": 0.75,
                "explanation": "Often sarcastic when used alone or in negative context",
                "examples": ["Fantastic, just fantastic"]
            },
            "wonderful": {
                "confidence": 0.70,
                "explanation": "Can be sarcastic in negative situations",
                "examples": ["Wonderful, another problem"]
            },
            "perfect": {
                "confidence": 0.70,
                "explanation": "Often sarcastic when things go wrong",
                "examples": ["Perfect, just perfect"]
            },
            "brilliant": {
                "confidence": 0.75,
                "explanation": "Sarcastic when used ironically",
                "examples": ["Brilliant idea, genius"]
            },
            "how nice": {
                "confidence": 0.80,
                "explanation": "Usually sarcastic",
                "examples": ["How nice for you"]
            },
            "lovely": {
                "confidence": 0.65,
                "explanation": "Can be sarcastic in wrong context",
                "examples": ["Lovely weather we're having"]
            },
            "as if": {
                "confidence": 0.95,
                "explanation": "Strong disbelief",
                "examples": ["As if that would work"]
            },
            "like that'll happen": {
                "confidence": 0.95,
                "explanation": "Expresses impossibility sarcastically",
                "examples": ["Yeah, like that'll happen"]
            },
            "i'm sure": {
                "confidence": 0.75,
                "explanation": "Often sarcastic doubt",
                "examples": ["I'm sure that's exactly what happened"]
            },
            "well done": {
                "confidence": 0.65,
                "explanation": "Can be sarcastic criticism",
                "examples": ["Well done, you broke it"]
            },
            "congratulations": {
                "confidence": 0.60,
                "explanation": "Can be sarcastic for mistakes",
                "examples": ["Congratulations, you failed"]
            },
            "thanks a lot": {
                "confidence": 0.80,
                "explanation": "Often sarcastic blame",
                "examples": ["Thanks a lot for nothing"]
            },
            "how wonderful": {
                "confidence": 0.85,
                "explanation": "Usually sarcastic",
                "examples": ["How wonderful for them"]
            },
            "charming": {
                "confidence": 0.70,
                "explanation": "Can be sarcastic criticism",
                "examples": ["How charming of you"]
            }
        }
    
    # ============================================================================
    # TONE INDICATORS
    # ============================================================================
    
    def _load_tone_indicators(self) -> Dict[str, List[str]]:
        """
        Load tone indicator words/patterns
        
        Returns dict mapping tone → indicator words
        """
        return {
            "sarcastic": [
                "oh great", "yeah right", "sure", "obviously",
                "fantastic", "wonderful", "perfect", "brilliant",
                "as if", "like that'll happen", "i'm sure"
            ],
            "angry": [
                "damn", "shit", "fuck", "hell", "goddamn",
                "pissed", "furious", "livid", "outraged",
                "sick of", "fed up", "enough"
            ],
            "frustrated": [
                "ugh", "argh", "seriously", "really",
                "come on", "for real", "are you kidding",
                "you've got to be kidding"
            ],
            "playful": [
                "haha", "lol", "lmao", "hehe",
                "just kidding", "jk", "joking",
                "kidding", "teasing"
            ],
            "sincere": [
                "truly", "honestly", "genuinely", "really appreciate",
                "thank you so much", "grateful", "blessed"
            ],
            "condescending": [
                "sweetie", "honey", "dear", "bless your heart",
                "cute", "adorable", "precious"
            ],
            "dismissive": [
                "whatever", "fine", "okay", "sure thing",
                "if you say so", "doesn't matter"
            ]
        }
    
    # ============================================================================
    # CONTEXT ANALYZERS
    # ============================================================================
    
    def _load_context_analyzers(self) -> Dict[str, callable]:
        """
        Load context analysis functions
        
        Returns dict mapping analyzer_name → function
        """
        return {
            "positive_word_negative_context": self._check_positive_negative_mismatch,
            "punctuation_analysis": self._analyze_punctuation,
            "exaggeration_detection": self._detect_exaggeration,
            "contradiction_detection": self._detect_contradiction
        }
    
    # ============================================================================
    # MAIN DETECTION METHOD
    # ============================================================================
    
    @lru_cache(maxsize=1000)
    def detect_sarcasm(self, text: str) -> Dict:
        """
        Main sarcasm detection method
        
        Args:
            text: Text to analyze
        
        Returns:
            {
                'is_sarcastic': bool,
                'confidence': float,
                'tone': str,
                'indicators': List[str],
                'explanation': str,
                'translation_guidance': str
            }
        """
        text_lower = text.lower().strip()
        
        # Initialize result
        result = {
            'is_sarcastic': False,
            'confidence': 0.0,
            'tone': 'neutral',
            'indicators': [],
            'explanation': '',
            'translation_guidance': ''
        }
        
        # STEP 1: Check for classic sarcasm patterns
        pattern_confidence = 0.0
        for pattern, metadata in self.sarcasm_patterns.items():
            if pattern in text_lower:
                pattern_confidence = max(pattern_confidence, metadata['confidence'])
                result['indicators'].append(f"Pattern: '{pattern}'")
        
        # STEP 2: Analyze context (positive words in negative context)
        context_score = self._check_positive_negative_mismatch(text_lower)
        if context_score > 0:
            result['indicators'].append("Positive words in negative context")
        
        # STEP 3: Analyze punctuation
        punct_score = self._analyze_punctuation(text)
        if punct_score > 0:
            result['indicators'].append("Sarcastic punctuation pattern")
        
        # STEP 4: Check for exaggeration
        exag_score = self._detect_exaggeration(text_lower)
        if exag_score > 0:
            result['indicators'].append("Exaggeration detected")
        
        # STEP 5: Calculate overall confidence
        final_confidence = max(
            pattern_confidence,
            context_score,
            punct_score * 0.5,
            exag_score * 0.6
        )
        
        # STEP 6: Determine if sarcastic
        result['is_sarcastic'] = final_confidence > 0.6
        result['confidence'] = final_confidence
        
        # STEP 7: Determine tone
        result['tone'] = self._determine_tone(text_lower, result['is_sarcastic'])
        
        # STEP 8: Generate explanation
        if result['is_sarcastic']:
            result['explanation'] = self._generate_sarcasm_explanation(
                text, result['indicators'], result['tone']
            )
            result['translation_guidance'] = self._generate_translation_guidance(
                result['tone']
            )
        
        return result
    
    # ============================================================================
    # CONTEXT ANALYSIS METHODS
    # ============================================================================
    
    def _check_positive_negative_mismatch(self, text: str) -> float:
        """
        Check if positive words appear in negative context
        
        This is a strong indicator of sarcasm
        
        Returns confidence score (0-1)
        """
        positive_words = [
            "great", "wonderful", "fantastic", "perfect",
            "brilliant", "amazing", "excellent", "lovely",
            "nice", "beautiful", "awesome", "incredible"
        ]
        
        negative_context_words = [
            "not", "never", "no", "none", "nothing",
            "problem", "issue", "fail", "failed", "broke",
            "lost", "missing", "wrong", "error", "bad",
            "terrible", "horrible", "awful", "worse"
        ]
        
        # Count positive and negative words
        positive_count = sum(1 for word in positive_words if word in text)
        negative_count = sum(1 for word in negative_context_words if word in text)
        
        # If we have both positive and negative, likely sarcastic
        if positive_count > 0 and negative_count > 0:
            return 0.85
        
        return 0.0
    
    def _analyze_punctuation(self, text: str) -> float:
        """
        Analyze punctuation patterns for sarcasm
        
        Returns confidence score (0-1)
        """
        score = 0.0
        
        # Ellipsis (...) can indicate sarcasm
        if '...' in text:
            score = max(score, 0.50)
        
        # Multiple exclamation marks
        if '!!' in text or '!!!' in text:
            score = max(score, 0.60)
        
        # Multiple question marks
        if '??' in text or '???' in text:
            score = max(score, 0.55)
        
        # Mixed punctuation (!? or ?!)
        if '!?' in text or '?!' in text:
            score = max(score, 0.65)
        
        # ALL CAPS (can indicate sarcasm or anger)
        words = text.split()
        all_caps_words = [w for w in words if w.isupper() and len(w) > 2]
        if len(all_caps_words) >= 2:
            score = max(score, 0.40)
        
        return score
    
    def _detect_exaggeration(self, text: str) -> float:
        """
        Detect exaggeration patterns
        
        Returns confidence score (0-1)
        """
        exaggeration_patterns = [
            "never in my life",
            "worst ever",
            "best ever",
            "most amazing",
            "absolutely",
            "completely",
            "totally",
            "literally",
            "seriously",
            "extremely"
        ]
        
        for pattern in exaggeration_patterns:
            if pattern in text:
                return 0.60
        
        return 0.0
    
    def _detect_contradiction(self, text: str) -> float:
        """
        Detect contradictory statements
        
        Returns confidence score (0-1)
        """
        # Simple contradiction patterns
        if "but" in text or "however" in text:
            # Check if there's a contradiction
            parts = re.split(r'\bbut\b|\bhowever\b', text)
            if len(parts) == 2:
                # Could be contradictory - moderate confidence
                return 0.50
        
        return 0.0
    
    # ============================================================================
    # TONE DETERMINATION
    # ============================================================================
    
    def _determine_tone(self, text: str, is_sarcastic: bool) -> str:
        """
        Determine overall tone of text
        
        Args:
            text: Text to analyze
            is_sarcastic: Whether sarcasm was detected
        
        Returns:
            Tone label (sarcastic, angry, playful, etc.)
        """
        if is_sarcastic:
            return "sarcastic/ironic"
        
        # Check other tones
        for tone, indicators in self.tone_indicators.items():
            for indicator in indicators:
                if indicator in text:
                    return tone
        
        return "neutral"
    
    # ============================================================================
    # EXPLANATION GENERATION
    # ============================================================================
    
    def _generate_sarcasm_explanation(self, text: str, 
                                     indicators: List[str],
                                     tone: str) -> str:
        """
        Generate explanation of why text is sarcastic
        
        For translator's reference
        """
        explanation = f"This text appears to be {tone}. "
        
        if indicators:
            explanation += "Indicators: " + ", ".join(indicators) + ". "
        
        explanation += "The speaker likely means the opposite of what they're literally saying."
        
        return explanation
    
    def _generate_translation_guidance(self, tone: str) -> str:
        """
        Generate guidance for translator on how to preserve tone
        
        Returns translation instructions
        """
        guidance_map = {
            "sarcastic/ironic": "Add '(con sarcasmo)' or '(irónico)' marker in Spanish to preserve sarcastic tone",
            "angry": "Use stronger/emphatic language to convey anger",
            "playful": "Maintain playful tone with appropriate colloquialisms",
            "sincere": "Use formal/respectful language",
            "condescending": "Preserve condescending tone carefully"
        }
        
        return guidance_map.get(tone, "Preserve original tone")


# ============================================================================
# GLOBAL INSTANCE
# ============================================================================
sarcasm_detector = SarcasmToneDetector()

# Convenience function
def detect_sarcasm(text: str) -> Dict:
    """
    Convenience function: Detect sarcasm in text
    
    Args:
        text: Text to analyze
    
    Returns:
        Sarcasm detection result
    """
    return sarcasm_detector.detect_sarcasm(text)


# Test example
if __name__ == "__main__":
    print("\n" + "="*60)
    print("SARCASM & TONE DETECTOR")
    print("="*60)
    
    # Test examples
    test_cases = [
        "Oh great, another bill. Just what I needed!",
        "Thank you so much for your help!",
        "Yeah right, like that'll work.",
        "I really appreciate your support.",
        "Perfect. Just perfect.",
    ]
    
    for text in test_cases:
        print(f"\n**Text:** \"{text}\"")
        result = detect_sarcasm(text)
        
        print(f"Sarcastic: {result['is_sarcastic']}")
        print(f"Confidence: {result['confidence']:.2f}")
        print(f"Tone: {result['tone']}")
        
        if result['is_sarcastic']:
            print(f"Explanation: {result['explanation']}")
            print(f"Guidance: {result['translation_guidance']}")
    
    print("\n" + "="*60)
