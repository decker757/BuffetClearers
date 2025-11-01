from raganything import RAGAnything, RAGAnythingConfig
from lightrag.llm.openai import openai_complete_if_cache  # still usable with Groq endpoint
from lightrag.utils import EmbeddingFunc
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv
import os, json, asyncio

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

            await self.engine.process_document_complete(file_to_process)
            result = await self.engine.aquery(
                "Is this document complete, properly formatted, and compliant?",
                mode="hybrid"
            )

            # Ensure result is serializable
            if result is None:
                return json.dumps({"error": "No result from query", "status": "failed"}, indent=2)

            # If result is already a string, return it
            if isinstance(result, str):
                # Try to parse and re-serialize to ensure valid JSON
                try:
                    parsed = json.loads(result)
                    return json.dumps(parsed, indent=2)
                except:
                    # If not JSON, wrap it
                    return json.dumps({"response": result}, indent=2)

            # Otherwise serialize the object
            return json.dumps(result, indent=2, default=str)
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