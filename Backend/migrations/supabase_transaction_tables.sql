-- ============================================================
-- TRANSACTION ANALYSIS TABLES FOR SUPABASE
-- Add these 4 new tables to your existing Supabase database
-- ============================================================

-- 1. TRANSACTION ANALYSIS AUDIT TRAIL
-- Tracks every analysis execution
CREATE TABLE IF NOT EXISTS transaction_analysis_audit (
    id BIGSERIAL PRIMARY KEY,
    execution_id UUID NOT NULL UNIQUE,
    event_type VARCHAR(50) NOT NULL DEFAULT 'transaction_analysis',
    data_source VARCHAR(255),
    total_transactions INTEGER NOT NULL,
    analysis_method VARCHAR(50) NOT NULL,
    model_versions JSONB,
    analysis_config JSONB,
    summary_stats JSONB,
    alert_summary JSONB,
    high_risk_count INTEGER DEFAULT 0,
    average_fraud_score DECIMAL(5,2),
    performed_by VARCHAR(255) DEFAULT 'system',
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for transaction_analysis_audit
CREATE INDEX IF NOT EXISTS idx_taa_execution_id ON transaction_analysis_audit(execution_id);
CREATE INDEX IF NOT EXISTS idx_taa_timestamp ON transaction_analysis_audit(timestamp);
CREATE INDEX IF NOT EXISTS idx_taa_high_risk_count ON transaction_analysis_audit(high_risk_count);

-- Enable RLS (adjust policies based on your needs)
ALTER TABLE transaction_analysis_audit ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Enable read for all users" ON transaction_analysis_audit
    FOR SELECT USING (true);

CREATE POLICY "Enable insert for all users" ON transaction_analysis_audit
    FOR INSERT WITH CHECK (true);


-- 2. FLAGGED TRANSACTIONS
-- Stores high-risk transactions (fraud_score >= 60)
CREATE TABLE IF NOT EXISTS flagged_transactions (
    id BIGSERIAL PRIMARY KEY,
    execution_id UUID NOT NULL,
    transaction_id VARCHAR(255) NOT NULL,
    amount DECIMAL(18,2) NOT NULL,
    fraud_risk_score DECIMAL(5,2) NOT NULL,
    risk_category VARCHAR(20) NOT NULL,
    xgboost_probability DECIMAL(6,4),
    isolation_forest_score DECIMAL(8,4),
    alert_count INTEGER DEFAULT 0,
    alerts JSONB,
    context JSONB,
    explanation JSONB,
    status VARCHAR(50) DEFAULT 'pending_review',
    assigned_to VARCHAR(255),
    reviewed_at TIMESTAMP WITH TIME ZONE,
    review_decision VARCHAR(50),
    review_notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT fk_ft_execution FOREIGN KEY (execution_id)
        REFERENCES transaction_analysis_audit(execution_id) ON DELETE CASCADE
);

-- Indexes for flagged_transactions
CREATE INDEX IF NOT EXISTS idx_ft_execution_id ON flagged_transactions(execution_id);
CREATE INDEX IF NOT EXISTS idx_ft_transaction_id ON flagged_transactions(transaction_id);
CREATE INDEX IF NOT EXISTS idx_ft_fraud_score ON flagged_transactions(fraud_risk_score DESC);
CREATE INDEX IF NOT EXISTS idx_ft_status ON flagged_transactions(status);

ALTER TABLE flagged_transactions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Enable all for all users" ON flagged_transactions
    FOR ALL USING (true);


-- 3. FRAUD ALERTS
-- Critical alerts for fraud_score >= 80
CREATE TABLE IF NOT EXISTS fraud_alerts (
    id BIGSERIAL PRIMARY KEY,
    execution_id UUID NOT NULL,
    transaction_id VARCHAR(255) NOT NULL,
    alert_type VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    fraud_score DECIMAL(5,2) NOT NULL,
    risk_category VARCHAR(20) NOT NULL,
    description TEXT,
    triggered_rules JSONB,
    status VARCHAR(50) DEFAULT 'open',
    assigned_to VARCHAR(255),
    resolved_at TIMESTAMP WITH TIME ZONE,
    resolution_notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB,

    CONSTRAINT fk_fa_execution FOREIGN KEY (execution_id)
        REFERENCES transaction_analysis_audit(execution_id) ON DELETE CASCADE
);

-- Indexes for fraud_alerts
CREATE INDEX IF NOT EXISTS idx_fa_execution_id ON fraud_alerts(execution_id);
CREATE INDEX IF NOT EXISTS idx_fa_severity ON fraud_alerts(severity);
CREATE INDEX IF NOT EXISTS idx_fa_status ON fraud_alerts(status);

ALTER TABLE fraud_alerts ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Enable all for all users" ON fraud_alerts
    FOR ALL USING (true);


-- 4. TRANSACTION FEEDBACK
-- Manual review feedback
CREATE TABLE IF NOT EXISTS transaction_feedback (
    id BIGSERIAL PRIMARY KEY,
    execution_id UUID NOT NULL,
    transaction_id VARCHAR(255) NOT NULL,
    reviewer VARCHAR(255) NOT NULL,
    decision VARCHAR(50) NOT NULL CHECK (
        decision IN ('confirmed_fraud', 'false_positive', 'needs_investigation', 'legitimate')
    ),
    notes TEXT,
    reviewed_at TIMESTAMP WITH TIME ZONE NOT NULL,
    reviewed BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT fk_tf_execution FOREIGN KEY (execution_id)
        REFERENCES transaction_analysis_audit(execution_id) ON DELETE CASCADE
);

-- Indexes for transaction_feedback
CREATE INDEX IF NOT EXISTS idx_tf_execution_id ON transaction_feedback(execution_id);
CREATE INDEX IF NOT EXISTS idx_tf_transaction_id ON transaction_feedback(transaction_id);
CREATE INDEX IF NOT EXISTS idx_tf_decision ON transaction_feedback(decision);

ALTER TABLE transaction_feedback ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Enable all for all users" ON transaction_feedback
    FOR ALL USING (true);


-- ============================================================
-- AUTO-UPDATE TIMESTAMP TRIGGER
-- ============================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_flagged_transactions_updated_at
    BEFORE UPDATE ON flagged_transactions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_fraud_alerts_updated_at
    BEFORE UPDATE ON fraud_alerts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();


-- ============================================================
-- USEFUL VIEWS
-- ============================================================

-- View: Recent high-risk transactions
CREATE OR REPLACE VIEW v_recent_high_risk AS
SELECT
    ft.*,
    taa.data_source,
    taa.performed_by,
    taa.timestamp as analysis_time
FROM flagged_transactions ft
JOIN transaction_analysis_audit taa ON ft.execution_id = taa.execution_id
WHERE ft.created_at >= NOW() - INTERVAL '30 days'
ORDER BY ft.fraud_risk_score DESC;

-- View: Open alerts dashboard
CREATE OR REPLACE VIEW v_open_alerts AS
SELECT
    fa.*,
    taa.total_transactions,
    taa.performed_by
FROM fraud_alerts fa
JOIN transaction_analysis_audit taa ON fa.execution_id = taa.execution_id
WHERE fa.status = 'open'
ORDER BY
    CASE fa.severity
        WHEN 'critical' THEN 1
        WHEN 'high' THEN 2
        ELSE 3
    END,
    fa.created_at DESC;
