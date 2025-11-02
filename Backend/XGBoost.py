# -----------------------------
# Suspicious Transaction Detection with XGBoost
# -----------------------------
import pandas as pd
import numpy as np
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score, confusion_matrix
import xgboost as xgb

# -----------------------------
# 1. Load dataset
# -----------------------------
df = pd.read_csv('Datasets/transactions_mock_1000_for_participants.csv')

# -----------------------------
# 2. Create label
# -----------------------------
# Transaction is suspicious if 'suspicion_determined_datetime' is not null
df['is_suspicious'] = df['suspicion_determined_datetime'].notna().astype(int)

# Optional: drop datetime columns
df = df.drop(['suspicion_determined_datetime', 'str_filed_datetime'], axis=1)

# -----------------------------
# 3. Feature engineering
# -----------------------------
# FX anomaly: difference between applied rate and market rate
df['fx_anomaly'] = abs(df['fx_applied_rate'] - df['fx_market_rate'])

# Amount relative to customer's daily total
df['amount_ratio_daily'] = df['amount'] / (df['daily_cash_total_customer'] + 1e-6)  # avoid divide by zero

# -----------------------------
# 4. Select features
# -----------------------------
categorical_cols = [
    'booking_jurisdiction', 'regulator', 'currency', 'channel', 'product_type',
    'originator_country', 'beneficiary_country', 'customer_type', 'customer_risk_rating',
    'customer_is_pep', 'travel_rule_complete', 'product_complex'
]

numeric_cols = [
    'amount', 'fx_applied_rate', 'fx_market_rate', 'fx_spread_bps',
    'daily_cash_total_customer', 'daily_cash_txn_count', 'fx_anomaly', 'amount_ratio_daily'
]

# Drop IDs/text columns
drop_cols = [
    'transaction_id', 'originator_name', 'originator_account', 
    'beneficiary_name', 'beneficiary_account', 'narrative'
]

feature_cols = numeric_cols + categorical_cols
X = df[feature_cols]
y = df['is_suspicious']

# -----------------------------
# 5. Encode categorical features
# -----------------------------
for col in categorical_cols:
    le = LabelEncoder()
    X[col] = le.fit_transform(X[col].astype(str))

# -----------------------------
# 6. Split dataset
# -----------------------------
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# -----------------------------
# 7. Train XGBoost classifier
# -----------------------------
# Handle class imbalance
scale_pos_weight = (y_train == 0).sum() / (y_train == 1).sum()

model = xgb.XGBClassifier(
    objective='binary:logistic',
    eval_metric='auc',
    use_label_encoder=False,
    n_estimators=200,
    max_depth=5,
    learning_rate=0.1,
    scale_pos_weight=scale_pos_weight,
    random_state=42
)

model.fit(X_train, y_train)

# -----------------------------
# 8. Predict and evaluate
# -----------------------------
y_pred = model.predict(X_test)
y_prob = model.predict_proba(X_test)[:,1]

print("Confusion Matrix:")
print(confusion_matrix(y_test, y_pred))
print("\nClassification Report:")
print(classification_report(y_test, y_pred))
print("ROC AUC Score:", roc_auc_score(y_test, y_prob))

# -----------------------------
# 9. Feature importance
# -----------------------------
import matplotlib.pyplot as plt
xgb.plot_importance(model, max_num_features=20)
plt.title("Top 20 Feature Importances")
plt.show()
