"""
Chatbot Clarification - Interactive Disambiguation for Translation
Handles ambiguous words by asking user for clarification via chatbot

Problem: Word "run" has 50+ meanings. Which one is correct?
Solution: Ask user in their language with clear examples

Workflow:
1. Translation engine detects ambiguous word (File 3: context_handler)
2. This module generates chatbot question in target language
3. User selects correct meaning via chatbot UI
4. Translation continues with confirmed meaning

Example:
Word: "bank"
Chatbot asks (in Spanish):
"La palabra 'bank' puede significar:
1. 🏦 Banco (institución financiera) - 'I went to the bank'
2. 🏞️ Orilla (de un río) - 'sitting on the river bank'
¿Cuál es el significado correcto en tu documento?"

User clicks option 1 → Translation uses "banco"
"""

import logging
from typing import Dict, List, Optional, Tuple
from .ui_translation import ui_translator
from .context_handler import context_handler
from .merriam_webster_api import mw_api
from .rae_scraper import rae_scraper

logger = logging.getLogger(__name__)

class ChatbotClarification:
    """
    Generates interactive clarification questions for chatbot
    
    Features:
    - Detects ambiguous words
    - Generates user-friendly questions in target language
    - Provides multiple-choice options with examples
    - Supports follow-up questions
    - Tracks clarification history
    - UI-aware phrasing (uses File 17a)
    
    Integration:
    - Used by mailbills_agent.py (File 17)
    - Works with context_handler.py (File 3)
    - Uses ui_translation.py (File 17a) for chatbot text
    """
    
    def __init__(self):
        """Initialize chatbot clarification system"""
        # Track clarification sessions
        self.active_sessions = {}
        
        # Emoji icons for visual clarity
        self.category_emojis = {
            'financial': '🏦',
            'nature': '🏞️',
            'body': '❤️',
            'action': '🏃',
            'object': '📦',
            'abstract': '💭',
            'location': '📍',
            'time': '⏰',
            'food': '🍽️',
            'general': '📝'
        }
    
    # ============================================================================
    # MAIN CLARIFICATION METHODS
    # ============================================================================
    
    def generate_clarification_question(self,
                                       word: str,
                                       source_lang: str = 'en',
                                       target_lang: str = 'es',
                                       context_sentence: Optional[str] = None) -> Optional[Dict]:
        """
        Generate chatbot clarification question for ambiguous word
        
        Args:
            word: Ambiguous word (e.g., "bank", "run", "fair")
            source_lang: Source language
            target_lang: Target language for question
            context_sentence: Optional sentence containing the word
        
        Returns:
            {
                'word': str,
                'question_text': str,  # In target language
                'options': List[Dict],  # Multiple choice options
                'type': 'multiple_choice',
                'help_text': str,
                'session_id': str
            }
        """
        # Check if word is ambiguous
        if not context_handler.is_ambiguous(word, source_lang):
            return None
        
        # Get all meanings
        meanings = context_handler.get_all_meanings(word, source_lang, target_lang)
        
        if not meanings:
            logger.warning(f"No meanings found for ambiguous word: {word}")
            return None
        
        # Try to auto-detect meaning from context
        if context_sentence:
            detected = context_handler.detect_meaning_from_sentence(
                word, context_sentence, source_lang
            )
            if detected and detected['confidence'] > 0.85:
                # High confidence - no clarification needed
                logger.info(f"Auto-detected meaning for '{word}': {detected['meaning']}")
                return None
        
        # Generate question in target language
        question_text = self._generate_question_text(word, source_lang, target_lang)
        
        # Generate multiple choice options
        options = self._generate_options(word, meanings, source_lang, target_lang)
        
        # Generate help text
        help_text = self._generate_help_text(word, target_lang)
        
        # Create session ID for tracking
        import uuid
        session_id = str(uuid.uuid4())
        
        clarification = {
            'word': word,
            'question_text': question_text,
            'options': options,
            'type': 'multiple_choice',
            'help_text': help_text,
            'session_id': session_id,
            'source_lang': source_lang,
            'target_lang': target_lang,
            'context_sentence': context_sentence
        }
        
        # Store session
        self.active_sessions[session_id] = clarification
        
        return clarification
    
    def _generate_question_text(self, word: str, source_lang: str, 
                                target_lang: str) -> str:
        """
        Generate question text in target language
        
        Example (Spanish):
        "La palabra 'bank' puede significar varias cosas. ¿Cuál es el significado correcto en tu documento?"
        """
        if target_lang == 'es':
            question = f"La palabra '{word}' puede significar varias cosas.\n\n"
            question += "¿Cuál es el significado correcto en tu documento?"
        elif target_lang == 'pt':
            question = f"A palavra '{word}' pode significar várias coisas.\n\n"
            question += "Qual é o significado correto no seu documento?"
        elif target_lang == 'fr':
            question = f"Le mot '{word}' peut signifier plusieurs choses.\n\n"
            question += "Quel est le sens correct dans votre document?"
        else:
            # Fallback to English
            question = f"The word '{word}' has multiple meanings.\n\n"
            question += "Which meaning is correct in your document?"
        
        return question
    
    def _generate_options(self, word: str, meanings: List[Dict],
                         source_lang: str, target_lang: str) -> List[Dict]:
        """
        Generate multiple choice options with examples and emojis
        
        Returns list of option dicts
        """
        options = []
        
        for i, meaning in enumerate(meanings[:6], 1):  # Limit to 6 options
            # Determine category for emoji
            category = self._categorize_meaning(meaning)
            emoji = self.category_emojis.get(category, '📝')
            
            # Get translation and example
            translation = meaning.get('translation', '')
            example_source = meaning.get('example_source', '')
            example_target = meaning.get('example_target', '')
            definition = meaning.get('definition', '')
            
            # Build option text
            if target_lang == 'es':
                option_text = f"{emoji} {translation}"
                if definition:
                    option_text += f" - {definition}"
            else:
                option_text = f"{emoji} {translation}"
            
            option = {
                'id': i,
                'text': option_text,
                'emoji': emoji,
                'translation': translation,
                'definition': definition,
                'example_source': example_source,
                'example_target': example_target,
                'category': category
            }
            
            options.append(option)
        
        # Add "None of these" option
        if target_lang == 'es':
            none_text = "❓ Ninguna de estas (necesito ayuda)"
        elif target_lang == 'pt':
            none_text = "❓ Nenhuma dessas (preciso de ajuda)"
        else:
            none_text = "❓ None of these (I need help)"
        
        options.append({
            'id': len(options) + 1,
            'text': none_text,
            'emoji': '❓',
            'is_help_option': True
        })
        
        return options
    
    def _categorize_meaning(self, meaning: Dict) -> str:
        """
        Categorize meaning for emoji selection
        
        Uses keywords in definition to determine category
        """
        definition = meaning.get('definition', '').lower()
        
        # Financial terms
        if any(word in definition for word in ['bank', 'money', 'financial', 'account', 'payment']):
            return 'financial'
        
        # Nature terms
        if any(word in definition for word in ['river', 'water', 'tree', 'nature', 'plant']):
            return 'nature'
        
        # Body parts
        if any(word in definition for word in ['heart', 'body', 'organ', 'physical']):
            return 'body'
        
        # Actions
        if any(word in definition for word in ['run', 'move', 'action', 'do', 'perform']):
            return 'action'
        
        # Objects
        if any(word in definition for word in ['object', 'thing', 'item', 'device']):
            return 'object'
        
        # Time
        if any(word in definition for word in ['time', 'date', 'when', 'period']):
            return 'time'
        
        # Location
        if any(word in definition for word in ['place', 'location', 'where', 'area']):
            return 'location'
        
        # Food
        if any(word in definition for word in ['food', 'eat', 'fruit', 'meal']):
            return 'food'
        
        return 'general'
    
    def _generate_help_text(self, word: str, target_lang: str) -> str:
        """
        Generate help text explaining how to answer
        """
        if target_lang == 'es':
            help_text = f"💡 **Tip:** Lee los ejemplos para ver cómo se usa '{word}' en cada contexto."
        elif target_lang == 'pt':
            help_text = f"💡 **Dica:** Leia os exemplos para ver como '{word}' é usado em cada contexto."
        elif target_lang == 'fr':
            help_text = f"💡 **Conseil:** Lisez les exemples pour voir comment '{word}' est utilisé dans chaque contexte."
        else:
            help_text = f"💡 **Tip:** Read the examples to see how '{word}' is used in each context."
        
        return help_text
    
    # ============================================================================
    # RESPONSE PROCESSING
    # ============================================================================
    
    def process_user_response(self, session_id: str, 
                              selected_option_id: int) -> Optional[Dict]:
        """
        Process user's clarification response
        
        Args:
            session_id: Session ID from clarification
            selected_option_id: Option ID user selected (1-based)
        
        Returns:
            {
                'word': str,
                'selected_meaning': Dict,
                'translation': str,
                'confidence': float,
                'needs_followup': bool
            }
        """
        # Get session
        if session_id not in self.active_sessions:
            logger.error(f"Invalid session ID: {session_id}")
            return None
        
        session = self.active_sessions[session_id]
        options = session['options']
        
        # Validate option ID
        if selected_option_id < 1 or selected_option_id > len(options):
            logger.error(f"Invalid option ID: {selected_option_id}")
            return None
        
        selected_option = options[selected_option_id - 1]
        
        # Check if user selected "None of these"
        if selected_option.get('is_help_option'):
            return {
                'word': session['word'],
                'selected_meaning': None,
                'translation': None,
                'confidence': 0.0,
                'needs_followup': True,
                'followup_type': 'human_assistance'
            }
        
        # Process normal selection
        result = {
            'word': session['word'],
            'selected_meaning': selected_option,
            'translation': selected_option['translation'],
            'confidence': 1.0,  # User confirmed
            'needs_followup': False
        }
        
        # Clean up session
        del self.active_sessions[session_id]
        
        logger.info(f"User clarified '{session['word']}' as: {selected_option['translation']}")
        
        return result
    
    # ============================================================================
    # BATCH CLARIFICATIONS
    # ============================================================================
    
    def generate_batch_clarifications(self,
                                     ambiguous_words: List[str],
                                     source_lang: str = 'en',
                                     target_lang: str = 'es',
                                     context_text: Optional[str] = None) -> List[Dict]:
        """
        Generate clarification questions for multiple ambiguous words
        
        Args:
            ambiguous_words: List of ambiguous words found
            source_lang: Source language
            target_lang: Target language
            context_text: Full text for context detection
        
        Returns:
            List of clarification dicts
        """
        clarifications = []
        
        for word in ambiguous_words:
            # Try to find sentence containing this word
            context_sentence = None
            if context_text:
                context_sentence = self._find_sentence_with_word(word, context_text)
            
            # Generate clarification
            clarification = self.generate_clarification_question(
                word, source_lang, target_lang, context_sentence
            )
            
            if clarification:
                clarifications.append(clarification)
        
        return clarifications
    
    def _find_sentence_with_word(self, word: str, text: str) -> Optional[str]:
        """
        Find sentence in text that contains the word
        
        Returns first sentence containing the word
        """
        import re
        
        # Split into sentences (simple approach)
        sentences = re.split(r'[.!?]+', text)
        
        word_lower = word.lower()
        for sentence in sentences:
            if word_lower in sentence.lower():
                return sentence.strip()
        
        return None
    
    # ============================================================================
    # CHATBOT UI HELPERS
    # ============================================================================
    
    def format_for_chatbot_ui(self, clarification: Dict) -> str:
        """
        Format clarification as chatbot message (Markdown)
        
        Returns formatted message ready for chatbot display
        """
        msg = f"**{clarification['question_text']}**\n\n"
        
        for option in clarification['options']:
            msg += f"{option['id']}. {option['text']}\n"
            
            # Add example if available
            if option.get('example_source'):
                msg += f"   _Ejemplo: \"{option['example_source']}\"_\n"
            
            msg += "\n"
        
        msg += f"\n{clarification['help_text']}"
        
        return msg
    
    def get_active_clarifications(self) -> List[Dict]:
        """
        Get all active clarification sessions
        
        Returns list of active clarifications
        """
        return list(self.active_sessions.values())
    
    def clear_session(self, session_id: str) -> bool:
        """
        Clear/cancel a clarification session
        
        Returns True if cleared, False if session not found
        """
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
            return True
        return False


# ============================================================================
# GLOBAL INSTANCE
# ============================================================================
chatbot_clarification = ChatbotClarification()

# Convenience functions
def ask_clarification(word: str, 
                     source_lang: str = 'en',
                     target_lang: str = 'es',
                     context: Optional[str] = None) -> Optional[Dict]:
    """
    Convenience function: Generate clarification question
    
    Args:
        word: Ambiguous word
        source_lang: Source language
        target_lang: Target language for question
        context: Optional context sentence
    
    Returns:
        Clarification dict for chatbot
    """
    return chatbot_clarification.generate_clarification_question(
        word, source_lang, target_lang, context
    )

def process_answer(session_id: str, option_id: int) -> Optional[Dict]:
    """
    Convenience function: Process user's answer
    
    Args:
        session_id: Session ID from clarification
        option_id: Selected option (1-based)
    
    Returns:
        Processing result
    """
    return chatbot_clarification.process_user_response(session_id, option_id)


# Test example
if __name__ == "__main__":
    print("\n" + "="*60)
    print("CHATBOT CLARIFICATION - INTERACTIVE DISAMBIGUATION")
    print("="*60)
    
    # Test with ambiguous word "bank"
    test_word = "bank"
    test_context = "I went to the bank to deposit money"
    
    print(f"\n**Test Word:** '{test_word}'")
    print(f"**Context:** {test_context}")
    
    # Generate clarification
    clarification = ask_clarification(test_word, 'en', 'es', test_context)
    
    if clarification:
        print(f"\n**Clarification Generated:**")
        print(f"Session ID: {clarification['session_id']}")
        
        # Format for chatbot
        chatbot_message = chatbot_clarification.format_for_chatbot_ui(clarification)
        print(f"\n**Chatbot Message:**")
        print(chatbot_message)
        
        # Simulate user selecting option 1
        print(f"\n**User selects option 1**")
        response = process_answer(clarification['session_id'], 1)
        
        if response:
            print(f"Selected meaning: {response['selected_meaning']['text']}")
            print(f"Translation: {response['translation']}")
            print(f"Confidence: {response['confidence']}")
    else:
        print("\n**No clarification needed** (auto-detected from context or not ambiguous)")
    
    print("\n" + "="*60)
```

---

## **What File 18 does:**

**Interactive Disambiguation** - handles ambiguous words via chatbot  

**Workflow:**
1. Detects ambiguous word (via File 3)
2. Generates question in target language (via File 17a)
3. Shows multiple-choice options with emojis + examples
4. User selects correct meaning via chatbot
5. Translation continues with confirmed meaning

**Example Chatbot Message (Spanish):**
```
La palabra 'bank' puede significar varias cosas.

¿Cuál es el significado correcto en tu documento?

1. 🏦 Banco (institución financiera) - "I went to the bank"
2. 🏞️ Orilla (de un río) - "sitting on the river bank"
3. ❓ Ninguna de estas (necesito ayuda)

💡 Tip: Lee los ejemplos para ver cómo se usa 'bank' en cada contexto.
