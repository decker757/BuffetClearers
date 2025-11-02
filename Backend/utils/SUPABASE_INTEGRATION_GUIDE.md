# Linking Supabase Rules to fraud_scoring.py

## Overview

The `fraud_scoring.py` module now supports dynamic rule loading from Supabase. This allows you to:

- Store AML rules in your Supabase database
- Automatically load and sync rules at runtime
- Update rules without changing code
- Maintain both default (hardcoded) and database-driven rules

## Setup Steps

### 1. Ensure Supabase Schema is Created

Make sure you've run the SQL schema from:
```
Backend/Regulations/create_supabase_schema.sql
```

This creates the following tables:
- `regulators` - Regulatory authorities (FINMA, MAS, HKMA)
- `regulatory_documents` - Document metadata
- `aml_rules` - The actual AML rules
- `rule_keywords` - Keywords for searchability

### 2. Configure Environment Variables

Add to your `.env` file:
```bash
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
```

### 3. Populate AML Rules in Supabase

Insert rules into the `aml_rules` table:

```sql
INSERT INTO aml_rules (
    rule_id,
    document_id,
    rule_type,
    title,
    description,
    threshold_amount,
    threshold_currency
) VALUES (
    'FINMA_TR_10K_CHF',
    'FINMA_CIRC_2024_01',
    'threshold_reporting',
    'CHF 10,000 Cash Transaction Reporting',
    'Report cash transactions exceeding CHF 10,000 to MROS',
    10000.00,
    'CHF'
);
```

## Usage Examples

### Example 1: With Supabase Integration

```python
from supabase import create_client
from fraud_scoring import FraudScorer
import os

# Initialize Supabase client
supabase = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_KEY')
)

# Initialize FraudScorer with Supabase
scorer = FraudScorer(supabase_client=supabase)

# Rules are automatically loaded from Supabase!
# scorer.ALERT_RULES now contains both default + Supabase rules

# Check a transaction
transaction = {
    'amount': 15000,
    'currency': 'CHF',
    'customer_is_pep': True,
    # ... other fields
}

alerts = scorer.check_alert_rules(transaction)
fraud_score = scorer.calculate_unified_fraud_score(
    xgb_prob=0.75,
    alerts=alerts
)
```

### Example 2: Without Supabase (Fallback)

```python
from fraud_scoring import FraudScorer

# Initialize without Supabase - uses default rules only
scorer = FraudScorer()

# Still works with hardcoded default rules
alerts = scorer.check_alert_rules(transaction)
```

### Example 3: Get Applicable Supabase Rules

```python
# Get rules that apply to a specific transaction
applicable_rules = scorer.get_applicable_rules(transaction)

for rule in applicable_rules:
    print(f"Rule: {rule['title']}")
    print(f"Threshold: {rule['threshold']} {rule['currency']}")
```

### Example 4: Reload Rules After Update

```python
# If rules are updated in Supabase, reload them
scorer.load_rules_from_supabase()

# scorer.ALERT_RULES is now updated with latest from Supabase
```

## How It Works

### 1. Initialization
When you create a `FraudScorer` with a Supabase client:
```python
scorer = FraudScorer(supabase_client=supabase)
```

It automatically:
1. Queries the `aml_rules` table for `threshold_reporting` rules
2. Loads them into `scorer.supabase_rules`
3. Syncs them into `scorer.ALERT_RULES` for use

### 2. Rule Synchronization
The `_sync_threshold_rules()` method converts Supabase rules to the internal format:

**Supabase Format:**
```json
{
  "rule_id": "FINMA_TR_10K_CHF",
  "title": "CHF 10,000 Cash Transaction Reporting",
  "threshold_amount": 10000.00,
  "threshold_currency": "CHF"
}
```

**Internal Format:**
```python
{
  'FINMA_TR_10K_CHF': {
    'threshold': 10000.0,
    'weight': 20,
    'description': 'CHF 10,000 Cash Transaction Reporting',
    'currency': 'CHF',
    'source': 'supabase'
  }
}
```

### 3. Alert Checking
When you call `check_alert_rules(transaction)`, it:
1. Checks all rules in `ALERT_RULES` (both default and Supabase)
2. Returns triggered alerts with severity and weights
3. Can be used to calculate the final fraud score

## Key Methods

### `__init__(supabase_client: Optional[Client] = None)`
Initialize the scorer with optional Supabase integration.

### `load_rules_from_supabase() -> bool`
Load rules from Supabase database. Returns `True` if successful.

### `get_applicable_rules(transaction: Dict) -> List[Dict]`
Get Supabase rules that apply to a specific transaction based on thresholds and currency.

### `check_alert_rules(transaction: Dict) -> List[Dict]`
Check transaction against all alert rules (default + Supabase).

### `calculate_unified_fraud_score(xgb_prob, iso_score, alerts) -> float`
Calculate final fraud score (0-100) from model predictions and alerts.

## Rule Types Supported

Currently, the integration focuses on **threshold-based rules** from Supabase:
- Cash transaction reporting thresholds
- High-value transaction alerts
- Currency-specific thresholds

The following rule types remain hardcoded (can be extended):
- PEP customer checks
- High-risk country checks
- FX spread anomalies
- Travel rule compliance

## Extending the Integration

### Add More Rule Types

Modify `load_rules_from_supabase()` to fetch other rule types:

```python
# Fetch customer due diligence rules
response = self.supabase.table('aml_rules').select('*').eq(
    'rule_type', 'customer_due_diligence'
).execute()
```

### Custom Rule Weights

Rules from Supabase currently default to weight=20. To customize:

```sql
-- Add a weight column to aml_rules table
ALTER TABLE aml_rules ADD COLUMN alert_weight INTEGER DEFAULT 20;

-- Update the rule with custom weight
UPDATE aml_rules SET alert_weight = 30
WHERE rule_id = 'FINMA_TR_10K_CHF';
```

Then modify `_sync_threshold_rules()` to use it:
```python
'weight': rule.get('alert_weight', 20)
```

## Testing

Run the example script to test the integration:

```bash
cd Backend/utils
python fraud_scoring_example.py
```

This will:
1. Load rules from Supabase
2. Check a sample transaction
3. Show triggered alerts
4. Calculate fraud score

## Troubleshooting

### "No Supabase client configured"
- Make sure you pass a Supabase client when initializing
- Check that SUPABASE_URL and SUPABASE_KEY are in .env

### "Failed to load rules from Supabase"
- Verify the `aml_rules` table exists
- Check Supabase connection credentials
- Ensure RLS policies allow read access

### Rules not appearing
- Confirm rules have `rule_type = 'threshold_reporting'`
- Check that `threshold_amount` is not NULL
- Verify rules are not soft-deleted

## Next Steps

1. **Populate your Supabase database** with actual regulatory rules from FINMA, MAS, HKMA
2. **Extend rule types** beyond threshold reporting
3. **Add currency conversion** for cross-currency threshold checks
4. **Implement rule versioning** to track regulatory changes over time
5. **Add caching** to reduce database queries for frequently used rules

## Questions?

Check these files for more details:
- [fraud_scoring.py](fraud_scoring.py) - Main implementation
- [fraud_scoring_example.py](fraud_scoring_example.py) - Working examples
- [../Regulations/create_supabase_schema.sql](../Regulations/create_supabase_schema.sql) - Database schema
