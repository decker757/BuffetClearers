"""
Example: Using FraudScorer with Supabase Integration
Shows how to link rules from Supabase into fraud_scoring.py
"""

from supabase import create_client
from fraud_scoring import FraudScorer
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def example_with_supabase():
    """
    Example 1: Using FraudScorer with Supabase for dynamic rule loading
    """
    print("=" * 60)
    print("EXAMPLE 1: FraudScorer with Supabase Integration")
    print("=" * 60)

    # Initialize Supabase client
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_KEY')

    supabase = create_client(supabase_url, supabase_key)

    # Initialize FraudScorer with Supabase
    fraud_scorer = FraudScorer(supabase_client=supabase)

    # Sample transaction
    transaction = {
        'transaction_id': 'TX_12345',
        'amount': 15000000,  # $15M
        'currency': 'USD',
        'fx_applied_rate': 1.25,
        'fx_market_rate': 1.20,
        'daily_cash_total_customer': 20000000,
        'customer_is_pep': True,
        'customer_risk_rating': 'High',
        'travel_rule_complete': False,
        'originator_country': 'IR',  # Iran - high risk
        'beneficiary_country': 'US',
        'daily_cash_txn_count': 25
    }

    # Check alert rules (now includes Supabase rules)
    alerts = fraud_scorer.check_alert_rules(transaction)

    print(f"\n✅ Triggered {len(alerts)} alerts:")
    for alert in alerts:
        print(f"  - [{alert['severity'].upper()}] {alert['description']}")
        print(f"    Value: {alert['value']}, Weight: {alert['weight']}")

    # Get applicable Supabase rules
    applicable_rules = fraud_scorer.get_applicable_rules(transaction)

    print(f"\n📋 Applicable Supabase rules: {len(applicable_rules)}")
    for rule in applicable_rules:
        print(f"  - {rule['title']}")
        print(f"    Threshold: {rule['threshold']} {transaction['currency']}")

    # Calculate fraud score
    fraud_score = fraud_scorer.calculate_unified_fraud_score(
        xgb_prob=0.85,
        iso_score=-0.3,
        alerts=alerts
    )

    print(f"\n🎯 Fraud Score: {fraud_score:.2f}/100")
    print(f"📊 Risk Category: {fraud_scorer.get_risk_category(fraud_score)}")


def example_without_supabase():
    """
    Example 2: Using FraudScorer without Supabase (fallback mode)
    """
    print("\n" + "=" * 60)
    print("EXAMPLE 2: FraudScorer without Supabase (Fallback)")
    print("=" * 60)

    # Initialize without Supabase - uses default rules only
    fraud_scorer = FraudScorer()

    transaction = {
        'amount': 5500000,  # $5.5M
        'currency': 'USD',
        'fx_applied_rate': 1.05,
        'fx_market_rate': 1.02,
        'daily_cash_total_customer': 7000000,
        'customer_is_pep': False,
        'customer_risk_rating': 'Medium',
        'travel_rule_complete': True,
        'originator_country': 'US',
        'beneficiary_country': 'UK',
        'daily_cash_txn_count': 5
    }

    alerts = fraud_scorer.check_alert_rules(transaction)

    print(f"\n✅ Triggered {len(alerts)} alerts:")
    for alert in alerts:
        print(f"  - [{alert['severity'].upper()}] {alert['description']}")

    fraud_score = fraud_scorer.calculate_unified_fraud_score(
        xgb_prob=0.45,
        iso_score=0.1,
        alerts=alerts
    )

    print(f"\n🎯 Fraud Score: {fraud_score:.2f}/100")
    print(f"📊 Risk Category: {fraud_scorer.get_risk_category(fraud_score)}")


def example_reload_rules():
    """
    Example 3: Reloading rules from Supabase (e.g., after rules updated)
    """
    print("\n" + "=" * 60)
    print("EXAMPLE 3: Reloading Rules from Supabase")
    print("=" * 60)

    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_KEY')

    supabase = create_client(supabase_url, supabase_key)
    fraud_scorer = FraudScorer(supabase_client=supabase)

    print(f"\nInitial rules count: {len(fraud_scorer.ALERT_RULES)}")

    # Simulate rule update in Supabase
    print("\n📝 Simulating rule update in Supabase...")

    # Reload rules
    success = fraud_scorer.load_rules_from_supabase()

    if success:
        print(f"✅ Rules reloaded successfully")
        print(f"Updated rules count: {len(fraud_scorer.ALERT_RULES)}")
    else:
        print("❌ Failed to reload rules")


def main():
    """Run all examples"""
    try:
        # Example 1: With Supabase
        example_with_supabase()

        # Example 2: Without Supabase
        example_without_supabase()

        # Example 3: Reload rules
        example_reload_rules()

    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure you have:")
        print("1. Created a .env file with SUPABASE_URL and SUPABASE_KEY")
        print("2. Run the Supabase schema SQL to create the aml_rules table")
        print("3. Populated the aml_rules table with some rules")


if __name__ == "__main__":
    main()
