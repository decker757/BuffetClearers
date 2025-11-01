import pandas as pd
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.ensemble import IsolationForest

# -----------------------------
# Step 1: Load your dataset
# -----------------------------
df = pd.read_csv("Datasets/transactions_mock_1000_for_participants.csv", parse_dates=['booking_datetime','value_date'])
df['amount'] = pd.to_numeric(df['amount'], errors='coerce').fillna(0)

# -----------------------------
# Step 2: Select features for anomaly detection
# -----------------------------
# Categorical features
cat_features = [
    'currency', 'channel', 'product_type', 'customer_type', 
    'customer_risk_rating', 'originator_country', 'beneficiary_country'
]

# Numeric features
num_features = [
    'amount', 'fx_applied_rate', 'daily_cash_total_customer', 
    'daily_cash_txn_count'
]

# Fill missing categorical values
for col in cat_features:
    df[col] = df[col].fillna('Unknown')

# -----------------------------
# Step 3: Preprocess features
# -----------------------------
preprocessor = ColumnTransformer(
    transformers=[
        ('num', StandardScaler(), num_features),
        ('cat', OneHotEncoder(handle_unknown='ignore'), cat_features)
    ]
)

# -----------------------------
# Step 4: Build Isolation Forest pipeline
# -----------------------------
clf = Pipeline([
    ('preprocess', preprocessor),
    ('iso', IsolationForest(
        n_estimators=200,       # number of trees
        contamination=0.01,     # ~1% of transactions considered anomalies
        random_state=42
    ))
])

# -----------------------------
# Step 5: Fit model and predict anomalies
# -----------------------------
features = df[num_features + cat_features]
clf.fit(features)

df['anomaly_score'] = clf['iso'].decision_function(preprocessor.fit_transform(features))
df['is_anomaly'] = clf['iso'].predict(preprocessor.transform(features))  # -1 = anomaly, 1 = normal

# -----------------------------
# Step 6: Output suspicious transactions
# -----------------------------
suspicious = df[df['is_anomaly'] == -1]

print("Suspicious transactions:")
print(suspicious[['transaction_id', 'amount', 'originator_country', 'beneficiary_country', 'anomaly_score']])

# Optionally save to CSV
suspicious.to_csv("suspicious_transactions.csv", index=False)