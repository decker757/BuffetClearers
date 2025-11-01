from raganything import RAGAnything, RAGAnythingConfig
from lightrag.llm.openai import openai_complete_if_cache  # still usable with Groq endpoint
from lightrag.utils import EmbeddingFunc
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv
import os, json, asyncio
import sys

# Add parent directory to path for utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.metadata_extractor import MetadataExtractor

load_dotenv()

class RAGProcessor:
    def __init__(self):
        # --- Use Groq API ---
        api_key = os.getenv('GROQ_KEY')
        base_url = "https://api.groq.com/openai/v1"

        # Create unique working directory for each instance to avoid conflicts
        import time
        import uuid
        working_dir = f"./rag_storage_{uuid.uuid4().hex[:8]}"

        # --- RAGAnything configuration ---
        config = RAGAnythingConfig(
            working_dir=working_dir,
            parser="mineru",
            parse_method="auto",
            enable_image_processing=False,  # Disabled - Groq doesn't support vision API
            enable_table_processing=True,
            enable_equation_processing=True,
            supported_file_extensions=['.pdf', '.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif',
                                      '.gif', '.webp', '.doc', '.docx', '.ppt', '.pptx',
                                      '.xls', '.xlsx', '.txt', '.md', '.csv']  # Added CSV support
        )

        self.working_dir = working_dir

        # --- LLM function using Groq ---
        async def llm_func(prompt, **kwargs):
            return await openai_complete_if_cache(
                "llama-3.3-70b-versatile", 
                prompt,
                api_key=api_key,
                base_url=base_url,
                **kwargs
            )

        model = SentenceTransformer("all-MiniLM-L6-v2")

        async def embedding_func_impl(texts):
            """Async wrapper for embedding function"""
            if isinstance(texts, str):
                texts = [texts]
            return model.encode(texts, convert_to_tensor=False).tolist()

        embedding_func = EmbeddingFunc(
            embedding_dim=384,  # MiniLM-L6 output dim
            max_token_size=512,
            func=embedding_func_impl,
        )

        # --- Initialize RAG engine ---
        self.engine = RAGAnything(
            config=config,
            llm_model_func=llm_func,
            embedding_func=embedding_func
        )

    def _convert_csv_to_text(self, file_path: str) -> str:
        """Convert CSV to readable text format for RAG processing"""
        import pandas as pd

        # Read CSV
        df = pd.read_csv(file_path)

        # Create a text representation
        text_parts = []
        text_parts.append(f"CSV Document Analysis: {os.path.basename(file_path)}\n")
        text_parts.append(f"Total Rows: {len(df)}, Total Columns: {len(df.columns)}\n")
        text_parts.append(f"Columns: {', '.join(df.columns)}\n\n")

        # Add sample data (first 100 rows to avoid overwhelming)
        text_parts.append("Data Preview:\n")
        text_parts.append(df.head(100).to_string(index=False))

        # Add statistics if numeric columns exist
        numeric_cols = df.select_dtypes(include=['number']).columns
        if len(numeric_cols) > 0:
            text_parts.append("\n\nNumeric Column Statistics:\n")
            text_parts.append(df[numeric_cols].describe().to_string())

        # Save as temporary text file
        txt_path = file_path.rsplit('.', 1)[0] + '_converted.txt'
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(text_parts))

        return txt_path

    async def process_document(self, file_path: str):
        converted_file = None
        try:
            # Check if CSV and convert to text
            if file_path.lower().endswith('.csv'):
                print(f"Converting CSV file to text format: {file_path}")
                converted_file = self._convert_csv_to_text(file_path)
                file_to_process = converted_file
            else:
                file_to_process = file_path

            # Extract metadata first
            file_ext = os.path.splitext(file_path)[1].lower()
            metadata = {}
            extracted_text = ""

            if file_ext == '.pdf':
                metadata = MetadataExtractor.extract_pdf_metadata(file_to_process)
                # Extract text for completeness check
                try:
                    from PyPDF2 import PdfReader
                    reader = PdfReader(file_to_process)
                    for page in reader.pages:
                        text = page.extract_text()
                        if text:
                            extracted_text += text
                except:
                    pass

            # Get completeness indicators
            doc_type = metadata.get('document_type', 'unknown')
            completeness = MetadataExtractor.extract_completeness_indicators(extracted_text, doc_type)

            # Process with RAG
            await self.engine.process_document_complete(file_to_process)

            # Improved, structured prompt for better LLM analysis
            prompt = f"""Analyze this {doc_type if doc_type != 'unknown' else ''} document for compliance and completeness.

DOCUMENT CONTEXT:
- Type: {doc_type}
- Pages: {metadata.get('page_count', 'unknown')}
- Text Coverage: {metadata.get('text_coverage_percent', 0):.1f}%
- Scanned: {'Yes' if metadata.get('is_scanned', False) else 'No'}

Provide a structured assessment:

1. COMPLETENESS:
   - Are all required sections present (date, parties, amounts, signatures, terms)?
   - Missing elements detected: {', '.join(completeness.get('missing_elements', [])) or 'None'}

2. FORMATTING:
   - Is the document properly formatted and consistent?
   - Are there any formatting anomalies or irregularities?

3. COMPLIANCE:
   - Does the document meet standard regulatory requirements for {doc_type}?
   - Are there any compliance red flags or concerns?

4. AUTHENTICITY INDICATORS:
   - Are there signs of tampering, alterations, or forgery?
   - Is the document structure consistent with legitimate {doc_type} documents?

Provide a clear verdict: COMPLIANT, REVIEW_REQUIRED, or NON_COMPLIANT with specific reasons."""

            result = await self.engine.aquery(prompt, mode="hybrid")

            # Parse LLM result and determine status
            llm_response = str(result) if result else ""
            status = self._determine_status(llm_response, completeness)

            # Build enhanced response
            enhanced_result = {
                "status": status,
                "llm_analysis": llm_response,
                "metadata": metadata,
                "completeness": completeness,
                "confidence_score": self._calculate_confidence(metadata, completeness, llm_response),
                "issues_detected": self._extract_issues(llm_response, completeness)
            }

            return json.dumps(enhanced_result, indent=2, default=str)
        finally:
            # Clean up converted file
            if converted_file and os.path.exists(converted_file):
                try:
                    os.remove(converted_file)
                except Exception as e:
                    print(f"Warning: Could not delete converted file {converted_file}: {e}")

            # Clean up working directory
            import shutil
            if os.path.exists(self.working_dir):
                try:
                    shutil.rmtree(self.working_dir)
                except Exception as e:
                    print(f"Warning: Could not delete RAG storage directory {self.working_dir}: {e}")

    def _determine_status(self, llm_response: str, completeness: dict) -> str:
        """Determine explicit document status based on LLM response and completeness"""
        llm_lower = llm_response.lower()

        # Check for explicit verdicts in LLM response
        if 'non_compliant' in llm_lower or 'non-compliant' in llm_lower:
            return "FAILED"
        if 'review_required' in llm_lower or 'review required' in llm_lower:
            return "REVIEW_REQUIRED"
        if 'compliant' in llm_lower:
            return "PASS"

        # Fall back to completeness score
        completeness_score = completeness.get('completeness_score', 0)

        if completeness_score < 50:
            return "INCOMPLETE"
        elif completeness_score < 80:
            return "REVIEW_REQUIRED"
        else:
            return "PASS"

    def _calculate_confidence(self, metadata: dict, completeness: dict, llm_response: str) -> float:
        """Calculate confidence score for the analysis"""
        confidence = 100.0

        # Penalize for missing metadata
        if not metadata.get('page_count'):
            confidence -= 10

        # Penalize for low text coverage (scanned docs)
        text_coverage = metadata.get('text_coverage_percent', 0)
        if text_coverage < 30:
            confidence -= 20
        elif text_coverage < 60:
            confidence -= 10

        # Penalize for low completeness
        completeness_score = completeness.get('completeness_score', 0)
        if completeness_score < 50:
            confidence -= 20
        elif completeness_score < 80:
            confidence -= 10

        # Penalize if LLM response is very short (uncertain)
        if len(llm_response) < 100:
            confidence -= 15

        return max(0, min(100, confidence))

    def _extract_issues(self, llm_response: str, completeness: dict) -> list:
        """Extract specific issues from analysis"""
        issues = []

        # Add missing elements from completeness check
        missing_elements = completeness.get('missing_elements', [])
        for element in missing_elements:
            issues.append({
                "type": "missing_content",
                "severity": "MEDIUM",
                "description": element
            })

        # Parse LLM response for issues
        llm_lower = llm_response.lower()

        if 'tamper' in llm_lower or 'alter' in llm_lower:
            issues.append({
                "type": "authenticity_concern",
                "severity": "HIGH",
                "description": "Possible tampering or alterations detected"
            })

        if 'incomplete' in llm_lower:
            issues.append({
                "type": "completeness",
                "severity": "MEDIUM",
                "description": "Document appears incomplete"
            })

        if 'formatting' in llm_lower and ('issue' in llm_lower or 'irregular' in llm_lower):
            issues.append({
                "type": "formatting",
                "severity": "LOW",
                "description": "Formatting irregularities detected"
            })

        return issues