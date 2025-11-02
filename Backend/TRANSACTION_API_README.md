# Transaction Analysis API

## Overview

The Transaction Analysis API provides endpoints for detecting suspicious financial transactions using machine learning models (XGBoost and Isolation Forest).

## Endpoints

### 1. Analyze Transactions
**POST** `/api/analyze-transactions`

Analyze transactions for suspicious activity using XGBoost and/or Isolation Forest models.

#### Query Parameters
- `method` (optional): Analysis method - `'xgboost'`, `'isolation_forest'`, or `'both'` (default: `'both'`)
- `threshold` (optional): Suspicion threshold for XGBoost (0-1, default: `0.5`)
- `contamination` (optional): Expected anomaly rate for Isolation Forest (0-1, default: `0.05`)

#### Request Body Options

**Option 1: CSV File Upload**
```bash
curl -X POST \
  "http://localhost:5001/api/analyze-transactions?method=both" \
  -F "file=@transactions.csv"
```

**Option 2: JSON Data**
```bash
curl -X POST \
  "http://localhost:5001/api/analyze-transactions?method=both" \
  -H "Content-Type: application/json" \
  -d '{
    "transactions": [
      {
        "transaction_id": "TXN001",
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
      }
    ]
  }'
```

#### Required Fields
- `amount` - Transaction amount
- `fx_applied_rate` - FX rate applied
- `fx_market_rate` - Market FX rate
- `daily_cash_total_customer` - Customer's daily transaction total
- `daily_cash_txn_count` - Customer's daily transaction count
- `currency` - Transaction currency
- `channel` - Transaction channel (e.g., online, branch)
- `product_type` - Product type (e.g., wire, deposit)
- `customer_type` - Customer type
- `customer_risk_rating` - Customer risk rating
- `originator_country` - Originator country code
- `beneficiary_country` - Beneficiary country code
- `booking_jurisdiction` - Booking jurisdiction
- `regulator` - Regulatory authority
- `customer_is_pep` - Is customer a PEP (Yes/No)
- `travel_rule_complete` - Travel rule completion status
- `product_complex` - Is product complex (Yes/No)

#### Response Example
```json
{
  "total_transactions": 1000,
  "analysis_timestamp": "2025-11-02T10:30:00",
  "method": "both",
  "xgboost": {
    "suspicious_count": 45,
    "suspicious_percentage": 4.5,
    "threshold": 0.5,
    "suspicious_transactions": [
      {
        "transaction_id": "TXN001",
        "amount": 50000,
        "suspicion_probability": 0.87,
        "risk_level": "High"
      }
    ],
    "risk_distribution": {
      "high": 15,
      "medium": 30,
      "low": 955
    }
  },
  "isolation_forest": {
    "anomaly_count": 50,
    "anomaly_percentage": 5.0,
    "contamination": 0.05,
    "anomalous_transactions": [
      {
        "transaction_id": "TXN001",
        "amount": 50000,
        "anomaly_score": -0.234,
        "anomaly_severity": "High"
      }
    ],
    "severity_distribution": {
      "high": 20,
      "medium": 20,
      "low": 10
    }
  },
  "consensus": {
    "flagged_by_both": 12,
    "flagged_by_xgboost_only": 33,
    "flagged_by_isolation_forest_only": 38,
    "high_confidence_transactions": ["TXN001", "TXN042", ...]
  }
}
```

---

### 2. Train Models
**POST** `/api/train-models`

Manually trigger training of ML models.

#### Query Parameters
- `model` (optional): Model to train - `'xgboost'`, `'isolation_forest'`, or `'both'` (default: `'both'`)

#### Example
```bash
curl -X POST "http://localhost:5001/api/train-models?model=both"
```

#### Response Example
```json
{
  "trained_at": "2025-11-02T10:30:00",
  "model_type": "both",
  "xgboost": {
    "status": "success",
    "metrics": {
      "confusion_matrix": [[800, 50], [20, 130]],
      "classification_report": {...},
      "roc_auc_score": 0.92
    }
  },
  "isolation_forest": {
    "status": "success",
    "metrics": {
      "confusion_matrix": [[820, 30], [40, 110]],
      "classification_report": {...},
      "roc_auc_score": 0.88
    }
  }
}
```

---

## Usage Examples

### Python Example
```python
import requests
import pandas as pd

# Load transactions
df = pd.read_csv('transactions.csv')

# Analyze with both models
response = requests.post(
    'http://localhost:5001/api/analyze-transactions?method=both',
    files={'file': open('transactions.csv', 'rb')}
)

result = response.json()
print(f"Found {result['consensus']['flagged_by_both']} high-confidence suspicious transactions")
```

### JavaScript Example
```javascript
// Upload CSV file
const formData = new FormData();
formData.append('file', fileInput.files[0]);

fetch('http://localhost:5001/api/analyze-transactions?method=both', {
  method: 'POST',
  body: formData
})
.then(res => res.json())
.then(data => {
  console.log(`Suspicious: ${data.xgboost.suspicious_count}`);
  console.log(`Anomalies: ${data.isolation_forest.anomaly_count}`);
});
```

---

## Model Information

### XGBoost (Supervised Learning)
- **Type**: Gradient Boosting Classifier
- **Purpose**: Predicts if a transaction is suspicious based on labeled training data
- **Output**: Suspicion probability (0-1) and risk level (Low/Medium/High)
- **Best for**: Transactions similar to known suspicious patterns

### Isolation Forest (Unsupervised Learning)
- **Type**: Anomaly Detection
- **Purpose**: Identifies transactions that deviate from normal patterns
- **Output**: Anomaly score and severity (Low/Medium/High)
- **Best for**: Detecting novel suspicious patterns not seen in training data

### Consensus
When using `method=both`, transactions flagged by **both models** have the highest confidence of being suspicious.

---

## Testing

Run the test script:
```bash
cd Backend
python test_transaction_endpoint.py
```

This will:
1. Check API health
2. Train both models
3. Analyze transactions from CSV
4. Analyze sample JSON transactions

---

## Error Handling

### Common Errors

**400 Bad Request - Missing Columns**
```json
{
  "error": "Missing required columns",
  "missing_columns": ["amount", "fx_applied_rate"],
  "required_columns": [...]
}
```

**400 Bad Request - No Data**
```json
{
  "error": "No transactions provided in request body"
}
```

**500 Internal Server Error**
```json
{
  "error": "Transaction analysis failed: ...",
  "error_type": "ValueError"
}
```

---

## Performance Notes

- First request trains the models (may take 10-30 seconds)
- Subsequent requests use cached models (fast)
- Models are stored in memory and persist until server restart
- For production, consider pre-training models on startup

---

## Next Steps

1. **Start the server**: `python app.py`
2. **Train models**: `curl -X POST http://localhost:5001/api/train-models`
3. **Analyze transactions**: Upload CSV or send JSON
4. **Integrate with frontend**: Use the response data to display results
