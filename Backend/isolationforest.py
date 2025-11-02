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

# Global variable for trained pipeline
_trained_pipeline = None
_preprocessor = None

def train_isolation_forest(csv_path="Datasets/transactions_mock_1000_for_participants.csv", contamination=0.05):
    """
    Train Isolation Forest model on transaction data

    Args:
        csv_path: Path to CSV file with transactions
        contamination: Expected proportion of anomalies (default 0.05 = 5%)

    Returns:
        Trained pipeline, preprocessor, and evaluation metrics
    """
    global _trained_pipeline, _preprocessor

    # Step 1: Load dataset
    df = pd.read_csv(csv_path, parse_dates=['booking_datetime','value_date'])

    # Convert numeric columns and fill missing values
    numeric_cols = ['amount', 'fx_applied_rate', 'fx_market_rate', 'daily_cash_total_customer', 'daily_cash_txn_count']
    for col in numeric_cols:
        df[col] = pd.to_numeric(df.get(col, 0), errors='coerce').fillna(0)

    # Step 2: Feature engineering
    df['fx_anomaly'] = abs(df['fx_applied_rate'] - df['fx_market_rate'])
    df['amount_ratio_daily'] = df['amount'] / (df['daily_cash_total_customer'] + 1e-6)

    # Step 3: Define features
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

    # Step 4: Build preprocessing + Isolation Forest pipeline
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
            contamination=contamination,
            random_state=42
        ))
    ])

    # Step 5: Fit model
    features = df[num_features + cat_features]
    clf.fit(features)

    # Step 6: Evaluate (if labels exist)
    metrics = None
    if 'suspicion_determined_datetime' in df.columns:
        scores = clf['iso'].decision_function(preprocessor.transform(features))
        threshold = np.percentile(scores, contamination * 100)
        predictions = (scores < threshold).astype(int)

        y_true = df['suspicion_determined_datetime'].notna().astype(int)

        metrics = {
            'confusion_matrix': confusion_matrix(y_true, predictions).tolist(),
            'classification_report': classification_report(y_true, predictions, output_dict=True),
            'roc_auc_score': float(roc_auc_score(y_true, -scores))
        }

    # Store globally
    _trained_pipeline = clf
    _preprocessor = preprocessor

    return clf, preprocessor, metrics


def detect_anomalies(transactions_df, pipeline=None, contamination=0.05):
    """
    Detect anomalies in transaction data using Isolation Forest

    Args:
        transactions_df: DataFrame with transaction data
        pipeline: Trained pipeline (optional, will use global if None)
        contamination: Contamination threshold for anomaly detection

    Returns:
        DataFrame with anomaly scores and flags
    """
    global _trained_pipeline, _preprocessor

    # Use global pipeline if not provided
    if pipeline is None:
        if _trained_pipeline is None:
            raise ValueError("No trained pipeline available. Call train_isolation_forest() first.")
        pipeline = _trained_pipeline

    # Make a copy to avoid modifying original
    df = transactions_df.copy()

    # Convert numeric columns and fill missing values
    numeric_cols = ['amount', 'fx_applied_rate', 'fx_market_rate', 'daily_cash_total_customer', 'daily_cash_txn_count']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df.get(col, 0), errors='coerce').fillna(0)

    # Feature engineering
    df['fx_anomaly'] = abs(df['fx_applied_rate'] - df['fx_market_rate'])
    df['amount_ratio_daily'] = df['amount'] / (df['daily_cash_total_customer'] + 1e-6)

    # Define features
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
        if col in df.columns:
            df[col] = df[col].fillna('Unknown')

    # Get features
    features = df[num_features + cat_features]

    # Get preprocessor from pipeline
    preprocessor = pipeline.named_steps['preprocess']

    # Compute anomaly scores
    scores = pipeline['iso'].decision_function(preprocessor.transform(features))
    threshold = np.percentile(scores, contamination * 100)

    # Add results to DataFrame
    result_df = transactions_df.copy()
    result_df['anomaly_score'] = scores
    result_df['is_anomaly'] = (scores < threshold).astype(int)
    result_df['anomaly_severity'] = pd.cut(
        -scores,  # Invert so higher is worse
        bins=3,
        labels=['Low', 'Medium', 'High']
    )

    return result_df


def get_anomalies(transactions_df, pipeline=None, contamination=0.05):
    """
    Get only anomalous transactions

    Args:
        transactions_df: DataFrame with transaction data
        pipeline: Trained pipeline (optional)
        contamination: Contamination threshold

    Returns:
        DataFrame with only anomalous transactions
    """
    result_df = detect_anomalies(transactions_df, pipeline, contamination)
    anomalies = result_df[result_df['is_anomaly'] == 1]
    return anomalies.sort_values('anomaly_score', ascending=True)  # Most anomalous first


# For backward compatibility - run training if executed directly
if __name__ == '__main__':
    clf, preprocessor, metrics = train_isolation_forest()

    # Load data for testing
    df = pd.read_csv("Datasets/transactions_mock_1000_for_participants.csv")

    # Detect anomalies
    results = detect_anomalies(df, clf)
    suspicious = results[results['is_anomaly'] == 1]

    print("Suspicious transactions:")
    print(suspicious[['transaction_id', 'amount', 'originator_country', 'beneficiary_country', 'anomaly_score']])
    suspicious.to_csv("suspicious_transactions.csv", index=False)

    if metrics:
        print("\nConfusion Matrix:")
        print(metrics['confusion_matrix'])
        print("\nClassification Report:")
        print(metrics['classification_report'])
        print("ROC AUC Score:", metrics['roc_auc_score'])
