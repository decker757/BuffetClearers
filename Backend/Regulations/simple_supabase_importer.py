#!/usr/bin/env python3

"""
Simple AML Rules JSON to Supabase Importer
Imports extracted regulatory rules from JSON into Supabase database using requests
"""

import json
import os
import requests
from datetime import datetime
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv
import re

# Load environment variables
load_dotenv()

class SimpleAMLImporter:
    """
    Import AML rules from JSON into Supabase database using requests
    """
    
    def __init__(self, supabase_url: str = None, supabase_key: str = None):
        """Initialize the importer with Supabase credentials"""
        
        # Use provided credentials or get from environment
        self.supabase_url = supabase_url or os.getenv('SUPABASE_URL')
        self.supabase_key = supabase_key or os.getenv('SUPABASE_PUBLIC_KEY')
        
        # Also try alternative environment variable names
        if not self.supabase_url:
            self.supabase_url = os.getenv('SUPABASE_PROJECT_URL')
        if not self.supabase_key:
            self.supabase_key = os.getenv('SUPABASE_ANON_KEY')
        
        # Extract Supabase URL if PostgreSQL format is provided
        if self.supabase_url and 'postgresql://' in self.supabase_url:
            # Extract project ref from PostgreSQL URL
            # postgresql://postgres:password@db.eoczumhzekbkzbcynoae.supabase.co:5432/postgres
            import re
            match = re.search(r'@db\.([^.]+)\.supabase\.co', self.supabase_url)
            if match:
                project_ref = match.group(1)
                self.supabase_url = f"https://{project_ref}.supabase.co"
                print(f"🔧 Converted PostgreSQL URL to REST API URL: {self.supabase_url}")
        
        if not self.supabase_url or not self.supabase_key:
            print("❌ Missing Supabase credentials. Please provide:")
            print("   - SUPABASE_URL: Your project URL (e.g., https://abc123.supabase.co)")
            print("   - SUPABASE_PUBLIC_KEY: Your anon/public API key")
            print("   You can find these in your Supabase dashboard under Project Settings > API")
            raise ValueError("❌ Supabase URL and key are required.")
        
        # Setup headers for Supabase REST API
        self.headers = {
            'apikey': self.supabase_key,
            'Authorization': f'Bearer {self.supabase_key}',
            'Content-Type': 'application/json',
            'Prefer': 'return=minimal'
        }
        
        self.base_url = f"{self.supabase_url}/rest/v1"
        
        print("✅ Connected to Supabase via REST API")
        
    def import_from_json(self, json_file_path: str) -> Dict:
        """
        Import AML rules from JSON file into Supabase
        
        Args:
            json_file_path: Path to the JSON file containing extracted rules
            
        Returns:
            Dict with import statistics
        """
        
        print(f"📥 Importing AML rules from: {json_file_path}")
        
        # Load JSON data
        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"❌ JSON file not found: {json_file_path}")
        except json.JSONDecodeError as e:
            raise ValueError(f"❌ Invalid JSON format: {e}")
        
        print(f"📊 Loaded JSON with {data.get('database_info', {}).get('total_rules', 'unknown')} rules")
        
        # Import statistics
        stats = {
            'documents_imported': 0,
            'rules_imported': 0,
            'keywords_imported': 0,
            'errors': [],
            'start_time': datetime.now(),
            'end_time': None
        }
        
        try:
            # Import each regulator's data
            regulators = data.get('regulators', {})
            
            for regulator_code, regulator_data in regulators.items():
                print(f"\n🏛️ Importing {regulator_code} data...")
                
                # Import documents and rules for this regulator
                regulator_stats = self._import_regulator_data(regulator_code, regulator_data)
                
                stats['documents_imported'] += regulator_stats['documents']
                stats['rules_imported'] += regulator_stats['rules']
                stats['keywords_imported'] += regulator_stats['keywords']
                stats['errors'].extend(regulator_stats['errors'])
                
            stats['end_time'] = datetime.now()
            stats['duration'] = (stats['end_time'] - stats['start_time']).total_seconds()
            
            print(f"\n✅ Import completed successfully!")
            print(f"📊 Documents imported: {stats['documents_imported']}")
            print(f"📊 Rules imported: {stats['rules_imported']}")
            print(f"📊 Keywords imported: {stats['keywords_imported']}")
            print(f"⏱️ Duration: {stats['duration']:.2f} seconds")
            
            if stats['errors']:
                print(f"⚠️ Errors encountered: {len(stats['errors'])}")
                for error in stats['errors'][:5]:  # Show first 5 errors
                    print(f"   - {error}")
            
            return stats
            
        except Exception as e:
            stats['end_time'] = datetime.now()
            stats['errors'].append(f"Critical error: {str(e)}")
            print(f"❌ Import failed: {e}")
            raise
    
    def _import_regulator_data(self, regulator_code: str, regulator_data: Dict) -> Dict:
        """Import data for a specific regulator"""
        
        stats = {
            'documents': 0,
            'rules': 0,
            'keywords': 0,
            'errors': []
        }
        
        # Get documents for this regulator
        documents = regulator_data.get('documents', [])
        
        for doc_data in documents:
            try:
                # Import document
                document_id = self._import_document(regulator_code, doc_data)
                stats['documents'] += 1
                
                # Import rules for this document
                rules = doc_data.get('extracted_rules', [])
                if not rules:
                    # Try alternative structure
                    rules = doc_data.get('rules', [])
                for rule_data in rules:
                    try:
                        rule_id = self._import_rule(document_id, rule_data)
                        stats['rules'] += 1
                        
                        # Import keywords for this rule
                        keywords_count = self._import_keywords(rule_id, rule_data)
                        stats['keywords'] += keywords_count
                        
                    except Exception as e:
                        error_msg = f"Failed to import rule {rule_data.get('rule_id', 'unknown')}: {e}"
                        stats['errors'].append(error_msg)
                        print(f"   ⚠️ {error_msg}")
                
            except Exception as e:
                error_msg = f"Failed to import document {doc_data.get('document_id', 'unknown')}: {e}"
                stats['errors'].append(error_msg)
                print(f"   ⚠️ {error_msg}")
        
        return stats
    
    def _import_document(self, regulator_code: str, doc_data: Dict) -> str:
        """Import a regulatory document"""
        
        document_data = {
            'document_id': doc_data['document_id'],
            'regulator_code': regulator_code,
            'title': doc_data['title'],
            'url': doc_data.get('url'),
            'document_type': doc_data.get('document_type'),
            'effective_date': doc_data.get('effective_date'),
            'status': 'active',
            'original_language': doc_data.get('language', 'en').split('(')[0].strip().lower(),
            'translated': 'translated' in doc_data.get('language', '').lower(),
            'extraction_confidence': doc_data.get('extraction_confidence', 0.8)
        }
        
        # Try to insert document
        url = f"{self.base_url}/regulatory_documents"
        
        response = requests.post(url, headers=self.headers, json=document_data)
        
        if response.status_code == 201:
            print(f"   📄 Imported document: {doc_data['document_id']}")
        elif response.status_code == 409 or 'duplicate key' in response.text.lower():
            # Update existing document
            update_url = f"{self.base_url}/regulatory_documents?document_id=eq.{doc_data['document_id']}"
            update_headers = {**self.headers, 'Prefer': 'return=minimal'}
            response = requests.patch(update_url, headers=update_headers, json=document_data)
            if response.status_code in [200, 204]:
                print(f"   📄 Updated document: {doc_data['document_id']}")
            else:
                raise Exception(f"Failed to update document: {response.status_code} - {response.text}")
        else:
            raise Exception(f"Failed to insert document: {response.status_code} - {response.text}")
        
        return doc_data['document_id']
    
    def _import_rule(self, document_id: str, rule_data: Dict) -> str:
        """Import an AML rule"""
        
        # Parse threshold information - handle both direct and nested formats
        threshold_amount = rule_data.get('threshold_amount')
        threshold_currency = rule_data.get('threshold_currency')
        
        # Extract from trigger if available
        trigger = rule_data.get('trigger', {})
        reporting_details = rule_data.get('reporting_details', {})
        
        # If no direct threshold, try to extract from description or trigger
        if not threshold_amount and 'description' in rule_data:
            threshold_amount, threshold_currency = self._extract_threshold_from_text(
                rule_data['description']
            )
        
        # Extract reporting authority
        reporting_authority = rule_data.get('reporting_authority')
        if not reporting_authority and reporting_details:
            reporting_authority = reporting_details.get('authority')
        
        # Extract applies_to information
        applies_to = rule_data.get('applies_to', [])
        if trigger and 'applies_to' in trigger:
            if isinstance(trigger['applies_to'], str):
                applies_to = [trigger['applies_to']]
            elif isinstance(trigger['applies_to'], list):
                applies_to = trigger['applies_to']
        
        # Build main_points and conditions from available data
        main_points = rule_data.get('main_points', [])
        conditions = rule_data.get('conditions', [])
        
        # Add trigger information to conditions if available
        if trigger:
            for key, value in trigger.items():
                if key not in ['applies_to'] and value:
                    conditions.append(f"{key}: {value}")
        
        # Add action required to main points
        if 'action_required' in rule_data:
            main_points.append(f"Action required: {rule_data['action_required']}")
        
        rule_db_data = {
            'rule_id': rule_data['rule_id'],
            'document_id': document_id,
            'rule_type': rule_data['rule_type'],
            'title': rule_data['title'],
            'description': rule_data['description'],
            'conditions': json.dumps(conditions),
            'main_points': json.dumps(main_points),
            'threshold_amount': threshold_amount,
            'threshold_currency': threshold_currency,
            'reporting_authority': reporting_authority,
            'reporting_timeframe': rule_data.get('reporting_timeframe'),
            'applies_to': json.dumps(applies_to),
            'required_approval': rule_data.get('required_approval'),
            'monitoring_frequency': rule_data.get('monitoring_frequency'),
            'ownership_threshold': rule_data.get('ownership_threshold'),
            'exceptions': json.dumps(rule_data.get('exceptions', [])),
            'update_frequency': rule_data.get('update_frequency'),
            'confidence': rule_data.get('confidence', 0.8),
            'manual_review_required': rule_data.get('confidence', 0.8) < 0.7
        }
        
        # Try to insert rule
        url = f"{self.base_url}/aml_rules"
        
        response = requests.post(url, headers=self.headers, json=rule_db_data)
        
        if response.status_code == 201:
            print(f"     📋 Imported rule: {rule_data['rule_id']}")
        elif response.status_code == 409 or 'duplicate key' in response.text.lower():
            # Update existing rule
            update_url = f"{self.base_url}/aml_rules?rule_id=eq.{rule_data['rule_id']}"
            update_headers = {**self.headers, 'Prefer': 'return=minimal'}
            response = requests.patch(update_url, headers=update_headers, json=rule_db_data)
            if response.status_code in [200, 204]:
                print(f"     📋 Updated rule: {rule_data['rule_id']}")
            else:
                raise Exception(f"Failed to update rule: {response.status_code} - {response.text}")
        else:
            raise Exception(f"Failed to insert rule: {response.status_code} - {response.text}")
        
        return rule_data['rule_id']
    
    def _import_keywords(self, rule_id: str, rule_data: Dict) -> int:
        """Extract and import keywords for a rule"""
        
        keywords = set()
        
        # Extract keywords from title
        title_keywords = self._extract_keywords_from_text(rule_data.get('title', ''))
        keywords.update(title_keywords)
        
        # Extract keywords from description
        desc_keywords = self._extract_keywords_from_text(rule_data.get('description', ''))
        keywords.update(desc_keywords)
        
        # Extract keywords from conditions and main points
        for condition in rule_data.get('conditions', []):
            if isinstance(condition, str):
                cond_keywords = self._extract_keywords_from_text(condition)
                keywords.update(cond_keywords)
        
        for point in rule_data.get('main_points', []):
            if isinstance(point, str):
                point_keywords = self._extract_keywords_from_text(point)
                keywords.update(point_keywords)
        
        # Add rule type as keyword
        keywords.add(rule_data.get('rule_type', '').replace('_', ' '))
        
        # Filter and score keywords
        filtered_keywords = []
        for keyword in keywords:
            if len(keyword) >= 3 and keyword.lower() not in ['the', 'and', 'for', 'with', 'from', 'that', 'this']:
                relevance_score = self._calculate_keyword_relevance(keyword, rule_data)
                filtered_keywords.append({
                    'rule_id': rule_id,
                    'keyword': keyword.lower(),
                    'relevance_score': relevance_score
                })
        
        # Insert keywords in batches
        if filtered_keywords:
            try:
                # Delete existing keywords for this rule
                delete_url = f"{self.base_url}/rule_keywords?rule_id=eq.{rule_id}"
                requests.delete(delete_url, headers=self.headers)
                
                # Insert new keywords
                keywords_url = f"{self.base_url}/rule_keywords"
                response = requests.post(keywords_url, headers=self.headers, json=filtered_keywords)
                
                if response.status_code == 201:
                    print(f"       🔍 Imported {len(filtered_keywords)} keywords for {rule_id}")
                else:
                    print(f"       ⚠️ Failed to import keywords for {rule_id}: {response.status_code}")
                    return 0
                    
            except Exception as e:
                print(f"       ⚠️ Failed to import keywords for {rule_id}: {e}")
                return 0
        
        return len(filtered_keywords)
    
    def _extract_threshold_from_text(self, text: str) -> tuple:
        """Extract threshold amount and currency from text"""
        
        if not text or not isinstance(text, str):
            return None, None
            
        # Look for amount patterns
        amount_patterns = [
            r'(\d{1,3}(?:,\d{3})*)\s*(CHF|SGD|HKD|USD|EUR)',
            r'(CHF|SGD|HKD|USD|EUR)\s*(\d{1,3}(?:,\d{3})*)',
            r'amount.*?(\d{1,3}(?:,\d{3})*)',
            r'exceeding.*?(\d{1,3}(?:,\d{3})*)'
        ]
        
        for pattern in amount_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                groups = match.groups()
                if len(groups) == 2:
                    # Try to determine which is amount and which is currency
                    if groups[0].replace(',', '').isdigit():
                        amount = float(groups[0].replace(',', ''))
                        currency = groups[1].upper()
                    else:
                        amount = float(groups[1].replace(',', ''))
                        currency = groups[0].upper()
                    return amount, currency
                elif len(groups) == 1 and groups[0].replace(',', '').isdigit():
                    amount = float(groups[0].replace(',', ''))
                    # Try to find currency in the same text
                    currency_match = re.search(r'\b(CHF|SGD|HKD|USD|EUR)\b', text, re.IGNORECASE)
                    if currency_match:
                        return amount, currency_match.group(1).upper()
                    return amount, None
        
        return None, None

    def _extract_threshold_from_conditions(self, conditions: List[str]) -> tuple:
        """Extract threshold amount and currency from conditions"""
        
        for condition in conditions:
            if isinstance(condition, str):
                # Look for amount patterns
                amount_patterns = [
                    r'(\d{1,3}(?:,\d{3})*)\s*(CHF|SGD|HKD|USD|EUR)',
                    r'(CHF|SGD|HKD|USD|EUR)\s*(\d{1,3}(?:,\d{3})*)',
                    r'amount.*?(\d{1,3}(?:,\d{3})*)',
                    r'exceeding.*?(\d{1,3}(?:,\d{3})*)'
                ]
                
                for pattern in amount_patterns:
                    match = re.search(pattern, condition, re.IGNORECASE)
                    if match:
                        groups = match.groups()
                        if len(groups) == 2:
                            # Try to determine which is amount and which is currency
                            if groups[0].replace(',', '').isdigit():
                                amount = float(groups[0].replace(',', ''))
                                currency = groups[1].upper()
                            else:
                                amount = float(groups[1].replace(',', ''))
                                currency = groups[0].upper()
                            return amount, currency
                        elif len(groups) == 1 and groups[0].replace(',', '').isdigit():
                            amount = float(groups[0].replace(',', ''))
                            # Try to find currency in the same condition
                            currency_match = re.search(r'\b(CHF|SGD|HKD|USD|EUR)\b', condition, re.IGNORECASE)
                            if currency_match:
                                return amount, currency_match.group(1).upper()
                            return amount, None
        
        return None, None
    
    def _extract_keywords_from_text(self, text: str) -> set:
        """Extract meaningful keywords from text"""
        
        if not text:
            return set()
        
        # Clean and split text
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        
        # Filter out common words
        stop_words = {
            'the', 'and', 'for', 'with', 'from', 'that', 'this', 'are', 'was', 'were',
            'been', 'have', 'has', 'had', 'will', 'would', 'could', 'should', 'may',
            'must', 'can', 'shall', 'not', 'but', 'all', 'any', 'some', 'such'
        }
        
        keywords = set()
        for word in words:
            if word not in stop_words and len(word) >= 3:
                keywords.add(word)
        
        return keywords
    
    def _calculate_keyword_relevance(self, keyword: str, rule_data: Dict) -> float:
        """Calculate relevance score for a keyword"""
        
        score = 1.0
        
        # Higher score for keywords in title
        if keyword.lower() in rule_data.get('title', '').lower():
            score += 0.5
        
        # Higher score for regulatory terms
        regulatory_terms = [
            'reporting', 'threshold', 'compliance', 'due', 'diligence', 'suspicious',
            'money', 'laundering', 'customer', 'identification', 'verification',
            'risk', 'assessment', 'monitoring', 'enhanced', 'politically', 'exposed'
        ]
        
        if keyword.lower() in regulatory_terms:
            score += 0.3
        
        # Higher score for currency codes
        if keyword.upper() in ['CHF', 'SGD', 'HKD', 'USD', 'EUR']:
            score += 0.4
        
        # Higher score for numbers (amounts, percentages)
        if any(char.isdigit() for char in keyword):
            score += 0.2
        
        return min(score, 2.0)  # Cap at 2.0
    
    def test_connection(self) -> bool:
        """Test the Supabase connection"""
        
        try:
            url = f"{self.base_url}/regulators?select=regulator_code&limit=1"
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 200:
                print("✅ Supabase connection test successful")
                return True
            else:
                print(f"❌ Supabase connection test failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Supabase connection test failed: {e}")
            return False
    
    def get_import_summary(self) -> Dict:
        """Get summary of current data in database"""
        
        try:
            # Get total counts
            rules_url = f"{self.base_url}/aml_rules?select=id"
            docs_url = f"{self.base_url}/regulatory_documents?select=id"
            keywords_url = f"{self.base_url}/rule_keywords?select=id"
            
            rules_response = requests.get(rules_url, headers=self.headers)
            docs_response = requests.get(docs_url, headers=self.headers)
            keywords_response = requests.get(keywords_url, headers=self.headers)
            
            total_rules = len(rules_response.json()) if rules_response.status_code == 200 else 0
            total_docs = len(docs_response.json()) if docs_response.status_code == 200 else 0
            total_keywords = len(keywords_response.json()) if keywords_response.status_code == 200 else 0
            
            # Get counts by regulator
            by_regulator = []
            for reg_code in ['MAS', 'FINMA', 'HKMA']:
                reg_rules_url = f"{self.base_url}/regulatory_documents?select=document_id&regulator_code=eq.{reg_code}"
                reg_response = requests.get(reg_rules_url, headers=self.headers)
                if reg_response.status_code == 200:
                    doc_ids = [doc['document_id'] for doc in reg_response.json()]
                    if doc_ids:
                        # Count rules for these documents
                        rules_count_url = f"{self.base_url}/aml_rules?select=id&document_id=in.({','.join(doc_ids)})"
                        rules_count_response = requests.get(rules_count_url, headers=self.headers)
                        if rules_count_response.status_code == 200:
                            rule_count = len(rules_count_response.json())
                            by_regulator.append({
                                'regulator_code': reg_code,
                                'total_rules': rule_count
                            })
            
            return {
                'total_rules': total_rules,
                'total_documents': total_docs,
                'total_keywords': total_keywords,
                'by_regulator': by_regulator
            }
            
        except Exception as e:
            print(f"⚠️ Failed to get import summary: {e}")
            return {}


# ============================================
# USAGE EXAMPLE
# ============================================

if __name__ == "__main__":
    # Initialize importer
    importer = SimpleAMLImporter()
    
    # Test connection
    if not importer.test_connection():
        print("❌ Cannot connect to Supabase. Check your credentials.")
        exit(1)
    
    # Look for JSON files to import
    import glob
    
    json_files = glob.glob("*.json")
    extracted_rules_files = [f for f in json_files if 'comprehensive_aml_database' in f.lower()]
    
    if not extracted_rules_files:
        print("❌ No comprehensive AML database JSON files found.")
        print("   Run the comprehensive processor first to generate the JSON output.")
        exit(1)
    
    # Import the most recent file
    latest_file = max(extracted_rules_files, key=os.path.getmtime)
    print(f"📁 Found JSON file: {latest_file}")
    
    # Perform import
    try:
        stats = importer.import_from_json(latest_file)
        
        # Show summary
        print("\n📊 DATABASE SUMMARY:")
        summary = importer.get_import_summary()
        print(f"   Total Rules: {summary.get('total_rules', 0)}")
        print(f"   Total Documents: {summary.get('total_documents', 0)}")
        print(f"   Total Keywords: {summary.get('total_keywords', 0)}")
        
        print("\n🏛️ BY REGULATOR:")
        for reg in summary.get('by_regulator', []):
            print(f"   {reg.get('regulator_code')}: {reg.get('total_rules', 0)} rules")
        
    except Exception as e:
        print(f"❌ Import failed: {e}")
        exit(1)