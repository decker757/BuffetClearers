"""
Test script for the /api/analyze-transactions endpoint
"""
import requests
import json

# Base URL for the API
BASE_URL = "http://localhost:5001"

def test_with_csv_file():
    """Test 1: Upload CSV file"""
    print("\n=== Test 1: Analyzing transactions from CSV file ===")

    url = f"{BASE_URL}/api/analyze-transactions?method=both&threshold=0.5&contamination=0.05"

    with open('Datasets/transactions_mock_1000_for_participants.csv', 'rb') as f:
        files = {'file': f}
        response = requests.post(url, files=files)

    if response.status_code == 200:
        result = response.json()
        print(f"✓ Success!")
        print(f"  Total transactions: {result['total_transactions']}")

        if 'xgboost' in result and 'error' not in result['xgboost']:
            print(f"\n  XGBoost Results:")
            print(f"    - Suspicious: {result['xgboost']['suspicious_count']} ({result['xgboost']['suspicious_percentage']}%)")
            print(f"    - Risk distribution: {result['xgboost']['risk_distribution']}")

        if 'isolation_forest' in result and 'error' not in result['isolation_forest']:
            print(f"\n  Isolation Forest Results:")
            print(f"    - Anomalies: {result['isolation_forest']['anomaly_count']} ({result['isolation_forest']['anomaly_percentage']}%)")
            print(f"    - Severity distribution: {result['isolation_forest']['severity_distribution']}")

        if 'consensus' in result:
            print(f"\n  Consensus:")
            print(f"    - Flagged by both: {result['consensus']['flagged_by_both']}")
            print(f"    - XGBoost only: {result['consensus']['flagged_by_xgboost_only']}")
            print(f"    - Isolation Forest only: {result['consensus']['flagged_by_isolation_forest_only']}")
    else:
        print(f"✗ Failed: {response.status_code}")
        print(response.text)


def test_with_json_data():
    """Test 2: Send JSON data"""
    print("\n=== Test 2: Analyzing transactions from JSON data ===")

    url = f"{BASE_URL}/api/analyze-transactions?method=xgboost&threshold=0.7"

    # Sample transaction data
    sample_transactions = [
        {
            "transaction_id": "TEST001",
            "amount": 50000,
            "fx_applied_rate": 1.35,
            "fx_market_rate": 1.32,
            "fx_spread_bps": 300,
            "daily_cash_total_customer": 100000,
            "daily_cash_txn_count": 5,
            "currency": "USD",
            "channel": "online",
            "product_type": "wire",
            "customer_type": "individual",
            "customer_risk_rating": "high",
            "originator_country": "US",
            "beneficiary_country": "RU",
            "booking_jurisdiction": "US",
            "regulator": "FINCEN",
            "customer_is_pep": "Yes",
            "travel_rule_complete": "No",
            "product_complex": "No"
        },
        {
            "transaction_id": "TEST002",
            "amount": 1000,
            "fx_applied_rate": 1.32,
            "fx_market_rate": 1.32,
            "fx_spread_bps": 0,
            "daily_cash_total_customer": 5000,
            "daily_cash_txn_count": 2,
            "currency": "EUR",
            "channel": "branch",
            "product_type": "deposit",
            "customer_type": "individual",
            "customer_risk_rating": "low",
            "originator_country": "US",
            "beneficiary_country": "US",
            "booking_jurisdiction": "US",
            "regulator": "FINCEN",
            "customer_is_pep": "No",
            "travel_rule_complete": "Yes",
            "product_complex": "No"
        }
    ]

    headers = {'Content-Type': 'application/json'}
    data = {'transactions': sample_transactions}

    response = requests.post(url, headers=headers, data=json.dumps(data))

    if response.status_code == 200:
        result = response.json()
        print(f"✓ Success!")
        print(f"  Total transactions: {result['total_transactions']}")

        if 'xgboost' in result and 'error' not in result['xgboost']:
            print(f"\n  XGBoost Results:")
            print(f"    - Suspicious: {result['xgboost']['suspicious_count']}")
            if result['xgboost']['suspicious_transactions']:
                print(f"    - Details:")
                for txn in result['xgboost']['suspicious_transactions']:
                    print(f"      • {txn['transaction_id']}: {txn['suspicion_probability']:.2%} risk")
    else:
        print(f"✗ Failed: {response.status_code}")
        print(response.text)


def test_train_models():
    """Test 3: Train models"""
    print("\n=== Test 3: Training models ===")

    url = f"{BASE_URL}/api/train-models?model=both"

    response = requests.post(url)

    if response.status_code == 200:
        result = response.json()
        print(f"✓ Success!")
        print(f"  Trained at: {result['trained_at']}")

        if 'xgboost' in result:
            print(f"\n  XGBoost: {result['xgboost']['status']}")
            if 'metrics' in result['xgboost']:
                metrics = result['xgboost']['metrics']
                print(f"    - ROC AUC: {metrics['roc_auc_score']:.4f}")

        if 'isolation_forest' in result:
            print(f"\n  Isolation Forest: {result['isolation_forest']['status']}")
    else:
        print(f"✗ Failed: {response.status_code}")
        print(response.text)


def test_health_check():
    """Test 4: Health check"""
    print("\n=== Test 4: Health check ===")

    url = f"{BASE_URL}/api/health"

    response = requests.get(url)

    if response.status_code == 200:
        result = response.json()
        print(f"✓ Success!")
        print(f"  Status: {result['status']}")
        print(f"  Version: {result['version']}")
    else:
        print(f"✗ Failed: {response.status_code}")


if __name__ == "__main__":
    print("=" * 60)
    print("Testing Transaction Analysis Endpoints")
    print("=" * 60)

    # Test health check first
    test_health_check()

    # Train models
    test_train_models()

    # Test with CSV file
    test_with_csv_file()

    # Test with JSON data
    test_with_json_data()

    print("\n" + "=" * 60)
    print("All tests complete!")
    print("=" * 60)
