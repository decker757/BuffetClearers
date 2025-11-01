"""
Enhanced metadata extraction for documents
- Page count
- Text coverage percentage
- Author/creator metadata
- Document type classification
"""

import os
from typing import Dict, Any, Optional
from datetime import datetime


class MetadataExtractor:
    """Extract comprehensive metadata from documents"""

    # Document type patterns
    DOCUMENT_TYPES = {
        'contract': ['agreement', 'contract', 'terms and conditions', 'party', 'whereas'],
        'invoice': ['invoice', 'bill', 'payment', 'total', 'subtotal', 'tax'],
        'financial_statement': ['balance sheet', 'income statement', 'cash flow', 'assets', 'liabilities'],
        'legal': ['plaintiff', 'defendant', 'court', 'legal', 'jurisdiction'],
        'kyc': ['know your customer', 'identity', 'passport', 'address proof', 'verification'],
        'aml': ['anti-money laundering', 'suspicious activity', 'transaction monitoring'],
    }

    @staticmethod
    def extract_pdf_metadata(file_path: str) -> Dict[str, Any]:
        """Extract metadata from PDF files"""
        metadata = {
            'page_count': 0,
            'author': None,
            'creator': None,
            'producer': None,
            'creation_date': None,
            'modification_date': None,
            'text_coverage_percent': 0,
            'total_characters': 0,
            'is_scanned': False,
            'document_type': 'unknown',
            'confidence': 0
        }

        try:
            from PyPDF2 import PdfReader

            reader = PdfReader(file_path)
            metadata['page_count'] = len(reader.pages)

            # Extract document info
            if reader.metadata:
                metadata['author'] = reader.metadata.get('/Author', None)
                metadata['creator'] = reader.metadata.get('/Creator', None)
                metadata['producer'] = reader.metadata.get('/Producer', None)

                # Parse dates
                creation_date = reader.metadata.get('/CreationDate', None)
                if creation_date:
                    metadata['creation_date'] = str(creation_date)

                mod_date = reader.metadata.get('/ModDate', None)
                if mod_date:
                    metadata['modification_date'] = str(mod_date)

            # Extract text and calculate coverage
            total_text = ""
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    total_text += text

            metadata['total_characters'] = len(total_text)

            # Estimate text coverage (characters per page)
            if metadata['page_count'] > 0:
                chars_per_page = metadata['total_characters'] / metadata['page_count']
                # Typical page has ~2000-3000 characters
                # Below 500 chars/page suggests scanned or mostly images
                metadata['text_coverage_percent'] = min(100, (chars_per_page / 2000) * 100)

                if chars_per_page < 500:
                    metadata['is_scanned'] = True

            # Classify document type
            doc_type, confidence = MetadataExtractor._classify_document_type(total_text.lower())
            metadata['document_type'] = doc_type
            metadata['confidence'] = confidence

        except Exception as e:
            metadata['error'] = str(e)

        return metadata

    @staticmethod
    def extract_image_metadata(file_path: str) -> Dict[str, Any]:
        """Extract metadata from image files"""
        metadata = {
            'width': 0,
            'height': 0,
            'format': None,
            'mode': None,
            'has_exif': False,
            'exif_data': {},
            'file_size_kb': 0
        }

        try:
            from PIL import Image
            from PIL.ExifTags import TAGS

            image = Image.open(file_path)
            metadata['width'] = image.width
            metadata['height'] = image.height
            metadata['format'] = image.format
            metadata['mode'] = image.mode
            metadata['file_size_kb'] = os.path.getsize(file_path) / 1024

            # Extract EXIF if available
            if hasattr(image, '_getexif') and image._getexif():
                exif = image._getexif()
                metadata['has_exif'] = True

                for tag_id, value in exif.items():
                    tag = TAGS.get(tag_id, tag_id)
                    metadata['exif_data'][tag] = str(value)

        except Exception as e:
            metadata['error'] = str(e)

        return metadata

    @staticmethod
    def _classify_document_type(text: str) -> tuple[str, float]:
        """
        Classify document type based on content

        Returns:
            (document_type, confidence_score)
        """
        if not text or len(text) < 100:
            return 'unknown', 0.0

        scores = {}

        for doc_type, keywords in MetadataExtractor.DOCUMENT_TYPES.items():
            score = 0
            for keyword in keywords:
                if keyword in text:
                    score += 1

            # Normalize score
            if len(keywords) > 0:
                scores[doc_type] = (score / len(keywords)) * 100

        if not scores:
            return 'unknown', 0.0

        # Get highest scoring type
        best_type = max(scores.items(), key=lambda x: x[1])

        # Only return if confidence > 20%
        if best_type[1] > 20:
            return best_type[0], best_type[1]

        return 'unknown', 0.0

    @staticmethod
    def extract_completeness_indicators(text: str, doc_type: str = 'unknown') -> Dict[str, Any]:
        """
        Analyze document completeness based on type

        Returns detailed completeness report
        """
        indicators = {
            'has_date': False,
            'has_signature_section': False,
            'has_parties': False,
            'has_amounts': False,
            'has_terms': False,
            'has_page_numbers': False,
            'missing_elements': [],
            'completeness_score': 0
        }

        if not text:
            indicators['missing_elements'].append('No text content extracted')
            return indicators

        text_lower = text.lower()

        # Check for common elements
        # Date patterns
        import re
        date_patterns = [
            r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}',  # DD/MM/YYYY
            r'\d{4}[/-]\d{1,2}[/-]\d{1,2}',    # YYYY-MM-DD
            r'(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2},?\s+\d{4}'
        ]
        for pattern in date_patterns:
            if re.search(pattern, text_lower):
                indicators['has_date'] = True
                break

        # Signature indicators
        signature_keywords = ['signature', 'signed by', 'executed', 'signed on']
        if any(kw in text_lower for kw in signature_keywords):
            indicators['has_signature_section'] = True

        # Party indicators
        party_keywords = ['party', 'buyer', 'seller', 'client', 'vendor', 'between']
        if any(kw in text_lower for kw in party_keywords):
            indicators['has_parties'] = True

        # Amount indicators
        amount_patterns = [r'\$\d+', r'€\d+', r'£\d+', r'\d+\.\d{2}']
        for pattern in amount_patterns:
            if re.search(pattern, text):
                indicators['has_amounts'] = True
                break

        # Terms/conditions
        if 'terms' in text_lower or 'conditions' in text_lower or 'obligations' in text_lower:
            indicators['has_terms'] = True

        # Page numbers
        page_patterns = [r'page\s+\d+', r'\d+\s+of\s+\d+', r'p\.\s*\d+']
        for pattern in page_patterns:
            if re.search(pattern, text_lower):
                indicators['has_page_numbers'] = True
                break

        # Build missing elements list
        if not indicators['has_date']:
            indicators['missing_elements'].append('Date not found')
        if not indicators['has_signature_section']:
            indicators['missing_elements'].append('Signature section not found')
        if not indicators['has_parties']:
            indicators['missing_elements'].append('Parties/entities not identified')
        if not indicators['has_amounts']:
            indicators['missing_elements'].append('No monetary amounts detected')

        # Calculate completeness score
        total_checks = 6
        passed_checks = sum([
            indicators['has_date'],
            indicators['has_signature_section'],
            indicators['has_parties'],
            indicators['has_amounts'],
            indicators['has_terms'],
            indicators['has_page_numbers']
        ])

        indicators['completeness_score'] = (passed_checks / total_checks) * 100

        return indicators
