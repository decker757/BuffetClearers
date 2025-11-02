# Enhanced Transaction Analysis API Documentation

## Overview

The Enhanced Transaction Analysis API provides comprehensive fraud detection with:
- **Dual ML Models**: XGBoost (supervised) + Isolation Forest (unsupervised)
- **Unified Fraud Score**: 0-100 composite risk score
- **Rule-Based Alerts**: 11+ high-risk trigger rules
- **Explainability**: Feature importance and risk factor explanations
- **Audit Trail**: Full traceability with execution IDs and model versions
- **Feedback Loop**: Manual review and decision tracking

---

## Enhanced Response Structure

```json
{
  // === AUDIT TRACEABILITY ===
  "execution_id": "550e8400-e29b-41d4-a716-446655440000",
  "model_version": {
    "xgboost": "1.0.0",
    "isolation_forest": "1.0.0",
    "fraud_scorer": "1.0.0"
  },
  "data_source": "csv_upload:transactions.csv",
  "analysis_timestamp": "2025-11-02T14:30:00.123456",

  // === ANALYSIS CONFIGURATION ===
  "analysis_config": {
    "method": "both",
    "xgboost_threshold": 0.5,
    "isolation_forest_contamination": 0.05,
    "include_explanations": true
  },

  // === SUMMARY STATISTICS ===
  "total_transactions": 1000,
  "summary_statistics": {
    "total_transactions": 1000,
    "fraud_scores": {
      "average": 23.45,
      "median": 18.2,
      "max": 95.6,
      "min": 2.1
    },
    "risk_categories": {
      "critical": 12,    // fraud_score >= 80
      "high": 45,        // fraud_score 60-79
      "medium": 123,     // fraud_score 40-59
      "low": 320,        // fraud_score 20-39
      "minimal": 500     // fraud_score < 20
    },
    "high_risk_percentage": 5.7,
    "total_alerts_triggered": 234,
    "unique_alert_types": 8
  },

  // === MODEL RESULTS ===
  "model_results": {
    "xgboost": {
      "suspicious_count": 45,
      "suspicious_percentage": 4.5,
      "threshold": 0.5,
      "risk_distribution": {
        "high": 15,
        "medium": 30,
        "low": 955
      },
      "feature_importance": [
        {"feature": "amount", "importance": 0.234},
        {"feature": "fx_anomaly", "importance": 0.187},
        {"feature": "customer_risk_rating", "importance": 0.156}
      ]
    },
    "isolation_forest": {
      "anomaly_count": 50,
      "anomaly_percentage": 5.0,
      "contamination": 0.05,
      "severity_distribution": {
        "high": 20,
        "medium": 20,
        "low": 10
      }
    }
  },

  // === ALERTS ===
  "alerts": {
    "summary": {
      "high_value": {
        "count": 23,
        "severity": "high",
        "description": "Transaction amount exceeds $1M"
      },
      "unusual_fx_spread": {
        "count": 15,
        "severity": "medium",
        "description": "FX rate spread > 5%"
      }
      // ... other alert types
    },
    "total_triggered": 234,
    "critical_alerts": 8,
    "high_alerts": 45
  },

  // === ENHANCED TRANSACTIONS (Top 100 by fraud score) ===
  "enhanced_transactions": [
    {
      "transaction_id": "TXN_001",
      "amount": 5000000.0,
      "fraud_risk_score": 87.5,        // UNIFIED SCORE 0-100
      "risk_category": "CRITICAL",

      "model_scores": {
        "xgboost_probability": 0.9234,
        "isolation_forest_score": -0.345
      },

      "alerts": [
        {
          "rule": "very_high_value",
          "severity": "critical",
          "description": "Transaction amount exceeds $10M",
          "value": 5000000.0,
          "weight": 40
        },
        {
          "rule": "pep_customer",
          "severity": "medium",
          "description": "Customer is PEP",
          "value": "Yes",
          "weight": 15
        }
      ],
      "alert_count": 2,

      "context": {
        "currency": "USD",
        "channel": "online",
        "originator_country": "US",
        "beneficiary_country": "RU",
        "customer_type": "individual",
        "customer_risk_rating": "high",
        "customer_is_pep": "Yes"
      },

      "explanation": {
        "top_features": [
          {"feature": "amount", "importance": 0.234},
          {"feature": "fx_anomaly", "importance": 0.187},
          {"feature": "customer_risk_rating", "importance": 0.156}
        ],
        "risk_factors": [
          {"factor": "High transaction amount", "value": 5000000.0},
          {"factor": "Customer is PEP", "value": "Yes"},
          {"factor": "High-risk customer", "value": "high"}
        ]
      },

      "feedback": {
        "reviewed": false,
        "reviewer": null,
        "decision": null,
        "notes": null,
        "reviewed_at": null
      }
    }
  ],

  // === CONSENSUS (when method=both) ===
  "consensus": {
    "high_confidence_count": 12,
    "high_confidence_percentage": 1.2,
    "description": "Transactions flagged as suspicious by both models"
  }
}
```

---

## Fraud Risk Score Calculation

### Unified Score (0-100)

The `fraud_risk_score` combines:

1. **XGBoost Probability** (40% weight)
   - Supervised learning model
   - Based on historical fraud patterns

2. **Isolation Forest Score** (40% weight)
   - Unsupervised anomaly detection
   - Detects unusual patterns

3. **Alert Rules** (20% weight)
   - Rule-based triggers
   - Each alert adds points

### Risk Categories

| Score Range | Category | Action Required |
|-------------|----------|-----------------|
| 80-100 | CRITICAL | Immediate investigation |
| 60-79 | HIGH | Priority review |
| 40-59 | MEDIUM | Standard review |
| 20-39 | LOW | Monitor |
| 0-19 | MINIMAL | Routine processing |

---

## Alert Rules

### 11 Built-in Alert Rules

| Rule | Threshold | Weight | Severity | Description |
|------|-----------|--------|----------|-------------|
| `very_high_value` | $10M+ | 40 | CRITICAL | Extremely large transaction |
| `high_value` | $1M+ | 25 | HIGH | Large transaction |
| `extreme_fx_spread` | >10% | 25 | CRITICAL | Extreme FX rate deviation |
| `unusual_fx_spread` | >5% | 15 | MEDIUM | Unusual FX rate spread |
| `large_daily_ratio` | >70% | 20 | MEDIUM | Large % of daily activity |
| `high_risk_customer` | - | 20 | HIGH | Customer rated high-risk |
| `pep_customer` | - | 15 | MEDIUM | Politically exposed person |
| `high_risk_country` | FATF list | 15 | HIGH | High-risk jurisdiction |
| `travel_rule_incomplete` | - | 10 | LOW | Missing travel rule data |
| `frequent_transactions` | >20/day | 10 | LOW | Unusual frequency |
| `round_amount` | Divisible by 100K | 5 | LOW | Suspiciously round amount |

### High-Risk Countries

Based on FATF grey/black lists:
- `KP` (North Korea)
- `IR` (Iran)
- `SY` (Syria)
- `MM` (Myanmar)
- `AF` (Afghanistan)
- `YE` (Yemen)
- `IQ` (Iraq)
- `SS` (South Sudan)

---

## API Endpoints

### 1. Analyze Transactions (Enhanced)

**POST** `/api/analyze-transactions`

#### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `method` | string | `both` | `xgboost`, `isolation_forest`, or `both` |
| `threshold` | float | `0.5` | XGBoost suspicion threshold (0-1) |
| `contamination` | float | `0.05` | Isolation Forest anomaly rate (0-1) |
| `include_explanations` | boolean | `true` | Include feature importance |

#### Example Request

```bash
curl -X POST \
  "http://localhost:5001/api/analyze-transactions?method=both&include_explanations=true" \
  -F "file=@transactions.csv"
```

#### Example with JSON

```bash
curl -X POST \
  "http://localhost:5001/api/analyze-transactions" \
  -H "Content-Type: application/json" \
  -d '{
    "transactions": [
      {
        "transaction_id": "TXN001",
        "amount": 2500000,
        "fx_applied_rate": 1.35,
        "fx_market_rate": 1.32,
        "fx_spread_bps": 300,
        "daily_cash_total_customer": 3000000,
        "daily_cash_txn_count": 15,
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
      }
    ]
  }'
```

---

### 2. Submit Feedback

**POST** `/api/transaction-feedback`

Submit manual review decisions for transactions.

#### Request Body

```json
{
  "execution_id": "550e8400-e29b-41d4-a716-446655440000",
  "transaction_id": "TXN001",
  "reviewer": "analyst@company.com",
  "decision": "confirmed_fraud",
  "notes": "Customer verified as sanctioned entity"
}
```

#### Valid Decisions

- `confirmed_fraud` - Transaction confirmed as fraudulent
- `false_positive` - Legitimate transaction, model error
- `needs_investigation` - Requires further review
- `legitimate` - Transaction approved as legitimate

#### Example

```bash
curl -X POST \
  "http://localhost:5001/api/transaction-feedback" \
  -H "Content-Type: application/json" \
  -d '{
    "execution_id": "550e8400-e29b-41d4-a716-446655440000",
    "transaction_id": "TXN001",
    "reviewer": "analyst@company.com",
    "decision": "confirmed_fraud",
    "notes": "Matches known fraud pattern"
  }'
```

---

### 3. Get Feedback

**GET** `/api/transaction-feedback/<execution_id>`

Retrieve feedback for a specific analysis execution.

#### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `transaction_id` | string | No | Filter by specific transaction |

#### Example

```bash
# Get all feedback for execution
curl "http://localhost:5001/api/transaction-feedback/550e8400-e29b-41d4-a716-446655440000"

# Get feedback for specific transaction
curl "http://localhost:5001/api/transaction-feedback/550e8400-e29b-41d4-a716-446655440000?transaction_id=TXN001"
```

---

## Use Cases

### 1. Real-time Transaction Screening

```python
import requests

response = requests.post(
    'http://localhost:5001/api/analyze-transactions',
    json={'transactions': [transaction_data]}
)

result = response.json()
fraud_score = result['enhanced_transactions'][0]['fraud_risk_score']

if fraud_score >= 80:
    # Block transaction
    block_transaction()
elif fraud_score >= 60:
    # Hold for review
    queue_for_review(result['execution_id'], transaction_id)
else:
    # Process normally
    approve_transaction()
```

### 2. Batch Analysis with Feedback Loop

```python
# Step 1: Analyze batch
response = requests.post(
    'http://localhost:5001/api/analyze-transactions',
    files={'file': open('daily_transactions.csv', 'rb')}
)

execution_id = response.json()['execution_id']
high_risk = [t for t in response.json()['enhanced_transactions']
             if t['fraud_risk_score'] >= 60]

# Step 2: Analyst reviews
for txn in high_risk:
    decision = analyst_review(txn)

    # Submit feedback
    requests.post(
        'http://localhost:5001/api/transaction-feedback',
        json={
            'execution_id': execution_id,
            'transaction_id': txn['transaction_id'],
            'reviewer': 'analyst@company.com',
            'decision': decision
        }
    )
```

### 3. Model Monitoring

```python
# Analyze feedback to improve models
feedback_response = requests.get(
    f'http://localhost:5001/api/transaction-feedback/{execution_id}'
)

feedback = feedback_response.json()['feedback']

false_positives = [f for f in feedback if f['decision'] == 'false_positive']
confirmed_fraud = [f for f in feedback if f['decision'] == 'confirmed_fraud']

print(f"False positive rate: {len(false_positives) / len(feedback) * 100}%")
```

---

## Best Practices

### 1. **Set Appropriate Thresholds**
- Start with default threshold (0.5)
- Adjust based on false positive/negative rates
- Use different thresholds for different transaction types

### 2. **Use Both Models**
- XGBoost: Good for known fraud patterns
- Isolation Forest: Catches novel fraud
- Consensus: High confidence when both agree

### 3. **Review High-Risk Transactions**
- CRITICAL (80+): Immediate block/review
- HIGH (60-79): Manual review required
- MEDIUM (40-59): Automated checks + sampling

### 4. **Leverage Explanations**
- Use `top_features` to understand model decisions
- Check `risk_factors` for specific red flags
- Review `alerts` for rule violations

### 5. **Close the Feedback Loop**
- Always submit feedback for reviewed transactions
- Track false positive/negative rates
- Retrain models periodically with feedback data

---

## Performance

### Response Times
- Single transaction: ~50ms
- Batch (100 txns): ~500ms
- Batch (1000 txns): ~3s
- First request (model training): ~20s

### Scalability
- Models cached in memory after first use
- Supports concurrent requests
- Recommended batch size: 100-1000 transactions

---

## Error Handling

### Common Errors

**Missing Required Fields**
```json
{
  "error": "Missing required columns",
  "missing_columns": ["amount", "fx_applied_rate"],
  "required_columns": [...]
}
```

**Invalid Decision Type**
```json
{
  "error": "Invalid decision",
  "valid_decisions": ["confirmed_fraud", "false_positive", "needs_investigation", "legitimate"]
}
```

---

## Database Schema

### transaction_feedback Table

```sql
CREATE TABLE transaction_feedback (
  id SERIAL PRIMARY KEY,
  execution_id UUID NOT NULL,
  transaction_id VARCHAR(255) NOT NULL,
  reviewer VARCHAR(255) NOT NULL,
  decision VARCHAR(50) NOT NULL,
  notes TEXT,
  reviewed_at TIMESTAMP NOT NULL,
  reviewed BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT NOW()
);
```

---

## Next Steps

1. **Integrate with your fraud system**
2. **Set up alerting for CRITICAL transactions**
3. **Build dashboard for summary_statistics**
4. **Implement feedback workflow**
5. **Monitor model performance over time**

For questions or issues, see the main documentation or contact support.
