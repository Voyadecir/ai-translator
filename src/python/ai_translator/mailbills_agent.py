"""
MailBills Agent - Main Deep Agent for Document Translation

This agent orchestrates the entire pipeline from OCR through translation and
enrichment.  It uses Azure Document Intelligence for OCR and will use
Azure OpenAI or the standard OpenAI API for classification and translation
depending on which credentials are available.  If Azure credentials are not
present, the agent falls back to the regular OpenAI client via the
`OPENAI_API_KEY` environment variable.  No new environment variables are
required; the agent will continue to function with the existing settings.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import os
import openai
from openai import AzureOpenAI

# Azure clients
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential

# Utility modules
from .utils.ocr_preprocessor import ocr_preprocessor, preprocess_for_ocr, assess_image
from .utils.ocr_postprocessor import ocr_postprocessor, clean_ocr_output
from .utils.translation_engine import translation_engine, translate_text
from .utils.translation_dictionaries import get_translation, AUTHORITATIVE_SOURCES
from .utils.ui_translation import ui_translator

logger = logging.getLogger(__name__)


class MailBillsAgent:
    """
    Main deep agent for document translation and enrichment.

    This class handles OCR preprocessing, calls Azure Document Intelligence for
    text extraction, classifies document type (using GPT if keywords fail),
    translates the content with cultural intelligence, and prepares any
    clarifications or warnings for the user.  It relies on the translation
    engine for performing the actual translation and supports both Azure and
    standard OpenAI backends.  When Azure credentials are absent, the agent
    gracefully falls back to the standard OpenAI client.
    """

    def __init__(self):
        """Initialize Azure services and GPT clients."""
        # Azure Document Intelligence (OCR)
        self.doc_intel_client = DocumentIntelligenceClient(
            endpoint=os.getenv("AZURE_DOC_INTEL_ENDPOINT"),
            credential=AzureKeyCredential(os.getenv("AZURE_DOC_INTEL_KEY")),
        )

        # Initialize OpenAI client with fallback to standard API
        azure_key = os.getenv("AZURE_OPENAI_API_KEY")
        azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        if azure_key and azure_endpoint:
            try:
                self.openai_client = AzureOpenAI(
                    api_key=azure_key,
                    api_version="2024-02-15-preview",
                    azure_endpoint=azure_endpoint,
                )
                logger.info("MailBillsAgent using Azure OpenAI.")
            except Exception as e:
                logger.warning(f"Failed to initialize AzureOpenAI client: {e}")
                self.openai_client = None
        else:
            openai_key = os.getenv("OPENAI_API_KEY")
            if openai_key:
                try:
                    self.openai_client = openai.OpenAI(api_key=openai_key)
                    logger.info("MailBillsAgent using standard OpenAI.")
                except Exception as e:
                    logger.warning(f"Failed to initialize OpenAI client: {e}")
                    self.openai_client = None
            else:
                logger.warning(
                    "No OpenAI API key found; document classification may be limited."
                )
                self.openai_client = None

        # Load document type metadata
        self.document_types = self._load_document_types()

        # Default language settings
        self.default_source_lang = 'en'
        self.default_target_lang = 'es'

    # =====================================================================
    # DOCUMENT TYPES
    # =====================================================================
    def _load_document_types(self) -> Dict[str, Dict]:
        """Load supported document types and metadata."""
        return {
            # IRS forms
            "irs_1040": {
                "name": "IRS Form 1040 - Individual Tax Return",
                "category": "tax",
                "keywords": ["1040", "U.S. Individual Income Tax Return", "Department of the Treasury"],
                "authority": "IRS",
                "url": "https://www.irs.gov/forms-pubs/about-form-1040",
            },
            "irs_w2": {
                "name": "IRS Form W-2 - Wage and Tax Statement",
                "category": "tax",
                "keywords": ["W-2", "Wage and Tax Statement", "Employer's identification number"],
                "authority": "IRS",
            },
            "irs_w9": {
                "name": "IRS Form W-9 - Request for Taxpayer Identification",
                "category": "tax",
                "keywords": ["W-9", "Request for Taxpayer Identification Number"],
                "authority": "IRS",
            },
            # USCIS forms
            "uscis_i9": {
                "name": "USCIS Form I-9 - Employment Eligibility Verification",
                "category": "immigration",
                "keywords": ["I-9", "Employment Eligibility Verification", "USCIS"],
                "authority": "USCIS",
            },
            "uscis_i130": {
                "name": "USCIS Form I-130 - Petition for Alien Relative",
                "category": "immigration",
                "keywords": ["I-130", "Petition for Alien Relative"],
                "authority": "USCIS",
            },
            # Medical documents
            "prescription": {
                "name": "Medical Prescription",
                "category": "medical",
                "keywords": ["Rx", "prescription", "medication", "dosage", "refills"],
                "authority": "Medical",
            },
            "lab_results": {
                "name": "Laboratory Test Results",
                "category": "medical",
                "keywords": ["lab results", "test results", "specimen", "reference range"],
                "authority": "Medical",
            },
            # Utility bills
            "electric_bill": {
                "name": "Electric Bill",
                "category": "utility",
                "keywords": ["electric", "electricity", "kWh", "meter reading", "billing period"],
                "authority": "Utility",
            },
            "water_bill": {
                "name": "Water Bill",
                "category": "utility",
                "keywords": ["water", "sewer", "gallons", "water service"],
                "authority": "Utility",
            },
            # Additional document types could be defined here
        }

    # =====================================================================
    # MAIN PIPELINE
    # =====================================================================
    def process_document(
        self,
        image_bytes: bytes,
        source_lang: str = 'en',
        target_lang: str = 'es',
        user_preferences: Optional[Dict] = None,
    ) -> Dict:
        """
        Process an uploaded document: OCR → translation → enrichment.

        Args:
            image_bytes: The image data of the document.
            source_lang: Source language code.
            target_lang: Target language code.
            user_preferences: Optional translation preferences.

        Returns:
            A dictionary containing OCR text, translated text, confidence score,
            warnings, cultural notes, clarifications needed, enrichment data, and
            metadata about the process.
        """
        result = {
            'document_type': None,
            'ocr_text': '',
            'translated_text': '',
            'confidence_score': 0.0,
            'warnings': [],
            'cultural_notes': [],
            'clarifications_needed': [],
            'enrichment': {},
            'pdf_url': None,
            'metadata': {
                'processing_steps': [],
                'timestamp': datetime.now().isoformat(),
            },
        }
        try:
            # Step 1: Assess image quality
            logger.info("Step 1: Assessing image quality...")
            quality = assess_image(image_bytes)
            result['metadata']['image_quality'] = quality
            result['metadata']['processing_steps'].append('image_quality_assessment')

            # Step 2: Preprocess image if needed
            if quality.get('needs_preprocessing', False):
                logger.info("Step 2: Preprocessing image for better OCR...")
                aggressive = quality.get('recommended_aggressive', False)
                enhanced_bytes, preprocess_metadata = preprocess_for_ocr(image_bytes, aggressive)
                result['metadata']['preprocessing'] = preprocess_metadata
                result['metadata']['processing_steps'].append('image_preprocessing')
                image_to_ocr = enhanced_bytes
            else:
                logger.info("Step 2: Image quality good, skipping preprocessing")
                image_to_ocr = image_bytes

            # Step 3: OCR via Azure Document Intelligence
            logger.info("Step 3: Running Azure Document Intelligence OCR...")
            ocr_raw = self._run_azure_ocr(image_to_ocr)
            result['metadata']['processing_steps'].append('azure_ocr')
            if not ocr_raw:
                result['warnings'].append('OCR failed to extract text')
                return result

            # Step 4: Detect document type
            logger.info("Step 4: Detecting document type...")
            doc_type = self._detect_document_type(ocr_raw)
            result['document_type'] = doc_type
            result['metadata']['processing_steps'].append('document_type_detection')

            # Step 5: Postprocess OCR output
            logger.info("Step 5: Postprocessing OCR output...")
            ocr_cleaned = clean_ocr_output(ocr_raw, doc_type)
            result['ocr_text'] = ocr_cleaned['cleaned_text']
            result['metadata']['ocr_postprocessing'] = ocr_cleaned
            result['metadata']['processing_steps'].append('ocr_postprocessing')

            # Step 6: Translate with cultural intelligence
            logger.info("Step 6: Translating with cultural intelligence...")
            translation_result = translate_text(
                text=result['ocr_text'],
                source_lang=source_lang,
                target_lang=target_lang,
                document_type=doc_type,
                user_preferences=user_preferences,
            )
            result['translated_text'] = translation_result['translated_text']
            result['confidence_score'] = translation_result['confidence_score']
            result['warnings'].extend(translation_result['warnings'])
            result['cultural_notes'].extend(translation_result['cultural_notes'])
            result['enrichment'] = translation_result['enrichment']
            result['metadata']['processing_steps'].append('translation_engine')

            # Step 7: Prepare clarifications for ambiguous words
            logger.info("Step 7: Checking for ambiguous words...")
            ambiguous = translation_result['enrichment'].get('ambiguous_words', [])
            if ambiguous:
                result['clarifications_needed'] = self._prepare_clarifications(ambiguous, target_lang)
                result['metadata']['processing_steps'].append('clarification_detection')

            # Step 8: PDF generation (placeholder)
            logger.info("Step 8: Generating PDF... (not yet implemented)")
            result['metadata']['processing_steps'].append('pdf_generation')

            logger.info(
                f"Document processing complete. Type: {doc_type}, Confidence: {result['confidence_score']:.2f}"
            )
            return result
        except Exception as e:
            logger.error(f"Document processing error: {e}")
            result['warnings'].append(f'Processing error: {str(e)}')
            return result

    # =====================================================================
    # OCR PROCESSING
    # =====================================================================
    def _run_azure_ocr(self, image_bytes: bytes) -> Optional[str]:
        """Run Azure Document Intelligence OCR and return extracted text."""
        try:
            poller = self.doc_intel_client.begin_analyze_document(
                "prebuilt-read", image_bytes
            )
            result = poller.result()
            text_content = []
            for page in result.pages:
                for line in page.lines:
                    text_content.append(line.content)
            return '\n'.join(text_content)
        except Exception as e:
            logger.error(f"Azure OCR error: {e}")
            return None

    # =====================================================================
    # DOCUMENT TYPE DETECTION
    # =====================================================================
    def _detect_document_type(self, ocr_text: str) -> Optional[str]:
        """Detect document type using keyword search and GPT classification."""
        # First, attempt keyword matching
        for doc_type, metadata in self.document_types.items():
            keywords = metadata.get('keywords', [])
            for keyword in keywords:
                if keyword.lower() in ocr_text.lower():
                    logger.info(f"Document type detected by keywords: {doc_type}")
                    return doc_type
        # Fallback to GPT classification if OpenAI client is available
        if self.openai_client:
            try:
                prompt = (
                    "Analyze this document text and classify it into one of these categories: \n"
                    "- IRS tax forms (1040, W-2, W-9, 1099, etc.)\n"
                    "- USCIS immigration forms (I-9, I-130, I-485, etc.)\n"
                    "- Medical documents (prescription, lab results, diagnosis, etc.)\n"
                    "- Utility bills (electric, water, gas, etc.)\n"
                    "- Bank statements\n"
                    "- Insurance documents\n"
                    "- Legal documents\n"
                    "- Other\n\n"
                    "Document text:\n"
                    f"{ocr_text[:500]}\n\n"
                    "Respond with just the category name."
                )
                response = self.openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a document classifier.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    max_tokens=50,
                    temperature=0.1,
                )
                category = response.choices[0].message.content.strip().lower()
                logger.info(f"Document type detected by GPT: {category}")
                return category
            except Exception as e:
                logger.error(f"Document type detection error: {e}")
                return "unknown"
        else:
            logger.warning(
                "OpenAI client unavailable; document type classification limited to keyword matching."
            )
            return "unknown"

    # =====================================================================
    # CLARIFICATION PREPARATION
    # =====================================================================
    def _prepare_clarifications(
        self, ambiguous_words: List[Dict], target_lang: str
    ) -> List[Dict]:
        clarifications = []
        for word_info in ambiguous_words:
            word = word_info['word']
            meanings = word_info.get('meanings', [])
            question_text = ui_translator.translate_ui_element(
                f"Which meaning of '{word}' is correct?",
                element_type="label",
                target_lang=target_lang,
            )
            clarifications.append({
                'word': word,
                'question': question_text,
                'options': meanings,
                'type': 'multiple_choice',
            })
        return clarifications

    # =====================================================================
    # AUTHORITATIVE SOURCES INFO
    # =====================================================================
    def get_authoritative_sources(self) -> List[Dict]:
        """Return a list of authoritative dictionary sources used."""
        sources = []
        for source_key, source_data in AUTHORITATIVE_SOURCES.items():
            sources.append({
                'name': source_data['name'],
                'url': source_data['url'],
                'category': source_data.get('category', 'general'),
                'description': source_data.get('description', ''),
            })
        return sources


# =====================================================================
# GLOBAL INSTANCE
# =====================================================================
mailbills_agent = MailBillsAgent()


def process_document(
    image_bytes: bytes,
    source_lang: str = 'en',
    target_lang: str = 'es',
    user_preferences: Optional[Dict] = None,
) -> Dict:
    """Convenience function to process a document using the global agent."""
    return mailbills_agent.process_document(
        image_bytes, source_lang, target_lang, user_preferences
    )
