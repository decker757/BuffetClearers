"""
Transaction AML Analyzer
Compares transaction data against AML rules in database to identify violations
"""

import pandas as pd
import requests
from simple_supabase_importer import SimpleAMLImporter
from datetime import datetime, timedelta
import re

class TransactionAMLAnalyzer:
    def __init__(self):
        self.importer = SimpleAMLImporter()
        self.violations = []
        
    def load_aml_rules(self):
        """Load AML rules from database"""
        print("📥 Loading AML rules from database...")
        
        rules_url = f"{self.importer.base_url}/aml_rules?select=*"
        response = requests.get(rules_url, headers=self.importer.headers)
        
        if response.status_code == 200:
            rules = response.json()
            print(f"✅ Loaded {len(rules)} AML rules")
            return rules
        else:
            print(f"❌ Error loading rules: {response.status_code}")
            return []
    
    def load_transactions(self, csv_path):
        """Load transaction data from CSV"""
        print(f"📥 Loading transactions from {csv_path}...")
        
        try:
            df = pd.read_csv(csv_path)
            print(f"✅ Loaded {len(df)} transactions")
            print(f"📊 Columns: {list(df.columns)}")
            return df
        except Exception as e:
            print(f"❌ Error loading transactions: {e}")
            return None
    
    def analyze_suspicious_transaction_reporting(self, transactions, rules):
        """Check STR compliance"""
        print("\n🚨 ANALYZING SUSPICIOUS TRANSACTION REPORTING...")
        
        # Get STR rules
        str_rules = [r for r in rules if r['rule_type'] == 'suspicious_transaction_reporting']
        print(f"Found {len(str_rules)} STR rules")
        
        violations = []
        
        # Check for transactions with suspicion but no STR filed
        suspicious_no_str = transactions[
            (transactions['suspicion_determined_datetime'].notna()) & 
            (transactions['str_filed_datetime'].isna())
        ]
        
        if len(suspicious_no_str) > 0:
            violations.append({
                'rule_type': 'suspicious_transaction_reporting',
                'violation': 'Suspicious transaction without STR filed',
                'count': len(suspicious_no_str),
                'transactions': suspicious_no_str['transaction_id'].tolist()[:5],  # First 5 examples
                'rule_reference': 'FINMA-STR-012 (reasonable grounds for suspicion → file STR)'
            })
        
        # Check for delayed STR filing (should be within reasonable time)
        if len(suspicious_no_str) == 0:
            print("✅ All suspicious transactions have STRs filed")
        
        return violations
    
    def analyze_threshold_reporting(self, transactions, rules):
        """Check threshold reporting compliance"""
        print("\n💰 ANALYZING THRESHOLD REPORTING...")
        
        # Get threshold rules
        threshold_rules = [r for r in rules if r['rule_type'] == 'threshold_reporting']
        print(f"Found {len(threshold_rules)} threshold rules")
        
        violations = []
        
        # Common AML thresholds (these would normally come from the rules)
        # For demo, using common regulatory thresholds
        thresholds = {
            'CHF': 10000,   # Switzerland
            'SGD': 20000,   # Singapore  
            'HKD': 120000,  # Hong Kong
            'USD': 10000,   # Common threshold
            'EUR': 10000,   # Common threshold
            'GBP': 10000    # Common threshold
        }
        
        large_transactions = []
        
        for currency, threshold in thresholds.items():
            large_txns = transactions[
                (transactions['currency'] == currency) & 
                (transactions['amount'] >= threshold)
            ]
            
            if len(large_txns) > 0:
                large_transactions.extend(large_txns.to_dict('records'))
        
        if large_transactions:
            violations.append({
                'rule_type': 'threshold_reporting',
                'violation': 'Large transactions requiring threshold reporting',
                'count': len(large_transactions),
                'transactions': [t['transaction_id'] for t in large_transactions[:5]],
                'rule_reference': 'FINMA-THRESHOLD-002 (reportable transactions above threshold)'
            })
        
        return violations
    
    def analyze_pep_due_diligence(self, transactions, rules):
        """Check PEP due diligence compliance"""
        print("\n👑 ANALYZING PEP DUE DILIGENCE...")
        
        violations = []
        
        # Check PEP transactions without Enhanced Due Diligence
        pep_transactions = transactions[transactions['customer_is_pep'] == True]
        
        if len(pep_transactions) > 0:
            # Check if EDD was performed
            pep_no_edd = pep_transactions[pep_transactions['edd_performed'] == False]
            
            if len(pep_no_edd) > 0:
                violations.append({
                    'rule_type': 'enhanced_due_diligence',
                    'violation': 'PEP transactions without Enhanced Due Diligence',
                    'count': len(pep_no_edd),
                    'transactions': pep_no_edd['transaction_id'].tolist()[:5],
                    'rule_reference': 'Enhanced Due Diligence required for PEPs'
                })
        
        return violations
    
    def analyze_sanctions_screening(self, transactions, rules):
        """Check sanctions screening compliance"""
        print("\n🎯 ANALYZING SANCTIONS SCREENING...")
        
        violations = []
        
        # Check transactions without sanctions screening
        no_screening = transactions[transactions['sanctions_screening'] == 'none']
        
        if len(no_screening) > 0:
            violations.append({
                'rule_type': 'sanctions_screening',
                'violation': 'Transactions without sanctions screening',
                'count': len(no_screening),
                'transactions': no_screening['transaction_id'].tolist()[:5],
                'rule_reference': 'All transactions must be screened against sanctions lists'
            })
        
        # Check for potential sanctions hits without proper handling
        potential_hits = transactions[transactions['sanctions_screening'] == 'potential']
        
        if len(potential_hits) > 0:
            violations.append({
                'rule_type': 'sanctions_screening',
                'violation': 'Potential sanctions hits requiring review',
                'count': len(potential_hits),
                'transactions': potential_hits['transaction_id'].tolist()[:5],
                'rule_reference': 'Potential sanctions matches require investigation'
            })
        
        return violations
    
    def analyze_kyc_compliance(self, transactions, rules):
        """Check KYC compliance"""
        print("\n📋 ANALYZING KYC COMPLIANCE...")
        
        violations = []
        
        # Convert date strings to datetime for comparison
        try:
            transactions['kyc_due_date'] = pd.to_datetime(transactions['kyc_due_date'], format='%d/%m/%Y', errors='coerce')
            current_date = datetime.now()
            
            # Check for expired KYC
            expired_kyc = transactions[transactions['kyc_due_date'] < current_date]
            
            if len(expired_kyc) > 0:
                violations.append({
                    'rule_type': 'customer_due_diligence',
                    'violation': 'Transactions with expired KYC',
                    'count': len(expired_kyc),
                    'transactions': expired_kyc['transaction_id'].tolist()[:5],
                    'rule_reference': 'Current KYC required for all transactions'
                })
        except Exception as e:
            print(f"⚠️ KYC date analysis error: {e}")
        
        return violations
    
    def run_full_analysis(self, csv_path):
        """Run complete AML analysis"""
        print("🔍 STARTING COMPREHENSIVE AML ANALYSIS")
        print("=" * 60)
        
        # Load data
        rules = self.load_aml_rules()
        transactions = self.load_transactions(csv_path)
        
        if not rules or transactions is None:
            print("❌ Cannot proceed - missing data")
            return
        
        print(f"\n📊 ANALYSIS SCOPE:")
        print(f"   Transactions: {len(transactions)}")
        print(f"   AML Rules: {len(rules)}")
        if 'regulator' in transactions.columns:
            print(f"   Regulators: {transactions['regulator'].unique()}")
        
        # Run all analyses
        all_violations = []
        
        all_violations.extend(self.analyze_suspicious_transaction_reporting(transactions, rules))
        all_violations.extend(self.analyze_threshold_reporting(transactions, rules))
        all_violations.extend(self.analyze_pep_due_diligence(transactions, rules))
        all_violations.extend(self.analyze_sanctions_screening(transactions, rules))
        all_violations.extend(self.analyze_kyc_compliance(transactions, rules))
        
        # Summary report
        print("\n" + "=" * 60)
        print("🚨 AML COMPLIANCE VIOLATIONS DETECTED")
        print("=" * 60)
        
        if not all_violations:
            print("✅ NO VIOLATIONS FOUND - All transactions appear compliant!")
        else:
            print(f"❌ Found {len(all_violations)} types of violations:")
            
            for i, violation in enumerate(all_violations, 1):
                print(f"\n{i}. {violation['violation'].upper()}")
                print(f"   Rule Type: {violation['rule_type']}")
                print(f"   Count: {violation['count']} transactions")
                print(f"   Examples: {violation['transactions']}")
                print(f"   Rule Reference: {violation['rule_reference']}")
        
        print("\n" + "=" * 60)
        print("✅ ANALYSIS COMPLETE")
        print("=" * 60)
        
        return all_violations


if __name__ == "__main__":
    analyzer = TransactionAMLAnalyzer()
    
    # Path to your transaction CSV
    csv_path = r"c:\Users\ihsan\OneDrive\Documents\GitHub\BuffetClearers\Datasets\transactions_mock_1000_for_participants.csv"
    
    # Run analysis
    violations = analyzer.run_full_analysis(csv_path)