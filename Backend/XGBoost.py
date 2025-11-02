# -----------------------------
# Suspicious Transaction Detection with XGBoost
# -----------------------------
import pandas as pd
import numpy as np
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score, confusion_matrix
import xgboost as xgb
import os
import pickle

# Global variables for trained model and encoders
_trained_model = None
_label_encoders = {}

def train_model(csv_path='Datasets/transactions_mock_1000_for_participants.csv'):
    """
    Train XGBoost model on transaction data
    Returns: trained model, label encoders, feature columns, and evaluation metrics
    """
    global _trained_model, _label_encoders

    # 1. Load dataset
    df = pd.read_csv(csv_path)

    # 2. Create label
    df['is_suspicious'] = df['suspicion_determined_datetime'].notna().astype(int)
    df = df.drop(['suspicion_determined_datetime', 'str_filed_datetime'], axis=1)

    # 3. Feature engineering
    df['fx_anomaly'] = abs(df['fx_applied_rate'] - df['fx_market_rate'])
    df['amount_ratio_daily'] = df['amount'] / (df['daily_cash_total_customer'] + 1e-6)

    # 4. Select features
    categorical_cols = [
        'booking_jurisdiction', 'regulator', 'currency', 'channel', 'product_type',
        'originator_country', 'beneficiary_country', 'customer_type', 'customer_risk_rating',
        'customer_is_pep', 'travel_rule_complete', 'product_complex'
    ]

    numeric_cols = [
        'amount', 'fx_applied_rate', 'fx_market_rate', 'fx_spread_bps',
        'daily_cash_total_customer', 'daily_cash_txn_count', 'fx_anomaly', 'amount_ratio_daily'
    ]

    feature_cols = numeric_cols + categorical_cols
    X = df[feature_cols]
    y = df['is_suspicious']

    # 5. Encode categorical features
    label_encoders = {}
    for col in categorical_cols:
        le = LabelEncoder()
        X[col] = le.fit_transform(X[col].astype(str))
        label_encoders[col] = le

    # 6. Split dataset
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # 7. Train XGBoost classifier
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

    # 8. Evaluate
    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:,1]

    metrics = {
        'confusion_matrix': confusion_matrix(y_test, y_pred).tolist(),
        'classification_report': classification_report(y_test, y_pred, output_dict=True),
        'roc_auc_score': float(roc_auc_score(y_test, y_prob))
    }

    # Store globally
    _trained_model = model
    _label_encoders = label_encoders

    return model, label_encoders, feature_cols, metrics


def predict_transactions(transactions_df, model=None, label_encoders=None, include_feature_importance=False):
    """
    Predict suspicious transactions from a DataFrame

    Args:
        transactions_df: DataFrame with transaction data
        model: Trained XGBoost model (optional, will use global if None)
        label_encoders: Dictionary of label encoders (optional, will use global if None)
        include_feature_importance: Whether to include feature importance explanations

    Returns:
        DataFrame with predictions and probabilities
        If include_feature_importance=True, also returns feature importance dict
    """
    global _trained_model, _label_encoders

    # Use global model if not provided
    if model is None:
        if _trained_model is None:
            raise ValueError("No trained model available. Call train_model() first.")
        model = _trained_model

    if label_encoders is None:
        if not _label_encoders:
            raise ValueError("No label encoders available. Call train_model() first.")
        label_encoders = _label_encoders

    # Make a copy to avoid modifying original
    df = transactions_df.copy()

    # Feature engineering
    df['fx_anomaly'] = abs(df['fx_applied_rate'] - df['fx_market_rate'])
    df['amount_ratio_daily'] = df['amount'] / (df['daily_cash_total_customer'] + 1e-6)

    categorical_cols = [
        'booking_jurisdiction', 'regulator', 'currency', 'channel', 'product_type',
        'originator_country', 'beneficiary_country', 'customer_type', 'customer_risk_rating',
        'customer_is_pep', 'travel_rule_complete', 'product_complex'
    ]

    numeric_cols = [
        'amount', 'fx_applied_rate', 'fx_market_rate', 'fx_spread_bps',
        'daily_cash_total_customer', 'daily_cash_txn_count', 'fx_anomaly', 'amount_ratio_daily'
    ]

    feature_cols = numeric_cols + categorical_cols
    X = df[feature_cols]

    # Encode categorical features
    for col in categorical_cols:
        if col in label_encoders:
            le = label_encoders[col]
            # Handle unseen categories
            X[col] = X[col].astype(str).apply(
                lambda x: le.transform([x])[0] if x in le.classes_ else -1
            )

    # Predict
    predictions = model.predict(X)
    probabilities = model.predict_proba(X)[:, 1]

    # Add results to DataFrame
    result_df = transactions_df.copy()
    result_df['is_suspicious_prediction'] = predictions
    result_df['suspicion_probability'] = probabilities
    result_df['risk_level'] = pd.cut(
        probabilities,
        bins=[0, 0.3, 0.7, 1.0],
        labels=['Low', 'Medium', 'High']
    )

    # Get feature importance if requested
    feature_importance = None
    if include_feature_importance:
        feature_importance = get_feature_importance(model, feature_cols)

    if include_feature_importance:
        return result_df, feature_importance
    else:
        return result_df


def get_feature_importance(model=None, feature_names=None, top_n=10):
    """
    Get feature importance from trained model

    Args:
        model: Trained XGBoost model (optional)
        feature_names: List of feature names (optional)
        top_n: Number of top features to return

    Returns:
        Dictionary with feature importance scores
    """
    global _trained_model

    if model is None:
        if _trained_model is None:
            raise ValueError("No trained model available. Call train_model() first.")
        model = _trained_model

    # Get feature importance scores
    importance_scores = model.feature_importances_

    if feature_names is None:
        categorical_cols = [
            'booking_jurisdiction', 'regulator', 'currency', 'channel', 'product_type',
            'originator_country', 'beneficiary_country', 'customer_type', 'customer_risk_rating',
            'customer_is_pep', 'travel_rule_complete', 'product_complex'
        ]

        numeric_cols = [
            'amount', 'fx_applied_rate', 'fx_market_rate', 'fx_spread_bps',
            'daily_cash_total_customer', 'daily_cash_txn_count', 'fx_anomaly', 'amount_ratio_daily'
        ]
        feature_names = numeric_cols + categorical_cols

    # Create feature importance dictionary
    feature_importance = dict(zip(feature_names, importance_scores))

    # Sort by importance and get top N
    sorted_features = sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)[:top_n]

    return {
        'top_features': [{'feature': name, 'importance': float(score)} for name, score in sorted_features],
        'all_features': {name: float(score) for name, score in feature_importance.items()}
    }


def explain_prediction(transaction_data, model=None, label_encoders=None, top_n=5):
    """
    Explain why a specific transaction was flagged as suspicious

    Args:
        transaction_data: Dictionary or Series with transaction data
        model: Trained model (optional)
        label_encoders: Label encoders (optional)
        top_n: Number of top contributing features to return

    Returns:
        Dictionary with explanation
    """
    global _trained_model, _label_encoders

    if model is None:
        model = _trained_model
    if label_encoders is None:
        label_encoders = _label_encoders

    # Convert to DataFrame if dict
    if isinstance(transaction_data, dict):
        df = pd.DataFrame([transaction_data])
    else:
        df = pd.DataFrame([transaction_data.to_dict()])

    # Get prediction
    result_df = predict_transactions(df, model, label_encoders)
    probability = result_df['suspicion_probability'].iloc[0]

    # Get feature values
    df['fx_anomaly'] = abs(df['fx_applied_rate'] - df['fx_market_rate'])
    df['amount_ratio_daily'] = df['amount'] / (df['daily_cash_total_customer'] + 1e-6)

    # Get global feature importance
    importance = get_feature_importance(model, top_n=top_n)

    # Identify specific risk factors for this transaction
    risk_factors = []

    # Check high-value features
    if df['amount'].iloc[0] > 100000:
        risk_factors.append({'factor': 'High transaction amount', 'value': float(df['amount'].iloc[0])})

    if df['fx_anomaly'].iloc[0] > 0.05:
        risk_factors.append({'factor': 'Unusual FX rate spread', 'value': float(df['fx_anomaly'].iloc[0])})

    if df['amount_ratio_daily'].iloc[0] > 0.5:
        risk_factors.append({'factor': 'Large portion of daily activity', 'value': float(df['amount_ratio_daily'].iloc[0])})

    if 'customer_is_pep' in df.columns and df['customer_is_pep'].iloc[0] == 'Yes':
        risk_factors.append({'factor': 'Customer is PEP', 'value': 'Yes'})

    if 'travel_rule_complete' in df.columns and df['travel_rule_complete'].iloc[0] == 'No':
        risk_factors.append({'factor': 'Travel rule incomplete', 'value': 'No'})

    if 'customer_risk_rating' in df.columns and df['customer_risk_rating'].iloc[0] in ['high', 'High']:
        risk_factors.append({'factor': 'High-risk customer', 'value': df['customer_risk_rating'].iloc[0]})

    return {
        'suspicion_probability': float(probability),
        'risk_level': result_df['risk_level'].iloc[0],
        'top_model_features': importance['top_features'][:top_n],
        'transaction_risk_factors': risk_factors
    }


def get_suspicious_transactions(transactions_df, threshold=0.5):
    """
    Get only suspicious transactions above a threshold

    Args:
        transactions_df: DataFrame with transaction data
        threshold: Probability threshold (default 0.5)

    Returns:
        DataFrame with only suspicious transactions
    """
    result_df = predict_transactions(transactions_df)
    suspicious = result_df[result_df['suspicion_probability'] >= threshold]
    return suspicious.sort_values('suspicion_probability', ascending=False)


# For backward compatibility - run training if executed directly
if __name__ == '__main__':
    import matplotlib.pyplot as plt

    model, encoders, features, metrics = train_model()

    print("Confusion Matrix:")
    print(metrics['confusion_matrix'])
    print("\nClassification Report:")
    print(metrics['classification_report'])
    print("ROC AUC Score:", metrics['roc_auc_score'])

    # Feature importance
    xgb.plot_importance(model, max_num_features=20)
    plt.title("Top 20 Feature Importances")
    plt.show()
