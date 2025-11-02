#!/usr/bin/env python3

"""
Final Production AML Pipeline
Handles SSL issues, improves filtering, and ensures proper data import
"""

import os
import requests
import fitz  # PyMuPDF
import json
import re
from datetime import datetime
from typing import Dict, List, Optional, Any
import time
from urllib.parse import urljoin, urlparse
import spacy
from googletrans import Translator
from simple_supabase_importer import SimpleAMLImporter
import logging
from bs4 import BeautifulSoup
import urllib3
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ProductionAMLPipeline:
    """
    Production-ready AML Pipeline
    Handles SSL issues, improved filtering, and robust data import
    """
    
    def __init__(self):
        """Initialize the production pipeline"""
        
        # Setup robust session with retries
        self.session = requests.Session()
        
        # Setup retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        # Initialize components
        self.translator = Translator()
        
        # Load spaCy model
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            logger.error("spaCy model not found. Installing...")
            os.system("python -m spacy download en_core_web_sm")
            self.nlp = spacy.load("en_core_web_sm")
        
        # Initialize database connection
        self.db_importer = SimpleAMLImporter()
        
        # Enhanced regulatory patterns
        self.rule_patterns = {
            'suspicious_transaction_reporting': [
                r'suspicious.*transaction.*report',
                r'STR.*report',
                r'report.*suspicious.*activit',
                r'unusual.*transaction.*report',
                r'money.*laundering.*report'
            ],
            'customer_due_diligence': [
                r'customer.*due.*diligence',
                r'CDD.*requirement',
                r'know.*your.*customer',
                r'customer.*identification',
                r'verify.*identity'
            ],
            'enhanced_due_diligence': [
                r'enhanced.*due.*diligence',
                r'EDD.*requirement',
                r'higher.*risk.*customer',
                r'additional.*measure'
            ],
            'politically_exposed_person': [
                r'politically.*exposed.*person',
                r'PEP.*screening',
                r'senior.*foreign.*political',
                r'public.*official'
            ],
            'threshold_reporting': [
                r'threshold.*amount',
                r'cash.*transaction.*report',
                r'CTR.*filing',
                r'amount.*exceeding',
                r'large.*cash.*transaction'
            ],
            'sanctions_screening': [
                r'sanction.*screening',
                r'OFAC.*check',
                r'embargo.*compliance',
                r'prohibited.*person'
            ]
        }
        
        logger.info("✅ Production AML Pipeline initialized")
    
    def run_production_pipeline(self, max_docs_per_regulator: int = 20) -> Dict:
        """
        Run the production pipeline
        """
        logger.info(f"🚀 Starting Production AML Pipeline (max {max_docs_per_regulator} docs per regulator)")
        
        start_time = datetime.now()
        total_stats = {
            'documents_processed': 0,
            'rules_extracted': 0,
            'keywords_imported': 0,
            'errors': [],
            'regulators': {}
        }
        
        # Production regulator configurations
        regulators = {
            'FINMA': {
                'name': 'Swiss Financial Market Supervisory Authority',
                'jurisdiction': 'Switzerland',
                'currency': 'CHF',
                'urls': [
                    'https://www.finma.ch/en/documentation/circulars/',
                    'https://www.finma.ch/en/documentation/finma-guidance/'
                ],
                'pdf_patterns': [
                    r'circular.*\d+.*\.pdf',
                    r'rs.*\d+.*\.pdf', 
                    r'guidance.*\.pdf',
                    r'aml.*\.pdf'
                ]
            },
            'MAS': {
                'name': 'Monetary Authority of Singapore',
                'jurisdiction': 'Singapore', 
                'currency': 'SGD',
                'urls': [
                    'https://www.mas.gov.sg/regulation/notices',
                    'https://www.mas.gov.sg/regulation/circulars'
                ],
                'pdf_patterns': [
                    r'notice.*\d+.*\.pdf',
                    r'circular.*\d+.*\.pdf',
                    r'aml.*\.pdf'
                ]
            },
            'HKMA': {
                'name': 'Hong Kong Monetary Authority',
                'jurisdiction': 'Hong Kong',
                'currency': 'HKD',
                'urls': [
                    'https://www.hkma.gov.hk/eng/key-functions/banking/anti-money-laundering-and-counter-financing-of-terrorism/guidance-papers-circulars/'
                ],
                'pdf_patterns': [
                    r'circular.*\.pdf',
                    r'guidance.*\.pdf',
                    r'aml.*\.pdf',
                    r'\d{8}e\d\.pdf'
                ]
            }
        }
        
        # Process each regulator
        for regulator_code, config in regulators.items():
            logger.info(f"\n🏛️ Processing {regulator_code} ({config['name']})")
            
            try:
                regulator_stats = self._process_regulator_production(
                    regulator_code, 
                    config, 
                    max_docs_per_regulator
                )
                
                total_stats['regulators'][regulator_code] = regulator_stats
                total_stats['documents_processed'] += regulator_stats['documents_processed']
                total_stats['rules_extracted'] += regulator_stats['rules_extracted']
                total_stats['keywords_imported'] += regulator_stats['keywords_imported']
                total_stats['errors'].extend(regulator_stats['errors'])
                
            except Exception as e:
                error_msg = f"Failed to process {regulator_code}: {str(e)}"
                logger.error(error_msg)
                total_stats['errors'].append(error_msg)
        
        # Calculate duration
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Final summary
        logger.info(f"\n🎉 Production Pipeline Complete!")
        logger.info(f"📊 Total Documents Processed: {total_stats['documents_processed']}")
        logger.info(f"📋 Total Rules Extracted: {total_stats['rules_extracted']}")
        logger.info(f"🔍 Total Keywords Imported: {total_stats['keywords_imported']}")
        logger.info(f"⏱️ Total Duration: {duration:.2f} seconds")
        
        if total_stats['errors']:
            logger.warning(f"⚠️ Errors encountered: {len(total_stats['errors'])}")
        
        return total_stats
    
    def _process_regulator_production(self, regulator_code: str, config: Dict, max_docs: int) -> Dict:
        """Process a single regulator with production settings"""
        
        stats = {
            'documents_processed': 0,
            'rules_extracted': 0,
            'keywords_imported': 0,
            'errors': []
        }
        
        # Discover documents
        all_documents = []
        for url in config['urls']:
            try:
                documents = self._discover_aml_documents(url, regulator_code, config['pdf_patterns'])
                all_documents.extend(documents)
                logger.info(f"   📄 Found {len(documents)} AML documents from {url}")
            except Exception as e:
                error_msg = f"Failed to discover documents from {url}: {str(e)}"
                logger.error(error_msg)
                stats['errors'].append(error_msg)
        
        # Filter and limit
        filtered_documents = self._filter_aml_documents(all_documents)
        limited_documents = filtered_documents[:max_docs]
        
        logger.info(f"   📊 Processing {len(limited_documents)} AML-relevant documents")
        
        # Process each document
        for i, doc_info in enumerate(limited_documents, 1):
            try:
                logger.info(f"   📄 Processing document {i}/{len(limited_documents)}: {doc_info['title'][:50]}...")
                
                # Extract and process
                success = self._process_single_document(regulator_code, doc_info, i + 200)  # Start from 201
                
                if success:
                    stats['documents_processed'] += 1
                
                # Rate limiting
                time.sleep(2)
                
            except Exception as e:
                error_msg = f"Failed to process document {doc_info.get('title', 'unknown')}: {str(e)}"
                logger.error(error_msg)
                stats['errors'].append(error_msg)
        
        return stats
    
    def _discover_aml_documents(self, url: str, regulator_code: str, pdf_patterns: List[str]) -> List[Dict]:
        """Discover AML-specific documents"""
        
        logger.info(f"   🔍 Discovering AML documents from {url}")
        
        try:
            # Get webpage with SSL verification disabled for problematic sites
            verify_ssl = 'hkma.gov.hk' not in url
            response = self.session.get(url, timeout=30, verify=verify_ssl)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            documents = []
            seen_urls = set()
            
            # Find all PDF links
            pdf_links = soup.find_all('a', href=re.compile(r'\.pdf', re.I))
            
            for link in pdf_links:
                href = link.get('href')
                if not href:
                    continue
                
                # Resolve URL
                if href.startswith('/'):
                    href = urljoin(url, href)
                elif not href.startswith('http'):
                    href = urljoin(url, href)
                
                if href in seen_urls:
                    continue
                seen_urls.add(href)
                
                # Get title
                title = link.get_text(strip=True)
                if not title:
                    title = link.get('title', os.path.basename(href))
                
                # Check if AML-relevant
                if self._is_aml_document(href, title, regulator_code):
                    documents.append({
                        'title': title[:200],
                        'url': href,
                        'date': self._extract_date_from_text(title),
                        'type': 'regulation'
                    })
                
                if len(documents) >= 30:
                    break
            
            logger.info(f"   ✅ Found {len(documents)} AML-relevant documents")
            return documents
            
        except Exception as e:
            logger.error(f"   ❌ Document discovery failed for {url}: {str(e)}")
            return []
    
    def _is_aml_document(self, url: str, title: str, regulator_code: str) -> bool:
        """Enhanced AML document detection"""
        
        url_lower = url.lower()
        title_lower = title.lower()
        
        # Strong AML indicators
        strong_aml_keywords = [
            'anti-money laundering', 'aml', 'suspicious transaction',
            'customer due diligence', 'cdd', 'enhanced due diligence', 'edd',
            'politically exposed person', 'pep', 'sanctions screening',
            'beneficial ownership', 'kyc', 'know your customer',
            'counter financing terrorism', 'cft'
        ]
        
        # Document type indicators
        doc_type_keywords = ['circular', 'guidance', 'notice', 'directive']
        
        # Check for strong AML indicators
        has_strong_aml = any(keyword in title_lower or keyword in url_lower for keyword in strong_aml_keywords)
        
        # Check for document types with potential AML content
        has_doc_type = any(keyword in title_lower or keyword in url_lower for keyword in doc_type_keywords)
        
        # Exclude non-relevant content
        exclude_keywords = [
            'newsletter', 'news', 'event', 'calendar', 'contact', 'about',
            'biography', 'speech', 'press release', 'annual report'
        ]
        is_excluded = any(keyword in title_lower for keyword in exclude_keywords)
        
        return has_strong_aml or (has_doc_type and not is_excluded)
    
    def _filter_aml_documents(self, documents: List[Dict]) -> List[Dict]:
        """Filter for most relevant AML documents"""
        
        # Sort by relevance score
        scored_docs = []
        for doc in documents:
            score = self._calculate_aml_relevance_score(doc['title'], doc['url'])
            scored_docs.append((score, doc))
        
        # Sort by score (highest first)
        scored_docs.sort(key=lambda x: x[0], reverse=True)
        
        # Return top documents
        return [doc for score, doc in scored_docs if score > 0]
    
    def _calculate_aml_relevance_score(self, title: str, url: str) -> float:
        """Calculate AML relevance score for prioritization"""
        
        score = 0.0
        text = (title + " " + url).lower()
        
        # High-value AML keywords
        high_value = ['aml', 'anti-money laundering', 'suspicious transaction', 'cdd', 'edd']
        for keyword in high_value:
            if keyword in text:
                score += 3.0
        
        # Medium-value keywords
        medium_value = ['compliance', 'due diligence', 'sanctions', 'pep', 'kyc']
        for keyword in medium_value:
            if keyword in text:
                score += 2.0
        
        # Document type bonus
        doc_types = ['circular', 'guidance', 'notice']
        for doc_type in doc_types:
            if doc_type in text:
                score += 1.0
        
        return score
    
    def _process_single_document(self, regulator_code: str, doc_info: Dict, doc_num: int) -> bool:
        """Process a single document and import to database"""
        
        try:
            # Extract text
            text_content = self._extract_pdf_text_robust(doc_info['url'])
            if not text_content or len(text_content) < 100:
                logger.warning(f"   ⚠️ Insufficient text content")
                return False
            
            # Detect and translate
            translated_content, language_info = self._handle_translation_robust(text_content)
            
            # Check if content is AML-relevant after translation
            if not self._contains_aml_content(translated_content):
                logger.warning(f"   ⚠️ No AML content detected")
                return False
            
            # Extract rules
            rules = self._extract_aml_rules(translated_content, regulator_code, doc_info, doc_num)
            
            if not rules:
                logger.warning(f"   ⚠️ No rules extracted")
                return False
            
            # Prepare document data
            document_data = {
                'document_id': f"{regulator_code}-{str(doc_num).zfill(3)}",
                'title': doc_info['title'],
                'url': doc_info['url'],
                'document_type': 'regulation',
                'effective_date': doc_info.get('date'),
                'language': language_info,
                'extraction_confidence': self._calculate_document_confidence(rules),
                'rules': rules
            }
            
            # Import to database
            self._import_document_to_database_robust(regulator_code, document_data)
            
            return True
            
        except Exception as e:
            logger.error(f"   ❌ Failed to process document: {str(e)}")
            return False
    
    def _extract_pdf_text_robust(self, url: str) -> str:
        """Robust PDF text extraction with SSL handling"""
        
        try:
            # Handle SSL verification based on domain
            verify_ssl = 'hkma.gov.hk' not in url
            
            response = self.session.get(url, timeout=60, verify=verify_ssl)
            response.raise_for_status()
            
            # Extract text
            doc = fitz.open(stream=response.content, filetype="pdf")
            text_content = ""
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                text_content += page.get_text()
            
            doc.close()
            
            # Clean text
            text_content = re.sub(r'\s+', ' ', text_content)
            return text_content.strip()
            
        except Exception as e:
            logger.error(f"   ❌ PDF extraction failed: {str(e)}")
            return ""
    
    def _handle_translation_robust(self, text: str) -> tuple[str, str]:
        """Robust translation handling"""
        
        # Quick language detection
        try:
            sample_text = text[:1000]
            detected = self.translator.detect(sample_text)
            detected_lang = detected.lang if hasattr(detected, 'lang') else 'en'
        except:
            detected_lang = 'en'
        
        if detected_lang in ['de', 'fr', 'it'] and detected_lang != 'en':
            try:
                # Translate key sections only for efficiency
                translated_text = self._translate_key_sections(text, detected_lang)
                return translated_text, f"{detected_lang} (translated)"
            except Exception as e:
                logger.warning(f"   ⚠️ Translation failed: {str(e)}")
                return text, detected_lang
        
        return text, detected_lang
    
    def _translate_key_sections(self, text: str, source_lang: str) -> str:
        """Translate only key sections for efficiency"""
        
        # Split into paragraphs
        paragraphs = text.split('\n\n')
        translated_paragraphs = []
        
        for para in paragraphs[:20]:  # Limit to first 20 paragraphs
            if len(para) > 50:  # Only translate substantial paragraphs
                try:
                    result = self.translator.translate(para[:2000], src=source_lang, dest='en')
                    translated_paragraphs.append(result.text)
                    time.sleep(0.3)
                except:
                    translated_paragraphs.append(para)
            else:
                translated_paragraphs.append(para)
        
        return '\n\n'.join(translated_paragraphs)
    
    def _contains_aml_content(self, text: str) -> bool:
        """Check if text contains AML-relevant content"""
        
        text_lower = text.lower()
        
        aml_indicators = [
            'money laundering', 'suspicious transaction', 'due diligence',
            'customer identification', 'beneficial ownership', 'sanctions',
            'politically exposed', 'compliance', 'reporting requirement'
        ]
        
        count = sum(1 for indicator in aml_indicators if indicator in text_lower)
        return count >= 2  # At least 2 AML indicators
    
    def _extract_aml_rules(self, text: str, regulator_code: str, doc_info: Dict, doc_num: int) -> List[Dict]:
        """Extract AML rules with improved accuracy"""
        
        rules = []
        doc = self.nlp(text[:500000])  # Process up to 500k chars
        
        sentences = [sent.text.strip() for sent in doc.sents if len(sent.text.strip()) > 30]
        
        rule_counter = 1
        
        # Extract rules by type
        for rule_type, patterns in self.rule_patterns.items():
            type_rules = []
            
            for pattern in patterns:
                for sentence in sentences:
                    if re.search(pattern, sentence, re.IGNORECASE) and len(sentence) > 50:
                        # Check for substantial content
                        if self._is_substantial_rule(sentence):
                            rule = self._create_rule_object(
                                regulator_code, rule_type, sentence, 
                                doc_info, doc_num, rule_counter
                            )
                            type_rules.append(rule)
                            rule_counter += 1
                        
                        if len(type_rules) >= 5:  # Limit per type
                            break
            
            rules.extend(type_rules)
            
            if len(rules) >= 25:  # Total limit
                break
        
        return rules
    
    def _is_substantial_rule(self, sentence: str) -> bool:
        """Check if sentence contains substantial rule content"""
        
        # Must contain action words
        action_words = ['must', 'shall', 'should', 'required', 'need', 'establish', 'implement', 'maintain']
        has_action = any(word in sentence.lower() for word in action_words)
        
        # Must be substantial length
        is_substantial = len(sentence) > 50
        
        # Should not be just reference or header
        reference_indicators = ['section', 'article', 'paragraph', 'page', 'see']
        is_reference = any(ind in sentence.lower()[:20] for ind in reference_indicators)
        
        return has_action and is_substantial and not is_reference
    
    def _create_rule_object(self, regulator_code: str, rule_type: str, sentence: str, 
                           doc_info: Dict, doc_num: int, rule_counter: int) -> Dict:
        """Create a rule object with all necessary fields"""
        
        rule_id = f"{regulator_code}-{rule_type.upper()[:3]}-{str(doc_num)}-{str(rule_counter).zfill(2)}"
        
        rule = {
            'rule_id': rule_id,
            'rule_type': rule_type,
            'title': self._generate_rule_title(rule_type),
            'description': sentence,
            'confidence': self._calculate_rule_confidence(sentence, rule_type),
            'extracted_from': doc_info['title']
        }
        
        # Add type-specific fields
        if rule_type == 'threshold_reporting':
            rule.update(self._extract_threshold_info(sentence))
        elif rule_type == 'suspicious_transaction_reporting':
            rule.update(self._extract_str_info(sentence, regulator_code))
        
        return rule
    
    def _generate_rule_title(self, rule_type: str) -> str:
        """Generate rule title"""
        titles = {
            'suspicious_transaction_reporting': 'Suspicious Transaction Reporting',
            'customer_due_diligence': 'Customer Due Diligence',
            'enhanced_due_diligence': 'Enhanced Due Diligence',
            'politically_exposed_person': 'PEP Requirements',
            'threshold_reporting': 'Threshold Reporting',
            'sanctions_screening': 'Sanctions Screening'
        }
        return titles.get(rule_type, 'AML Compliance Rule')
    
    def _calculate_rule_confidence(self, text: str, rule_type: str) -> float:
        """Calculate confidence score"""
        base_confidence = 0.6
        
        confidence_indicators = ['must', 'shall', 'required', 'mandatory']
        matches = sum(1 for indicator in confidence_indicators if indicator.lower() in text.lower())
        
        return min(base_confidence + (matches * 0.1), 1.0)
    
    def _extract_threshold_info(self, text: str) -> Dict:
        """Extract threshold information"""
        amount_pattern = r'(\d{1,3}(?:,\d{3})*)\s*(CHF|SGD|HKD|USD|EUR)'
        match = re.search(amount_pattern, text, re.IGNORECASE)
        
        if match:
            return {
                'threshold_amount': float(match.group(1).replace(',', '')),
                'threshold_currency': match.group(2).upper()
            }
        return {}
    
    def _extract_str_info(self, text: str, regulator_code: str) -> Dict:
        """Extract STR information"""
        authorities = {
            'FINMA': 'FINMA',
            'MAS': 'STRO',
            'HKMA': 'JFIU'
        }
        
        return {
            'reporting_authority': authorities.get(regulator_code),
            'reporting_timeframe': self._extract_timeframe(text)
        }
    
    def _extract_timeframe(self, text: str) -> Optional[str]:
        """Extract timeframe"""
        if 'immediate' in text.lower():
            return 'immediate'
        
        day_match = re.search(r'(\d+)\s*day', text, re.IGNORECASE)
        if day_match:
            return f"{day_match.group(1)} days"
        
        return None
    
    def _extract_date_from_text(self, text: str) -> Optional[str]:
        """Extract date from text"""
        date_patterns = [
            r'\b(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{4})\b',
            r'\b(\d{4}[\/\-\.]\d{1,2}[\/\-\.]\d{1,2})\b'
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        return None
    
    def _calculate_document_confidence(self, rules: List[Dict]) -> float:
        """Calculate document confidence"""
        if not rules:
            return 0.3
        
        avg_confidence = sum(rule.get('confidence', 0.5) for rule in rules) / len(rules)
        return round(avg_confidence, 2)
    
    def _import_document_to_database_robust(self, regulator_code: str, document_data: Dict):
        """Robust database import"""
        
        try:
            # Import document
            doc_id = self.db_importer._import_document(regulator_code, document_data)
            
            # Import rules with proper error handling
            total_rules = 0
            total_keywords = 0
            
            for rule_data in document_data['rules']:
                try:
                    # Import rule
                    rule_id = self.db_importer._import_rule(doc_id, rule_data)
                    total_rules += 1
                    
                    # Import keywords with error handling
                    try:
                        keywords_count = self.db_importer._import_keywords(rule_id, rule_data)
                        total_keywords += keywords_count
                    except Exception as e:
                        logger.warning(f"     ⚠️ Keywords import failed for {rule_id}: {str(e)}")
                        # Continue without keywords
                    
                except Exception as e:
                    logger.error(f"     ⚠️ Rule import failed for {rule_data.get('rule_id')}: {str(e)}")
            
            logger.info(f"     ✅ Imported: {total_rules} rules, {total_keywords} keywords")
            
        except Exception as e:
            logger.error(f"   ❌ Document import failed: {str(e)}")
            raise


if __name__ == "__main__":
    pipeline = ProductionAMLPipeline()
    
    print("🚀 Starting Production AML Pipeline")
    print("=" * 50)
    
    try:
        results = pipeline.run_production_pipeline(max_docs_per_regulator=20)
        
        print("\n🎉 Production pipeline completed!")
        print(f"📊 Final Summary:")
        print(f"   Documents processed: {results['documents_processed']}")
        print(f"   Rules extracted: {results['rules_extracted']}")
        print(f"   Keywords imported: {results['keywords_imported']}")
        
        for regulator, stats in results['regulators'].items():
            print(f"   {regulator}: {stats['documents_processed']} docs, {stats['rules_extracted']} rules")
            
        print(f"\n✅ Your enhanced AML database is ready for production!")
        
    except Exception as e:
        print(f"❌ Pipeline failed: {str(e)}")
        exit(1)