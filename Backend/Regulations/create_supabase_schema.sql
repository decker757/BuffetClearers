-- ================================================================
-- AML RULES DATABASE SCHEMA FOR SUPABASE
-- ================================================================
-- Run this SQL in your Supabase SQL Editor to create the tables

-- 1. REGULATORS TABLE
-- Store information about regulatory authorities
CREATE TABLE IF NOT EXISTS regulators (
    id SERIAL PRIMARY KEY,
    regulator_code VARCHAR(10) UNIQUE NOT NULL, -- FINMA, MAS, HKMA
    regulator_name TEXT NOT NULL,
    jurisdiction VARCHAR(100) NOT NULL,
    country_code VARCHAR(3) NOT NULL,
    website TEXT,
    primary_currency VARCHAR(3),
    aml_authority TEXT,
    aml_authority_full_name TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. REGULATORY DOCUMENTS TABLE
-- Store document metadata
CREATE TABLE IF NOT EXISTS regulatory_documents (
    id SERIAL PRIMARY KEY,
    document_id VARCHAR(50) UNIQUE NOT NULL,
    regulator_code VARCHAR(10) REFERENCES regulators(regulator_code),
    title TEXT NOT NULL,
    url TEXT,
    document_type VARCHAR(50), -- circular, guideline, notice, etc.
    effective_date DATE,
    status VARCHAR(20) DEFAULT 'active', -- active, superseded, draft
    original_language VARCHAR(10),
    translated BOOLEAN DEFAULT FALSE,
    extraction_confidence FLOAT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. AML RULES TABLE (Main table for extracted rules)
-- Store the actual extracted rules
CREATE TABLE IF NOT EXISTS aml_rules (
    id SERIAL PRIMARY KEY,
    rule_id VARCHAR(50) UNIQUE NOT NULL,
    document_id VARCHAR(50) REFERENCES regulatory_documents(document_id),
    rule_type VARCHAR(50) NOT NULL, -- threshold_reporting, customer_due_diligence, etc.
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    
    -- Rule conditions (stored as JSONB for flexibility)
    conditions JSONB,
    main_points JSONB,
    
    -- Threshold information (for threshold-based rules)
    threshold_amount DECIMAL(15,2),
    threshold_currency VARCHAR(3),
    
    -- Reporting details
    reporting_authority VARCHAR(100),
    reporting_timeframe VARCHAR(50),
    
    -- Other attributes
    applies_to JSONB, -- Array of entities this applies to
    required_approval VARCHAR(100),
    monitoring_frequency VARCHAR(50),
    ownership_threshold VARCHAR(10),
    exceptions JSONB,
    update_frequency VARCHAR(50),
    
    -- Confidence and quality metrics
    confidence FLOAT NOT NULL DEFAULT 0.5,
    manual_review_required BOOLEAN DEFAULT FALSE,
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Indexes for better performance
    CONSTRAINT valid_confidence CHECK (confidence >= 0 AND confidence <= 1)
);

-- 4. RULE_KEYWORDS TABLE
-- Store keywords for better searchability
CREATE TABLE IF NOT EXISTS rule_keywords (
    id SERIAL PRIMARY KEY,
    rule_id VARCHAR(50) REFERENCES aml_rules(rule_id),
    keyword VARCHAR(100) NOT NULL,
    relevance_score FLOAT DEFAULT 1.0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 5. EXTRACTION_LOG TABLE
-- Track extraction activities and performance
CREATE TABLE IF NOT EXISTS extraction_log (
    id SERIAL PRIMARY KEY,
    document_id VARCHAR(50) REFERENCES regulatory_documents(document_id),
    extraction_method VARCHAR(50),
    rules_extracted INTEGER DEFAULT 0,
    average_confidence FLOAT,
    extraction_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    processing_time_seconds FLOAT,
    notes TEXT
);

-- ================================================================
-- INDEXES FOR PERFORMANCE
-- ================================================================

-- Indexes on frequently queried columns
CREATE INDEX IF NOT EXISTS idx_aml_rules_rule_type ON aml_rules(rule_type);
CREATE INDEX IF NOT EXISTS idx_aml_rules_document_id ON aml_rules(document_id);
CREATE INDEX IF NOT EXISTS idx_aml_rules_confidence ON aml_rules(confidence);
CREATE INDEX IF NOT EXISTS idx_aml_rules_threshold_amount ON aml_rules(threshold_amount);
CREATE INDEX IF NOT EXISTS idx_aml_rules_threshold_currency ON aml_rules(threshold_currency);
CREATE INDEX IF NOT EXISTS idx_regulatory_documents_regulator ON regulatory_documents(regulator_code);
CREATE INDEX IF NOT EXISTS idx_rule_keywords_keyword ON rule_keywords(keyword);

-- JSONB indexes for fast queries on conditions and main_points
CREATE INDEX IF NOT EXISTS idx_aml_rules_conditions_gin ON aml_rules USING GIN(conditions);
CREATE INDEX IF NOT EXISTS idx_aml_rules_main_points_gin ON aml_rules USING GIN(main_points);

-- ================================================================
-- INSERT SAMPLE REGULATORS
-- ================================================================

-- Insert the three regulators we're working with
INSERT INTO regulators (regulator_code, regulator_name, jurisdiction, country_code, website, primary_currency, aml_authority, aml_authority_full_name) 
VALUES 
    ('FINMA', 'Swiss Financial Market Supervisory Authority', 'Switzerland', 'CH', 'https://www.finma.ch', 'CHF', 'MROS', 'Money Laundering Reporting Office Switzerland'),
    ('MAS', 'Monetary Authority of Singapore', 'Singapore', 'SG', 'https://www.mas.gov.sg', 'SGD', 'SPF_CAD', 'Singapore Police Force Commercial Affairs Department'),
    ('HKMA', 'Hong Kong Monetary Authority', 'Hong Kong', 'HK', 'https://www.hkma.gov.hk', 'HKD', 'JFIU', 'Joint Financial Intelligence Unit')
ON CONFLICT (regulator_code) DO NOTHING;

-- ================================================================
-- HELPFUL FUNCTIONS
-- ================================================================

-- Function to get rules by threshold amount
CREATE OR REPLACE FUNCTION get_rules_by_threshold(
    min_amount DECIMAL DEFAULT 0,
    currency_code VARCHAR(3) DEFAULT NULL
)
RETURNS TABLE (
    rule_id VARCHAR(50),
    title TEXT,
    threshold_amount DECIMAL(15,2),
    threshold_currency VARCHAR(3),
    regulator_code VARCHAR(10)
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        ar.rule_id,
        ar.title,
        ar.threshold_amount,
        ar.threshold_currency,
        rd.regulator_code
    FROM aml_rules ar
    JOIN regulatory_documents rd ON ar.document_id = rd.document_id
    WHERE ar.threshold_amount >= min_amount
    AND (currency_code IS NULL OR ar.threshold_currency = currency_code)
    ORDER BY ar.threshold_amount ASC;
END;
$$ LANGUAGE plpgsql;

-- Function to search rules by keyword
CREATE OR REPLACE FUNCTION search_rules_by_keyword(search_term TEXT)
RETURNS TABLE (
    rule_id VARCHAR(50),
    title TEXT,
    description TEXT,
    rule_type VARCHAR(50),
    relevance_score FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        ar.rule_id,
        ar.title,
        ar.description,
        ar.rule_type,
        rk.relevance_score
    FROM aml_rules ar
    JOIN rule_keywords rk ON ar.rule_id = rk.rule_id
    WHERE LOWER(rk.keyword) LIKE LOWER('%' || search_term || '%')
       OR LOWER(ar.title) LIKE LOWER('%' || search_term || '%')
       OR LOWER(ar.description) LIKE LOWER('%' || search_term || '%')
    ORDER BY rk.relevance_score DESC, ar.confidence DESC;
END;
$$ LANGUAGE plpgsql;

-- ================================================================
-- VIEWS FOR EASY QUERYING
-- ================================================================

-- View: Complete rule information with regulator details
CREATE OR REPLACE VIEW v_complete_rules AS
SELECT 
    ar.rule_id,
    ar.title,
    ar.description,
    ar.rule_type,
    ar.conditions,
    ar.main_points,
    ar.threshold_amount,
    ar.threshold_currency,
    ar.reporting_authority,
    ar.reporting_timeframe,
    ar.confidence,
    rd.document_id,
    rd.title as document_title,
    rd.url as document_url,
    rd.effective_date,
    r.regulator_code,
    r.regulator_name,
    r.jurisdiction,
    r.country_code
FROM aml_rules ar
JOIN regulatory_documents rd ON ar.document_id = rd.document_id
JOIN regulators r ON rd.regulator_code = r.regulator_code;

-- View: Rules summary by regulator
CREATE OR REPLACE VIEW v_rules_by_regulator AS
SELECT 
    r.regulator_code,
    r.regulator_name,
    COUNT(ar.id) as total_rules,
    COUNT(CASE WHEN ar.rule_type = 'threshold_reporting' THEN 1 END) as threshold_rules,
    COUNT(CASE WHEN ar.rule_type = 'customer_due_diligence' THEN 1 END) as cdd_rules,
    COUNT(CASE WHEN ar.rule_type = 'suspicious_activity_reporting' THEN 1 END) as sar_rules,
    AVG(ar.confidence) as average_confidence,
    COUNT(CASE WHEN ar.manual_review_required = true THEN 1 END) as needs_review
FROM regulators r
LEFT JOIN regulatory_documents rd ON r.regulator_code = rd.regulator_code
LEFT JOIN aml_rules ar ON rd.document_id = ar.document_id
GROUP BY r.regulator_code, r.regulator_name
ORDER BY total_rules DESC;

-- ================================================================
-- ENABLE ROW LEVEL SECURITY (Optional - for production)
-- ================================================================

-- Uncomment these if you want to enable RLS
-- ALTER TABLE regulators ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE regulatory_documents ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE aml_rules ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE rule_keywords ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE extraction_log ENABLE ROW LEVEL SECURITY;

-- ================================================================
-- COMPLETION MESSAGE
-- ================================================================

DO $$
BEGIN
    RAISE NOTICE '✅ AML Rules Database Schema Created Successfully!';
    RAISE NOTICE '📊 Tables created: regulators, regulatory_documents, aml_rules, rule_keywords, extraction_log';
    RAISE NOTICE '🔍 Indexes created for optimal performance';
    RAISE NOTICE '📁 Views created: v_complete_rules, v_rules_by_regulator';
    RAISE NOTICE '⚙️  Functions created: get_rules_by_threshold(), search_rules_by_keyword()';
    RAISE NOTICE '🚀 Ready to import AML rules from JSON!';
END $$;