"""
Fraud Scoring and Alert Rules
Combines multiple model outputs and applies rule-based alerts
Integrates with Supabase for dynamic rule management
"""
import pandas as pd
from typing import Optional, Dict, List
from supabase import Client


class FraudScorer:
    """Unified fraud risk scoring system with Supabase integration"""

    # Default alert thresholds (fallback if Supabase unavailable)
    ALERT_RULES = {
        'high_value': {'threshold': 1000000, 'weight': 25, 'description': 'Transaction amount exceeds $1M'},
        'very_high_value': {'threshold': 10000000, 'weight': 40, 'description': 'Transaction amount exceeds $10M'},
        'unusual_fx_spread': {'threshold': 0.05, 'weight': 15, 'description': 'FX rate spread > 5%'},
        'extreme_fx_spread': {'threshold': 0.10, 'weight': 25, 'description': 'FX rate spread > 10%'},
        'large_daily_ratio': {'threshold': 0.7, 'weight': 20, 'description': 'Transaction > 70% of daily total'},
        'pep_customer': {'threshold': None, 'weight': 15, 'description': 'Customer is PEP'},
        'high_risk_customer': {'threshold': None, 'weight': 20, 'description': 'Customer risk rating is high'},
        'travel_rule_incomplete': {'threshold': None, 'weight': 10, 'description': 'Travel rule not complete'},
        'high_risk_country': {'threshold': None, 'weight': 15, 'description': 'High-risk country involved'},
        'frequent_transactions': {'threshold': 20, 'weight': 10, 'description': 'More than 20 daily transactions'},
        'round_amount': {'threshold': None, 'weight': 5, 'description': 'Suspiciously round transaction amount'},
    }

    # High-risk countries (FATF grey/black list examples)
    HIGH_RISK_COUNTRIES = ['KP', 'IR', 'SY', 'MM', 'AF', 'YE', 'IQ', 'SS']

    def __init__(self, supabase_client: Optional[Client] = None):
        """
        Initialize FraudScorer with optional Supabase integration

        Args:
            supabase_client: Optional Supabase client for dynamic rule loading
        """
        self.supabase = supabase_client
        self.supabase_rules = []

        if self.supabase:
            self.load_rules_from_supabase()

    def load_rules_from_supabase(self) -> bool:
        """
        Load AML rules from Supabase database

        Returns:
            True if rules loaded successfully, False otherwise
        """
        if not self.supabase:
            print("⚠️ No Supabase client configured")
            return False

        try:
            # Fetch threshold-based rules from aml_rules table
            response = self.supabase.table('aml_rules').select(
                'rule_id, title, description, rule_type, threshold_amount, '
                'threshold_currency, conditions, confidence'
            ).eq('rule_type', 'threshold_reporting').execute()

            self.supabase_rules = response.data
            print(f"✅ Loaded {len(self.supabase_rules)} rules from Supabase")

            # Update ALERT_RULES dynamically from Supabase
            self._sync_threshold_rules()

            return True

        except Exception as e:
            print(f"⚠️ Failed to load rules from Supabase: {e}")
            return False

    def _sync_threshold_rules(self):
        """
        Synchronize threshold rules from Supabase into ALERT_RULES
        Maps Supabase rules to the internal alert system
        """
        for rule in self.supabase_rules:
            rule_id = rule.get('rule_id')
            threshold_amount = rule.get('threshold_amount')

            if threshold_amount and rule_id:
                # Create a standardized rule entry
                self.ALERT_RULES[rule_id] = {
                    'threshold': float(threshold_amount),
                    'weight': 20,  # Default weight, can be adjusted
                    'description': rule.get('description', rule.get('title', '')),
                    'currency': rule.get('threshold_currency', 'USD'),
                    'confidence': rule.get('confidence', 0.5),
                    'source': 'supabase'
                }

        print(f"✅ Synchronized {len([r for r in self.ALERT_RULES.values() if r.get('source') == 'supabase'])} rules from Supabase")

    def get_applicable_rules(self, transaction: Dict) -> List[Dict]:
        """
        Get applicable Supabase rules for a given transaction

        Args:
            transaction: Transaction dictionary

        Returns:
            List of applicable rules with details
        """
        if not self.supabase:
            return []

        applicable_rules = []
        amount = transaction.get('amount', 0)
        currency = transaction.get('currency', 'USD')

        for rule in self.supabase_rules:
            threshold = rule.get('threshold_amount')
            rule_currency = rule.get('threshold_currency', 'USD')

            # Simple threshold check (can be enhanced with currency conversion)
            if threshold and currency == rule_currency and amount >= threshold:
                applicable_rules.append({
                    'rule_id': rule['rule_id'],
                    'title': rule['title'],
                    'description': rule['description'],
                    'threshold': threshold,
                    'confidence': rule.get('confidence', 0.5)
                })

        return applicable_rules

    def calculate_unified_fraud_score(self, xgb_prob=None, iso_score=None, alerts=None):
        """
        Calculate unified fraud risk score (0-100)

        Args:
            xgb_prob: XGBoost suspicion probability (0-1)
            iso_score: Isolation Forest anomaly score (lower = more anomalous)
            alerts: List of triggered alerts

        Returns:
            Fraud score from 0-100
        """
        score = 0
        weights = []

        # XGBoost contribution (40% weight if available)
        if xgb_prob is not None:
            score += xgb_prob * 40
            weights.append(40)

        # Isolation Forest contribution (40% weight if available)
        if iso_score is not None:
            # Normalize isolation forest score (typically ranges from -0.5 to 0.5)
            # Lower scores = more anomalous, so invert and normalize
            iso_normalized = max(0, min(1, (0.5 - iso_score) / 1.0))
            score += iso_normalized * 40
            weights.append(40)

        # Alert rules contribution (20% weight)
        if alerts and len(alerts) > 0:
            alert_score = min(20, len(alerts) * 5)  # Cap at 20 points
            score += alert_score
            weights.append(20)

        # Normalize if not all components available
        if sum(weights) > 0:
            score = (score / sum(weights)) * 100

        return min(100, max(0, score))

    def check_alert_rules(self, transaction):
        """
        Check transaction against alert rules

        Args:
            transaction: Dictionary or Series with transaction data

        Returns:
            List of triggered alerts
        """
        alerts = []

        # Convert to dict if Series
        if isinstance(transaction, pd.Series):
            transaction = transaction.to_dict()

        # Calculate derived features
        fx_anomaly = abs(transaction.get('fx_applied_rate', 0) - transaction.get('fx_market_rate', 0))
        amount_ratio = transaction.get('amount', 0) / max(transaction.get('daily_cash_total_customer', 1), 1)

        # High value alerts
        amount = transaction.get('amount', 0)
        if amount > self.ALERT_RULES['very_high_value']['threshold']:
            alerts.append({
                'rule': 'very_high_value',
                'severity': 'critical',
                'description': self.ALERT_RULES['very_high_value']['description'],
                'value': float(amount),
                'weight': self.ALERT_RULES['very_high_value']['weight']
            })
        elif amount > self.ALERT_RULES['high_value']['threshold']:
            alerts.append({
                'rule': 'high_value',
                'severity': 'high',
                'description': self.ALERT_RULES['high_value']['description'],
                'value': float(amount),
                'weight': self.ALERT_RULES['high_value']['weight']
            })

        # FX spread alerts
        if fx_anomaly > self.ALERT_RULES['extreme_fx_spread']['threshold']:
            alerts.append({
                'rule': 'extreme_fx_spread',
                'severity': 'critical',
                'description': self.ALERT_RULES['extreme_fx_spread']['description'],
                'value': float(fx_anomaly),
                'weight': self.ALERT_RULES['extreme_fx_spread']['weight']
            })
        elif fx_anomaly > self.ALERT_RULES['unusual_fx_spread']['threshold']:
            alerts.append({
                'rule': 'unusual_fx_spread',
                'severity': 'medium',
                'description': self.ALERT_RULES['unusual_fx_spread']['description'],
                'value': float(fx_anomaly),
                'weight': self.ALERT_RULES['unusual_fx_spread']['weight']
            })

        # Daily ratio alert
        if amount_ratio > self.ALERT_RULES['large_daily_ratio']['threshold']:
            alerts.append({
                'rule': 'large_daily_ratio',
                'severity': 'medium',
                'description': self.ALERT_RULES['large_daily_ratio']['description'],
                'value': float(amount_ratio),
                'weight': self.ALERT_RULES['large_daily_ratio']['weight']
            })

        # PEP alert
        pep_value = str(transaction.get('customer_is_pep', '')).lower()
        if pep_value in ['yes', 'true', '1']:
            alerts.append({
                'rule': 'pep_customer',
                'severity': 'medium',
                'description': self.ALERT_RULES['pep_customer']['description'],
                'value': 'Yes',
                'weight': self.ALERT_RULES['pep_customer']['weight']
            })

        # High-risk customer
        risk_rating = str(transaction.get('customer_risk_rating', '')).lower()
        if risk_rating in ['high', 'critical']:
            alerts.append({
                'rule': 'high_risk_customer',
                'severity': 'high',
                'description': self.ALERT_RULES['high_risk_customer']['description'],
                'value': transaction.get('customer_risk_rating'),
                'weight': self.ALERT_RULES['high_risk_customer']['weight']
            })

        # Travel rule incomplete
        travel_rule = str(transaction.get('travel_rule_complete', '')).lower()
        if travel_rule in ['no', 'false', '0']:
            alerts.append({
                'rule': 'travel_rule_incomplete',
                'severity': 'low',
                'description': self.ALERT_RULES['travel_rule_incomplete']['description'],
                'value': 'No',
                'weight': self.ALERT_RULES['travel_rule_incomplete']['weight']
            })

        # High-risk countries
        originator = str(transaction.get('originator_country', '')).upper()
        beneficiary = str(transaction.get('beneficiary_country', '')).upper()

        if originator in self.HIGH_RISK_COUNTRIES or beneficiary in self.HIGH_RISK_COUNTRIES:
            alerts.append({
                'rule': 'high_risk_country',
                'severity': 'high',
                'description': self.ALERT_RULES['high_risk_country']['description'],
                'value': f"{originator} -> {beneficiary}",
                'weight': self.ALERT_RULES['high_risk_country']['weight']
            })

        # Frequent transactions
        txn_count = transaction.get('daily_cash_txn_count', 0)
        if txn_count > self.ALERT_RULES['frequent_transactions']['threshold']:
            alerts.append({
                'rule': 'frequent_transactions',
                'severity': 'low',
                'description': self.ALERT_RULES['frequent_transactions']['description'],
                'value': int(txn_count),
                'weight': self.ALERT_RULES['frequent_transactions']['weight']
            })

        # Round amount detection (e.g., exactly 100000, 1000000)
        if amount > 0 and amount % 100000 == 0:
            alerts.append({
                'rule': 'round_amount',
                'severity': 'low',
                'description': FraudScorer.ALERT_RULES['round_amount']['description'],
                'value': float(amount),
                'weight': FraudScorer.ALERT_RULES['round_amount']['weight']
            })

        return alerts

    @staticmethod
    def get_risk_category(fraud_score):
        """
        Categorize fraud risk score

        Args:
            fraud_score: Score from 0-100

        Returns:
            Risk category string
        """
        if fraud_score >= 80:
            return 'CRITICAL'
        elif fraud_score >= 60:
            return 'HIGH'
        elif fraud_score >= 40:
            return 'MEDIUM'
        elif fraud_score >= 20:
            return 'LOW'
        else:
            return 'MINIMAL'
