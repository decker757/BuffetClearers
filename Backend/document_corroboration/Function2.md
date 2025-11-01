@ -1,259 +0,0 @@
# Document Corroboration System

Comprehensive document validation system with 4 integrated components for detecting fraudulent or non-compliant documents.

## Architecture

```
document_corroboration/
├── processing_engine.py    # Component 1: Document Processing Engine
├── format_validator.py     # Component 2: Format Validation System
├── image_analyzer.py       # Component 3: Image Analysis Engine
└── risk_scorer.py          # Component 4: Risk Scoring & Reporting
```

## Components

### 1. Document Processing Engine (`processing_engine.py`)
**Technologies:** RAGAnything + Groq LLM + SentenceTransformers

**Capabilities:**
- Multi-format support (PDF, DOCX, DOC, TXT, CSV, XLSX, XLS)
- Content extraction using MineRU parser
- Table and equation processing
- AI-powered content analysis
- Compliance checking

### 2. Format Validation System (`format_validator.py`)
**Detects:**
- Double spacing and irregular formatting
- Inconsistent indentation
- Spelling mistakes
- Missing required sections
- Incomplete sentences
- Unbalanced parentheses/brackets
- Document structure issues

### 3. Image Analysis Engine (`image_analyzer.py`)
**Detects:**
- Missing or stripped EXIF metadata
- Software editing indicators
- Pixel-level tampering
- Clone stamp usage
- AI-generated images
- Metadata anomalies

### 4. Risk Scoring & Reporting (`risk_scorer.py`)
**Features:**
- Comprehensive risk scoring (0-100)
- Multi-factor analysis integration
- Automated report generation
- Audit trail maintenance
- Action item generation
- Real-time compliance feedback

## API Endpoints

### Comprehensive Validation
```bash
POST /api/validate
```
Performs all 4 components of analysis and returns a detailed report.

**Example:**
```bash
curl -X POST -F "file=@document.pdf" http://localhost:5001/api/validate
```

**Response:**
```json
{
  "report_id": "a1b2c3d4e5f6",
  "file_name": "document.pdf",
  "analysis_timestamp": "2025-11-01T15:30:00",
  "summary": {
    "overall_risk_score": 25.5,
    "status": "APPROVED_WITH_NOTES",
    "max_severity": "MEDIUM",
    "recommendation": "Document is acceptable but has minor issues"
  },
  "detailed_analysis": {
    "document_processing": {...},
    "format_validation": {...},
    "image_analysis": {...}
  },
  "risk_factors": [...],
  "action_items": [...]
}
```

### Format Validation Only
```bash
POST /api/validate/format
```
Validates document formatting only (text/document files).

**Example:**
```bash
curl -X POST -F "file=@report.docx" http://localhost:5001/api/validate/format
```

### Image Analysis Only
```bash
POST /api/validate/image
```
Analyzes image authenticity only.

**Example:**
```bash
curl -X POST -F "file=@photo.jpg" http://localhost:5001/api/validate/image
```

### Audit History
```bash
GET /api/audit/history?file_name=document.pdf&limit=10
```
Retrieve audit history for analyzed documents.

## Risk Scoring

### Status Levels
- **APPROVED** (0-20): Document meets all requirements
- **APPROVED_WITH_NOTES** (20-40): Minor issues noted
- **REVIEW_REQUIRED** (40-70): Manual review needed
- **REJECTED** (70-100): Does not meet requirements

### Severity Levels
- **LOW**: 5 points
- **MEDIUM**: 15 points
- **HIGH**: 30 points

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export GROQ_KEY="your_groq_api_key"

# Run server
python app.py
```

## Usage Examples

### Python Example
```python
import requests

# Validate a PDF document
with open('contract.pdf', 'rb') as f:
    response = requests.post(
        'http://localhost:5001/api/validate',
        files={'file': f}
    )

report = response.json()
print(f"Risk Score: {report['summary']['overall_risk_score']}")
print(f"Status: {report['summary']['status']}")
```

### JavaScript Example
```javascript
const formData = new FormData();
formData.append('file', fileInput.files[0]);

fetch('http://localhost:5001/api/validate', {
    method: 'POST',
    body: formData
})
.then(res => res.json())
.then(report => {
    console.log('Risk Score:', report.summary.overall_risk_score);
    console.log('Status:', report.summary.status);
});
```

## Audit Trail

All analysis reports are automatically saved to `./audit_logs/` with the following naming convention:
```
audit_{report_id}_{timestamp}.json
```

## Supported File Types

**Documents:**
- PDF (.pdf)
- Word (.doc, .docx)
- Text (.txt)
- CSV (.csv)
- Excel (.xls, .xlsx)

**Images:**
- JPEG (.jpg, .jpeg)
- PNG (.png)
- BMP (.bmp)
- TIFF (.tiff, .tif)
- GIF (.gif)

## Advanced Features

### Custom Query Modification
Edit `processing_engine.py` line 68-70 to customize the RAG query:
```python
result = await self.engine.aquery(
    "Your custom compliance question here",
    mode="hybrid"
)
```

### Risk Threshold Customization
Edit `risk_scorer.py` `_determine_status()` method to adjust thresholds.

### Format Rules
Add custom format rules in `format_validator.py` `_check_content_validation()` method.

## Performance

- **Document Processing:** 10-30 seconds (depending on size)
- **Format Validation:** <1 second
- **Image Analysis:** 1-3 seconds
- **Risk Scoring:** <1 second

## Limitations

- Image analysis uses heuristic methods (not deep learning)
- Format validation is rule-based
- CSV files converted to text before RAG processing
- Image processing disabled for Groq (no vision API)

## Future Enhancements

1. Deep learning-based image forgery detection
2. Template matching with custom templates
3. OCR for scanned documents
4. Batch processing support
5. WebSocket real-time progress updates
6. Integration with reverse image search APIs
7. Advanced linguistic analysis for authenticity

## Troubleshooting

**Error: "GROQ_KEY not set"**
- Set environment variable: `export GROQ_KEY="your_key"`

**Error: "Event loop already running"**
- Each request creates isolated RAG storage to prevent conflicts

**Error: "Module not found"**
- Run: `pip install -r requirements.txt`

## Contributing

When adding new validation rules:
1. Add detection logic to appropriate module
2. Update severity scoring in `risk_scorer.py`
3. Add corresponding action items
4. Update this documentation