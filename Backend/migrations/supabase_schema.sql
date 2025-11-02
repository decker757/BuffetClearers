-- ============================================================
-- Supabase Schema for Enhanced Transaction Analysis API
-- ============================================================

-- 1. AUDIT TRAIL TABLE
-- Tracks every analysis execution with full metadata
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
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Indexes for performance
    INDEX idx_execution_id (execution_id),
    INDEX idx_timestamp (timestamp),
    INDEX idx_performed_by (performed_by),
    INDEX idx_high_risk_count (high_risk_count)
);

-- Enable Row Level Security
ALTER TABLE transaction_analysis_audit ENABLE ROW LEVEL SECURITY;

-- RLS Policy: Allow authenticated users to read
CREATE POLICY "Enable read access for authenticated users"
ON transaction_analysis_audit FOR SELECT
TO authenticated
USING (true);

-- RLS Policy: Allow system to insert
CREATE POLICY "Enable insert for system"
ON transaction_analysis_audit FOR INSERT
TO authenticated
WITH CHECK (true);


-- 2. FLAGGED TRANSACTIONS TABLE
-- Stores high-risk transactions (fraud_score >= 60) for review
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

    -- Foreign key to audit trail
    CONSTRAINT fk_execution
        FOREIGN KEY (execution_id)
        REFERENCES transaction_analysis_audit(execution_id)
        ON DELETE CASCADE,

    -- Indexes
    INDEX idx_execution_id (execution_id),
    INDEX idx_transaction_id (transaction_id),
    INDEX idx_fraud_score (fraud_risk_score DESC),
    INDEX idx_risk_category (risk_category),
    INDEX idx_status (status),
    INDEX idx_assigned_to (assigned_to),
    INDEX idx_created_at (created_at DESC)
);

-- Enable RLS
ALTER TABLE flagged_transactions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Enable read access for authenticated users"
ON flagged_transactions FOR SELECT
TO authenticated
USING (true);

CREATE POLICY "Enable insert for system"
ON flagged_transactions FOR INSERT
TO authenticated
WITH CHECK (true);

CREATE POLICY "Enable update for authenticated users"
ON flagged_transactions FOR UPDATE
TO authenticated
USING (true);


-- 3. FRAUD ALERTS TABLE
-- Critical alerts for transactions with fraud_score >= 80
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

    -- Foreign key
    CONSTRAINT fk_execution
        FOREIGN KEY (execution_id)
        REFERENCES transaction_analysis_audit(execution_id)
        ON DELETE CASCADE,

    -- Indexes
    INDEX idx_execution_id (execution_id),
    INDEX idx_transaction_id (transaction_id),
    INDEX idx_severity (severity),
    INDEX idx_status (status),
    INDEX idx_assigned_to (assigned_to),
    INDEX idx_created_at (created_at DESC)
);

-- Enable RLS
ALTER TABLE fraud_alerts ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Enable read access for authenticated users"
ON fraud_alerts FOR SELECT
TO authenticated
USING (true);

CREATE POLICY "Enable all for authenticated users"
ON fraud_alerts FOR ALL
TO authenticated
USING (true);


-- 4. TRANSACTION FEEDBACK TABLE
-- Manual review feedback from analysts
CREATE TABLE IF NOT EXISTS transaction_feedback (
    id BIGSERIAL PRIMARY KEY,
    execution_id UUID NOT NULL,
    transaction_id VARCHAR(255) NOT NULL,
    reviewer VARCHAR(255) NOT NULL,
    decision VARCHAR(50) NOT NULL,
    notes TEXT,
    reviewed_at TIMESTAMP WITH TIME ZONE NOT NULL,
    reviewed BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Constraints
    CONSTRAINT valid_decision
        CHECK (decision IN ('confirmed_fraud', 'false_positive', 'needs_investigation', 'legitimate')),

    -- Foreign key
    CONSTRAINT fk_execution
        FOREIGN KEY (execution_id)
        REFERENCES transaction_analysis_audit(execution_id)
        ON DELETE CASCADE,

    -- Indexes
    INDEX idx_execution_id (execution_id),
    INDEX idx_transaction_id (transaction_id),
    INDEX idx_reviewer (reviewer),
    INDEX idx_decision (decision),
    INDEX idx_reviewed_at (reviewed_at DESC)
);

-- Enable RLS
ALTER TABLE transaction_feedback ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Enable all for authenticated users"
ON transaction_feedback FOR ALL
TO authenticated
USING (true);


-- ============================================================
-- FUNCTIONS & TRIGGERS
-- ============================================================

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers for updated_at
CREATE TRIGGER update_flagged_transactions_updated_at
    BEFORE UPDATE ON flagged_transactions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_fraud_alerts_updated_at
    BEFORE UPDATE ON fraud_alerts
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();


-- ============================================================
-- VIEWS FOR ANALYTICS
-- ============================================================

-- View: Recent High-Risk Transactions
CREATE OR REPLACE VIEW recent_high_risk_transactions AS
SELECT
    ft.id,
    ft.execution_id,
    ft.transaction_id,
    ft.amount,
    ft.fraud_risk_score,
    ft.risk_category,
    ft.alert_count,
    ft.status,
    ft.assigned_to,
    ft.created_at,
    taa.data_source,
    taa.performed_by,
    taa.timestamp as analysis_timestamp
FROM flagged_transactions ft
JOIN transaction_analysis_audit taa ON ft.execution_id = taa.execution_id
WHERE ft.created_at >= NOW() - INTERVAL '30 days'
ORDER BY ft.fraud_risk_score DESC, ft.created_at DESC;


-- View: Alert Dashboard
CREATE OR REPLACE VIEW alert_dashboard AS
SELECT
    fa.id,
    fa.execution_id,
    fa.transaction_id,
    fa.alert_type,
    fa.severity,
    fa.fraud_score,
    fa.status,
    fa.assigned_to,
    fa.created_at,
    fa.description,
    taa.total_transactions,
    taa.performed_by
FROM fraud_alerts fa
JOIN transaction_analysis_audit taa ON fa.execution_id = taa.execution_id
WHERE fa.status = 'open'
ORDER BY
    CASE fa.severity
        WHEN 'critical' THEN 1
        WHEN 'high' THEN 2
        WHEN 'medium' THEN 3
        ELSE 4
    END,
    fa.created_at DESC;


-- View: Analysis Performance Metrics
CREATE OR REPLACE VIEW analysis_performance_metrics AS
SELECT
    DATE(timestamp) as analysis_date,
    COUNT(*) as total_analyses,
    SUM(total_transactions) as total_transactions_processed,
    AVG(average_fraud_score) as avg_fraud_score,
    SUM(high_risk_count) as total_high_risk,
    ROUND(AVG(high_risk_count::DECIMAL / NULLIF(total_transactions, 0) * 100), 2) as avg_high_risk_percentage
FROM transaction_analysis_audit
GROUP BY DATE(timestamp)
ORDER BY analysis_date DESC;


-- View: Feedback Analysis
CREATE OR REPLACE VIEW feedback_analysis AS
SELECT
    decision,
    COUNT(*) as count,
    ROUND(COUNT(*)::DECIMAL / (SELECT COUNT(*) FROM transaction_feedback) * 100, 2) as percentage
FROM transaction_feedback
GROUP BY decision
ORDER BY count DESC;


-- ============================================================
-- SAMPLE QUERIES
-- ============================================================

/*
-- Get all analyses from the last 7 days
SELECT * FROM transaction_analysis_audit
WHERE timestamp >= NOW() - INTERVAL '7 days'
ORDER BY timestamp DESC;

-- Get pending high-risk transactions
SELECT * FROM flagged_transactions
WHERE status = 'pending_review'
AND fraud_risk_score >= 80
ORDER BY fraud_risk_score DESC;

-- Get open critical alerts
SELECT * FROM alert_dashboard
WHERE severity = 'critical';

-- Get feedback for a specific execution
SELECT * FROM transaction_feedback
WHERE execution_id = 'your-execution-id';

-- Model accuracy: Compare predictions with feedback
SELECT
    ft.fraud_risk_score,
    ft.risk_category,
    tf.decision,
    COUNT(*) as count
FROM flagged_transactions ft
JOIN transaction_feedback tf ON ft.execution_id = tf.execution_id
    AND ft.transaction_id = tf.transaction_id
GROUP BY ft.fraud_risk_score, ft.risk_category, tf.decision
ORDER BY ft.fraud_risk_score DESC;
*/


-- ============================================================
-- GRANTS (Adjust based on your security requirements)
-- ============================================================

-- Grant access to authenticated users (modify as needed)
GRANT SELECT ON ALL TABLES IN SCHEMA public TO authenticated;
GRANT INSERT ON transaction_analysis_audit TO authenticated;
GRANT INSERT ON flagged_transactions TO authenticated;
GRANT INSERT ON fraud_alerts TO authenticated;
GRANT ALL ON transaction_feedback TO authenticated;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO authenticated;
