# -----------------------------
# Suspicious Transaction Detection with Isolation Forest (Enhanced)
# -----------------------------
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.ensemble import IsolationForest
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score

# -----------------------------
# Step 1: Load dataset
# -----------------------------
df = pd.read_csv("Datasets/transactions_mock_1000_for_participants.csv", parse_dates=['booking_datetime','value_date'])

# Convert numeric columns and fill missing values
numeric_cols = ['amount', 'fx_applied_rate', 'fx_market_rate', 'daily_cash_total_customer', 'daily_cash_txn_count']
for col in numeric_cols:
    df[col] = pd.to_numeric(df.get(col, 0), errors='coerce').fillna(0)

# -----------------------------
# Step 2: Feature engineering
# -----------------------------
# FX anomaly: difference between applied and market rate
df['fx_anomaly'] = abs(df['fx_applied_rate'] - df['fx_market_rate'])

# Amount relative to customer's daily total
df['amount_ratio_daily'] = df['amount'] / (df['daily_cash_total_customer'] + 1e-6)  # avoid divide by zero

# -----------------------------
# Step 3: Define features
# -----------------------------
cat_features = [
    'currency', 'channel', 'product_type', 'customer_type', 
    'customer_risk_rating', 'originator_country', 'beneficiary_country'
]

num_features = [
    'amount', 'fx_applied_rate', 'daily_cash_total_customer', 
    'daily_cash_txn_count', 'fx_anomaly', 'amount_ratio_daily'
]

# Fill missing categorical values
for col in cat_features:
    df[col] = df[col].fillna('Unknown')

# -----------------------------
# Step 4: Build preprocessing + Isolation Forest pipeline
# -----------------------------
preprocessor = ColumnTransformer(
    transformers=[
        ('num', StandardScaler(), num_features),
        ('cat', OneHotEncoder(handle_unknown='ignore'), cat_features)
    ]
)

clf = Pipeline([
    ('preprocess', preprocessor),
    ('iso', IsolationForest(
        n_estimators=200,
        contamination=0.05,   # flag ~5% of transactions as anomalies
        random_state=42
    ))
])

# -----------------------------
# Step 5: Fit model
# -----------------------------
features = df[num_features + cat_features]
clf.fit(features)

# -----------------------------
# Step 6: Compute anomaly scores and flag anomalies
# -----------------------------
scores = clf['iso'].decision_function(preprocessor.transform(features))  # higher = more normal
threshold = np.percentile(scores, 5)  # bottom 5% are most anomalous
df['anomaly_score'] = scores
df['is_anomaly'] = (scores < threshold).astype(int)  # 1 = suspicious, 0 = normal

# -----------------------------
# Step 7: Output suspicious transactions
# -----------------------------
suspicious = df[df['is_anomaly'] == 1]
print("Suspicious transactions:")
print(suspicious[['transaction_id', 'amount', 'originator_country', 'beneficiary_country', 'anomaly_score']])
suspicious.to_csv("suspicious_transactions.csv", index=False)

# -----------------------------
# Step 8: Evaluation (if labels exist)
# -----------------------------
if 'suspicion_determined_datetime' in df.columns:
    df['is_suspicious'] = df['suspicion_determined_datetime'].notna().astype(int)
    y_true = df['is_suspicious']
    y_pred = df['is_anomaly']
    
    print("\nConfusion Matrix:")
    print(confusion_matrix(y_true, y_pred))
    
    print("\nClassification Report:")
    print(classification_report(y_true, y_pred))
    
    # ROC AUC using inverted anomaly scores (lower = more anomalous)
    print("ROC AUC Score:", roc_auc_score(y_true, -df['anomaly_score']))
