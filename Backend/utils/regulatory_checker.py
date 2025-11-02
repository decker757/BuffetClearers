"""
Regulatory Compliance Checker
Checks transactions against AML regulatory rules stored in Supabase
"""
import pandas as pd
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


class RegulatoryChecker:
    """Check transactions against regulatory rules"""

    def __init__(self, supabase_client):
        """
        Initialize regulatory checker

        Args:
            supabase_client: Supabase client instance
        """
        self.supabase = supabase_client

    def check_transaction(self, transaction: Dict) -> List[Dict]:
        """
        Check a single transaction against all active regulatory rules

        Args:
            transaction: Transaction data dictionary

        Returns:
            List of regulatory violations found
        """
        violations = []

        try:
            # Get all active regulatory rules
            rules = self._get_active_rules()

            if not rules:
                logger.warning("No active regulatory rules found in database")
                return violations

            # Check each rule
            for rule in rules:
                violation = self._check_rule(transaction, rule)
                if violation:
                    violations.append(violation)

            logger.info(f"Transaction {transaction.get('transaction_id', 'UNKNOWN')} - {len(violations)} violations found")

        except Exception as e:
            logger.error(f"Error checking regulations: {e}", exc_info=True)

        return violations

    def _get_active_rules(self) -> List[Dict]:
        """
        Get all currently active regulatory rules from Supabase

        Returns:
            List of active rule dictionaries
        """
        try:
            # Query Supabase for all rules (use v_complete_rules view for full context)
            # The actual schema doesn't have is_active, it checks document status
            response = self.supabase.table('v_complete_rules')\
                .select('*')\
                .execute()

            if response.data:
                logger.info(f"Loaded {len(response.data)} regulatory rules from view")
                return response.data

            # Fallback to direct aml_rules table
            response = self.supabase.table('aml_rules')\
                .select('*')\
                .execute()

            if response.data:
                logger.info(f"Loaded {len(response.data)} regulatory rules")
                return response.data

            logger.warning("No regulatory rules found in database")
            return []

        except Exception as e:
            logger.error(f"Failed to load regulatory rules: {e}")
            return []

    def _check_rule(self, transaction: Dict, rule: Dict) -> Optional[Dict]:
        """
        Check if a transaction violates a specific regulatory rule

        Args:
            transaction: Transaction data
            rule: Regulatory rule to check

        Returns:
            Violation dictionary if rule is violated, None otherwise
        """
        try:
            rule_id = rule.get('rule_id', rule.get('id', 'UNKNOWN'))
            rule_type = rule.get('rule_type', '')

            # Get trigger conditions from either 'conditions' or 'trigger_conditions'
            trigger_conditions = rule.get('conditions', rule.get('trigger_conditions', {}))

            # Parse trigger conditions (assuming JSON format)
            if isinstance(trigger_conditions, str):
                import json
                trigger_conditions = json.loads(trigger_conditions)

            # If no trigger conditions and no threshold, use rule_type based checking
            if not trigger_conditions and not rule.get('threshold_amount'):
                return None

            # Check various condition types
            violated = False
            matched_conditions = []

            # Check threshold_amount from schema (threshold_reporting rules)
            threshold_amount = rule.get('threshold_amount')
            if threshold_amount:
                amount = transaction.get('amount', 0)
                threshold_currency = rule.get('threshold_currency', 'USD')
                txn_currency = transaction.get('currency', 'USD')

                # Only compare if currencies match or do basic conversion
                if txn_currency == threshold_currency and amount >= threshold_amount:
                    violated = True
                    matched_conditions.append(
                        f"Amount {txn_currency} {amount:,.2f} exceeds reporting threshold "
                        f"{threshold_currency} {threshold_amount:,.2f}"
                    )

            # Amount threshold checks from conditions JSONB
            if 'amount_threshold' in trigger_conditions:
                threshold = trigger_conditions['amount_threshold']
                amount = transaction.get('amount', 0)

                if amount >= threshold:
                    violated = True
                    matched_conditions.append(f"Amount ${amount:,.2f} exceeds threshold ${threshold:,.2f}")

            # Country checks
            if 'prohibited_countries' in trigger_conditions:
                prohibited = trigger_conditions['prohibited_countries']
                orig_country = transaction.get('originator_country', '')
                benef_country = transaction.get('beneficiary_country', '')

                if orig_country in prohibited or benef_country in prohibited:
                    violated = True
                    matched_conditions.append(f"Transaction involves prohibited country: {orig_country} or {benef_country}")

            # PEP checks
            if 'pep_enhanced_dd' in trigger_conditions:
                if trigger_conditions['pep_enhanced_dd']:
                    is_pep = str(transaction.get('customer_is_pep', '')).lower() in ['yes', 'true', '1']
                    if is_pep:
                        violated = True
                        matched_conditions.append("Customer is PEP - Enhanced Due Diligence required")

            # High-risk customer checks
            if 'high_risk_customer_monitoring' in trigger_conditions:
                if trigger_conditions['high_risk_customer_monitoring']:
                    risk_rating = str(transaction.get('customer_risk_rating', '')).lower()
                    if risk_rating in ['high', 'critical']:
                        violated = True
                        matched_conditions.append(f"High-risk customer: {risk_rating}")

            # Travel rule checks
            if 'travel_rule_required' in trigger_conditions:
                if trigger_conditions['travel_rule_required']:
                    travel_complete = str(transaction.get('travel_rule_complete', '')).lower()
                    if travel_complete in ['no', 'false', '0', '']:
                        violated = True
                        matched_conditions.append("Travel rule compliance incomplete")

            # Cash intensity checks
            if 'cash_intensive_business' in trigger_conditions:
                daily_count = transaction.get('daily_cash_txn_count', 0)
                if daily_count > trigger_conditions.get('transaction_frequency_threshold', 20):
                    violated = True
                    matched_conditions.append(f"High transaction frequency: {daily_count} transactions")

            # If rule was violated, return violation details
            if violated:
                return {
                    'rule_id': rule_id,
                    'rule_title': rule.get('title', 'Unknown Rule'),
                    'rule_type': rule_type,
                    'rule_source': rule.get('regulator_code', rule.get('source', 'Unknown Source')),
                    'regulator_name': rule.get('regulator_name', ''),
                    'jurisdiction': rule.get('jurisdiction', ''),
                    'document_id': rule.get('document_id', ''),
                    'document_title': rule.get('document_title', ''),
                    'severity': rule.get('severity_level', 'medium'),  # Not in schema, default medium
                    'category': rule.get('rule_type', 'general'),
                    'matched_conditions': matched_conditions,
                    'required_actions': rule.get('main_points', []),
                    'reporting_authority': rule.get('reporting_authority', ''),
                    'reporting_timeframe': rule.get('reporting_timeframe', ''),
                    'description': rule.get('description', '')[:200],  # Truncate
                    'confidence': rule.get('confidence', 0.5)
                }

            return None

        except Exception as e:
            logger.error(f"Error checking rule {rule.get('rule_id', 'UNKNOWN')}: {e}")
            return None

    def check_batch(self, transactions_df: pd.DataFrame) -> Dict[str, List[Dict]]:
        """
        Check a batch of transactions against regulatory rules

        Args:
            transactions_df: DataFrame of transactions

        Returns:
            Dictionary mapping transaction_id to list of violations
        """
        results = {}

        for idx, row in transactions_df.iterrows():
            transaction = row.to_dict()
            txn_id = transaction.get('transaction_id', f'TXN_{idx}')

            violations = self.check_transaction(transaction)
            if violations:
                results[txn_id] = violations

        logger.info(f"Batch check complete: {len(results)} transactions with violations out of {len(transactions_df)}")

        return results

    def get_violation_summary(self, violations: List[Dict]) -> Dict:
        """
        Create a summary of violations

        Args:
            violations: List of violation dictionaries

        Returns:
            Summary statistics
        """
        if not violations:
            return {
                'total_violations': 0,
                'severity_breakdown': {},
                'category_breakdown': {},
                'sources': []
            }

        # Count by severity
        severity_counts = {}
        category_counts = {}
        sources = set()

        for v in violations:
            severity = v.get('severity', 'unknown')
            category = v.get('category', 'unknown')
            source = v.get('rule_source', 'unknown')

            severity_counts[severity] = severity_counts.get(severity, 0) + 1
            category_counts[category] = category_counts.get(category, 0) + 1
            sources.add(source)

        return {
            'total_violations': len(violations),
            'severity_breakdown': severity_counts,
            'category_breakdown': category_counts,
            'sources': list(sources),
            'most_severe': max(violations, key=lambda x: self._severity_score(x.get('severity')))
        }

    @staticmethod
    def _severity_score(severity: str) -> int:
        """Convert severity to numeric score"""
        scores = {
            'critical': 4,
            'high': 3,
            'medium': 2,
            'low': 1
        }
        return scores.get(severity.lower(), 0)
