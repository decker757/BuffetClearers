-- Create table for document validations
CREATE TABLE IF NOT EXISTS document_validations (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    file_name TEXT NOT NULL,
    file_hash TEXT NOT NULL,
    file_size INTEGER NOT NULL,
    mime_type TEXT,
    risk_score DECIMAL(5,2),
    status TEXT CHECK (status IN ('APPROVED', 'APPROVED_WITH_NOTES', 'REVIEW_REQUIRED', 'REJECTED')),
    report_id TEXT UNIQUE NOT NULL,
    report_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_file_hash ON document_validations(file_hash);
CREATE INDEX IF NOT EXISTS idx_file_name ON document_validations(file_name);
CREATE INDEX IF NOT EXISTS idx_status ON document_validations(status);
CREATE INDEX IF NOT EXISTS idx_created_at ON document_validations(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_risk_score ON document_validations(risk_score);

-- Create trigger for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_document_validations_updated_at BEFORE UPDATE
    ON document_validations FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Add comment
COMMENT ON TABLE document_validations IS 'Stores document validation results with risk scores and analysis reports';
