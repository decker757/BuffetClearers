
"""
Supabase AML System Manager
Complete database operations for AML monitoring system
"""
from supabase import create_client, Client
from datetime import datetime
import json
import requests
from typing import Dict, List, Optional, Any
import pandas as pd


class SupabaseAMLSystem:
    """
    Complete AML system using Supabase for all data operations
    """
    
    def __init__(self, supabase_url: str, supabase_key: str, jina_api_key: str, groq_api_key: str):
        """Initialize the AML system with API credentials"""
        self.supabase: Client = create_client(supabase_url, supabase_key)
        self.jina_api_key = jina_api_key
        self.groq_api_key = groq_api_key
        
        print("✅ Supabase AML System initialized")
    
    # ============================================
    # REGULATORY RULE MANAGEMENT
    # ============================================
    
    def ingest_regulation(self, regulation: Dict, changed_by: str = "system") -> Dict:
        """
        Ingest new regulation or update existing one
        Handles versioning automatically
        """
        # Check if rule exists
        existing = self.supabase.table('regulatory_rules').select('*').eq(
            'rule_id', regulation['rule_id']
        ).execute()
        
        if existing.data:
            return self._update_rule(regulation, existing.data[0], changed_by)
        else:
            return self._create_new_rule(regulation, changed_by)
    
    def _create_new_rule(self, regulation: Dict, changed_by: str) -> Dict:
        """Create new rule (version 1)"""
        print(f"📥 Creating new rule: {regulation['rule_id']}")
        
        # 1. Insert master record
        master = self.supabase.table('regulatory_rules').insert({
            'rule_id': regulation['rule_id'],
            'source': regulation['source'],
            'rule_number': regulation.get('rule_number'),
            'title': regulation['title'],
            'category': regulation.get('category'),
            'effective_date': regulation.get('effective_date'),
            'current_version': 1
        }).execute()
        
        # 2. Get Jina embedding
        embedding = self._get_jina_embedding(regulation['content'])
        
        # 3. Insert version 1 with embedding
        version = self.supabase.table('rule_versions').insert({
            'rule_id': regulation['rule_id'],
            'version': 1,
            'content': regulation['content'],
            'summary': regulation.get('summary'),
            'trigger_conditions': regulation.get('trigger_conditions'),
            'required_actions': regulation.get('required_actions'),
            'severity_level': regulation.get('severity_level', 'medium'),
            'embedding': embedding,
            'effective_from': regulation.get('effective_date')
        }).execute()
        
        print(f"✅ Rule {regulation['rule_id']} created successfully")
        
        return {
            'status': 'created',
            'rule_id': regulation['rule_id'],
            'version': 1
        }
    
    def _update_rule(self, regulation: Dict, existing: Dict, changed_by: str) -> Dict:
        """Update existing rule (create new version)"""
        old_version = existing['current_version']
        new_version = old_version + 1
        
        print(f"🔄 Updating rule {regulation['rule_id']}: v{old_version} → v{new_version}")
        
        # 1. Close old version
        self.supabase.table('rule_versions').update({
            'effective_to': datetime.now().date().isoformat()
        }).eq('rule_id', regulation['rule_id']).eq('version', old_version).execute()
        
        # 2. Get embedding for new version
        embedding = self._get_jina_embedding(regulation['content'])
        
        # 3. Insert new version
        self.supabase.table('rule_versions').insert({
            'rule_id': regulation['rule_id'],
            'version': new_version,
            'content': regulation['content'],
            'summary': regulation.get('summary'),
            'trigger_conditions': regulation.get('trigger_conditions'),
            'required_actions': regulation.get('required_actions'),
            'severity_level': regulation.get('severity_level', 'medium'),
            'embedding': embedding,
            'effective_from': datetime.now().date().isoformat()
        }).execute()
        
        # 4. Update master record
        self.supabase.table('regulatory_rules').update({
            'current_version': new_version
        }).eq('rule_id', regulation['rule_id']).execute()
        
        print(f"✅ Rule {regulation['rule_id']} updated to version {new_version}")
        
        return {
            'status': 'updated',
            'rule_id': regulation['rule_id'],
            'old_version': old_version,
            'new_version': new_version
        }
    
    def search_regulations(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        Semantic search using pgvector
        """
        # Get query embedding
        query_embedding = self._get_jina_embedding(query)
        
        # Use RPC for vector search
        try:
            results = self.supabase.rpc('match_regulations', {
                'query_embedding': query_embedding,
                'match_threshold': 0.5,
                'match_count': top_k
            }).execute()
            
            return results.data
        except Exception as e:
            print(f"⚠️ Vector search failed: {e}")
            # Fallback to text search
            results = self.supabase.table('rule_versions').select(
                'rule_id, version, content'
            ).limit(top_k).execute()
            return results.data
    
    # ============================================
    # TRANSACTION ANALYSIS
    # ============================================
    
    def insert_transaction(self, transaction: Dict) -> str:
        """Insert a new transaction into the database"""
        result = self.supabase.table('transactions').insert({
            'transaction_id': transaction['transaction_id'],
            'booking_jurisdiction': transaction.get('booking_jurisdiction'),
            'regulator': transaction.get('regulator'),
            'booking_datetime': transaction.get('booking_datetime'),
            'value_date': transaction.get('value_date'),
            'amount': transaction['amount'],
            'currency': transaction['currency'],
            'channel': transaction.get('channel'),
            'product_type': transaction.get('product_type'),
            'originator_name': transaction.get('originator_name'),
            'originator_account': transaction.get('originator_account'),
            'originator_country': transaction.get('originator_country'),
            'beneficiary_name': transaction.get('beneficiary_name'),
            'beneficiary_account': transaction.get('beneficiary_account'),
            'beneficiary_country': transaction.get('beneficiary_country'),
            'customer_id': transaction.get('customer_id'),
            'customer_type': transaction.get('customer_type'),
            'customer_risk_rating': transaction.get('customer_risk_rating'),
            'customer_is_pep': transaction.get('customer_is_pep', False),
            'sanctions_screening': transaction.get('sanctions_screening'),
            'raw_data': transaction
        }).execute()
        
        return result.data[0]['id']
    
    def analyze_transaction(self, transaction: Dict) -> Dict:
        """
        Complete transaction analysis workflow
        """
        print(f"\n🔍 Analyzing transaction: {transaction['transaction_id']}")
        
        # 1. Insert transaction
        try:
            tx_id = self.insert_transaction(transaction)
        except Exception as e:
            print(f"⚠️ Transaction already exists, using existing record")
        
        # 2. Calculate risk score
        risk_score, risk_factors = self.calculate_risk_score(transaction)
        
        # 3. Search for relevant regulations
        query = self._build_regulation_query(transaction)
        relevant_rules = self.search_regulations(query, top_k=5)
        
        # 4. Get detailed analysis from Groq
        analysis = self._analyze_with_groq(transaction, relevant_rules, risk_score, risk_factors)
        
        # 5. Update transaction with analysis
        self.supabase.table('transactions').update({
            'risk_score': risk_score,
            'flagged': risk_score >= 70,
            'analysis_summary': json.dumps(analysis)
        }).eq('transaction_id', transaction['transaction_id']).execute()
        
        # 6. Track rule applications
        for rule in relevant_rules:
            self.supabase.table('rule_applications').insert({
                'transaction_id': transaction['transaction_id'],
                'rule_id': rule['rule_id'],
                'rule_version': rule['version'],
                'matched': True,
                'risk_contribution': 10
            }).execute()
        
        # 7. Create alert if high risk
        if risk_score >= 70:
            alert = self._create_alert(transaction, risk_score, risk_factors, relevant_rules)
            print(f"🚨 Alert created: {alert['alert_id']} (Severity: {alert['severity']})")
        
        # 8. Audit log
        self._log_audit('transaction', transaction['transaction_id'], 'analyzed')
        
        print(f"✅ Analysis complete - Risk Score: {risk_score}/100")
        
        return {
            'transaction_id': transaction['transaction_id'],
            'risk_score': risk_score,
            'risk_factors': risk_factors,
            'regulations_matched': len(relevant_rules),
            'analysis': analysis
        }
    
    def calculate_risk_score(self, transaction: Dict) -> tuple[int, List[str]]:
        """
        Calculate risk score based on multiple factors
        Returns: (score, risk_factors)
        """
        score = 0
        risk_factors = []
        
        # 1. Customer Risk Rating (0-25 points)
        if transaction.get('customer_risk_rating') == 'High':
            score += 25
            risk_factors.append("High-risk customer rating")
        elif transaction.get('customer_risk_rating') == 'Medium':
            score += 15
            risk_factors.append("Medium-risk customer rating")
        else:
            score += 5
        
        # 2. Sanctions Screening (0-30 points)
        if transaction.get('sanctions_screening') == 'potential':
            score += 30
            risk_factors.append("Potential sanctions match")
        
        # 3. High-Risk Jurisdictions (0-20 points)
        high_risk_countries = ['IR', 'RU', 'KP', 'SY']
        orig_country = transaction.get('originator_country', '')
        benef_country = transaction.get('beneficiary_country', '')
        
        if orig_country in high_risk_countries or benef_country in high_risk_countries:
            score += 20
            risk_factors.append(f"High-risk jurisdiction: {orig_country} → {benef_country}")
        
        # 4. PEP Status (0-15 points)
        if transaction.get('customer_is_pep'):
            score += 15
            risk_factors.append("Politically Exposed Person (PEP)")
        
        # 5. Large Cash Transaction (0-15 points)
        if transaction.get('channel') == 'Cash' and transaction.get('amount', 0) > 10000:
            score += 15
            risk_factors.append(f"Large cash transaction: {transaction['amount']} {transaction['currency']}")
        
        # 6. EDD Compliance (0-10 points)
        if transaction.get('edd_required') and not transaction.get('edd_performed'):
            score += 10
            risk_factors.append("EDD required but not performed")
        
        # 7. Travel Rule Non-Compliance (0-10 points)
        if not transaction.get('travel_rule_complete', True):
            score += 10
            risk_factors.append("Travel rule not complete")
        
        # 8. Unverified Cash (0-10 points)
        if transaction.get('channel') == 'Cash' and not transaction.get('cash_id_verified', True):
            score += 10
            risk_factors.append("Cash transaction without ID verification")
        
        # 9. Unusual FX Spread (0-5 points)
        if transaction.get('fx_spread_bps', 0) > 100:
            score += 5
            risk_factors.append(f"Unusual FX spread: {transaction['fx_spread_bps']} bps")
        
        return min(score, 100), risk_factors
    
    def _create_alert(self, transaction: Dict, risk_score: int, risk_factors: List[str], 
                      regulations: List[Dict]) -> Dict:
        """Create alert for high-risk transaction"""
        
        # Determine routing
        if risk_score >= 90:
            assigned_to = 'legal'
            severity = 'critical'
        elif risk_score >= 70:
            assigned_to = 'compliance'
            severity = 'high'
        elif risk_score >= 50:
            assigned_to = 'compliance'
            severity = 'medium'
        else:
            assigned_to = 'front_office'
            severity = 'low'
        
        alert_data = {
            'alert_id': f"ALT_{int(datetime.now().timestamp())}_{transaction['transaction_id'][:8]}",
            'transaction_id': transaction['transaction_id'],
            'alert_type': 'high_risk_transaction',
            'severity': severity,
            'title': f"High Risk Transaction: {transaction['transaction_id']}",
            'description': f"Transaction flagged with risk score {risk_score}/100. {len(risk_factors)} risk factors identified.",
            'regulations_violated': [r['rule_id'] for r in regulations],
            'risk_factors': risk_factors,
            'assigned_to': assigned_to,
            'status': 'open'
        }
        
        result = self.supabase.table('alerts').insert(alert_data).execute()
        
        return result.data[0]
    
    # ============================================
    # GROQ INTEGRATION
    # ============================================
    
    def _analyze_with_groq(self, transaction: Dict, regulations: List[Dict], 
                           risk_score: int, risk_factors: List[str]) -> Dict:
        """Use Groq for detailed transaction analysis"""
        
        from groq import Groq
        client = Groq(api_key=self.groq_api_key)
        
        # Build prompt
        prompt = f"""
Analyze this financial transaction for AML compliance:

TRANSACTION DETAILS:
- ID: {transaction['transaction_id']}
- Amount: {transaction['amount']} {transaction['currency']}
- Channel: {transaction.get('channel')}
- Origin: {transaction.get('originator_country')} → Beneficiary: {transaction.get('beneficiary_country')}
- Customer Risk: {transaction.get('customer_risk_rating')}
- PEP: {transaction.get('customer_is_pep')}
- Sanctions Screening: {transaction.get('sanctions_screening')}

RISK SCORE: {risk_score}/100

RISK FACTORS:
{chr(10).join(f'- {rf}' for rf in risk_factors)}

RELEVANT REGULATIONS:
{chr(10).join(f'- {r.get("title", "Unknown")}' for r in regulations[:3])}

Provide a concise analysis with:
1. Key concerns (2-3 sentences)
2. Recommended actions (bullet points)
3. Compliance officer notes

Keep response under 200 words.
"""
        
        try:
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=500
            )
            
            return {
                'analysis': response.choices[0].message.content,
                'model': 'llama-3.3-70b-versatile',
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            print(f"⚠️ Groq analysis failed: {e}")
            return {
                'analysis': f"Risk score: {risk_score}. Factors: {', '.join(risk_factors[:3])}",
                'model': 'fallback',
                'timestamp': datetime.now().isoformat()
            }
    
    # ============================================
    # JINA AI INTEGRATION
    # ============================================
    
    def _get_jina_embedding(self, text: str) -> List[float]:
        """Get embedding from Jina AI"""
        headers = {
            "Authorization": f"Bearer {self.jina_api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": "jina-embeddings-v3",
            "input": [text[:8000]],  # Limit text length
            "task": "retrieval.passage",
            "dimensions": 1024
        }
        
        try:
            response = requests.post(
                "https://api.jina.ai/v1/embeddings",
                headers=headers,
                json=data,
                timeout=30
            )
            response.raise_for_status()
            return response.json()['data'][0]['embedding']
        except Exception as e:
            print(f"⚠️ Jina embedding failed: {e}")
            # Return zero vector as fallback
            return [0.0] * 1024
    
    # ============================================
    # HELPER METHODS
    # ============================================
    
    def _build_regulation_query(self, transaction: Dict) -> str:
        """Build query for regulation search"""
        return f"""
AML compliance check for:
- Transaction type: {transaction.get('product_type')}
- Amount: {transaction['amount']} {transaction['currency']}
- Channel: {transaction.get('channel')}
- Customer risk: {transaction.get('customer_risk_rating')}
- Jurisdictions: {transaction.get('originator_country')} to {transaction.get('beneficiary_country')}
- PEP: {transaction.get('customer_is_pep')}
- Sanctions screening: {transaction.get('sanctions_screening')}
"""
    
    def _log_audit(self, entity_type: str, entity_id: str, action: str, 
                   user_id: str = None, details: Dict = None):
        """Log action to audit trail"""
        self.supabase.table('audit_trail').insert({
            'entity_type': entity_type,
            'entity_id': entity_id,
            'action': action,
            'user_id': user_id,
            'details': details
        }).execute()
    
    # ============================================
    # DASHBOARD QUERIES
    # ============================================
    
    def get_dashboard_stats(self) -> Dict:
        """Get real-time dashboard statistics"""
        
        stats = {}
        
        # Total transactions
        tx_count = self.supabase.table('transactions').select(
            'id', count='exact'
        ).execute()
        stats['total_transactions'] = tx_count.count
        
        # Open alerts
        open_alerts = self.supabase.table('alerts').select(
            'id', count='exact'
        ).eq('status', 'open').execute()
        stats['open_alerts'] = open_alerts.count
        
        # High risk transactions
        high_risk = self.supabase.table('transactions').select(
            'id', count='exact'
        ).gte('risk_score', 70).execute()
        stats['high_risk_count'] = high_risk.count
        
        # Alerts by severity
        alerts = self.supabase.table('alerts').select('severity').eq('status', 'open').execute()
        severity_counts = {}
        for alert in alerts.data:
            sev = alert['severity']
            severity_counts[sev] = severity_counts.get(sev, 0) + 1
        stats['alerts_by_severity'] = severity_counts
        
        # Recent high-risk transactions
        recent = self.supabase.table('transactions').select(
            'transaction_id, amount, currency, risk_score, customer_risk_rating'
        ).gte('risk_score', 70).order('created_at', desc=True).limit(10).execute()
        stats['recent_high_risk'] = recent.data
        
        return stats
    
    def get_open_alerts(self, assigned_to: Optional[str] = None) -> List[Dict]:
        """Get all open alerts"""
        query = self.supabase.table('alerts').select('*').eq('status', 'open')
        
        if assigned_to:
            query = query.eq('assigned_to', assigned_to)
        
        query = query.order('severity', desc=True).order('created_at', desc=True)
        
        result = query.execute()
        return result.data
    
    # ============================================
    # BATCH OPERATIONS
    # ============================================
    
    def bulk_load_transactions(self, csv_path: str) -> Dict:
        """Load transactions from CSV file"""
        print(f"📊 Loading transactions from {csv_path}")
        
        df = pd.read_csv(csv_path)
        print(f"Found {len(df)} transactions")
        
        loaded = 0
        errors = 0
        
        for idx, row in df.iterrows():
            try:
                transaction = row.to_dict()
                self.insert_transaction(transaction)
                loaded += 1
                
                if (idx + 1) % 100 == 0:
                    print(f"  Loaded {idx + 1}/{len(df)} transactions...")
                    
            except Exception as e:
                errors += 1
                if errors < 5:  # Only print first few errors
                    print(f"  ⚠️ Error loading row {idx}: {e}")
        
        print(f"✅ Bulk load complete: {loaded} loaded, {errors} errors")
        
        return {
            'loaded': loaded,
            'errors': errors,
            'total': len(df)
        }


# ============================================
# USAGE EXAMPLE
# ============================================

if __name__ == "__main__":
    # Initialize system
    aml_system = SupabaseAMLSystem(
        supabase_url="YOUR_SUPABASE_URL",
        supabase_key="YOUR_SUPABASE_KEY",
        jina_api_key="YOUR_JINA_KEY",
        groq_api_key="YOUR_GROQ_KEY"
    )
    
    # Example: Analyze a transaction
    sample_transaction = {
        'transaction_id': 'TEST_TX_001',
        'amount': 50000,
        'currency': 'USD',
        'channel': 'Cash',
        'originator_country': 'RU',
        'beneficiary_country': 'CH',
        'customer_risk_rating': 'High',
        'customer_is_pep': True,
        'sanctions_screening': 'potential',
        'edd_required': True,
        'edd_performed': False
    }
    
    result = aml_system.analyze_transaction(sample_transaction)
    print(f"\nAnalysis Result: {json.dumps(result, indent=2)}")