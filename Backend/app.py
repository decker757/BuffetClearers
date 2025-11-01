from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from datetime import datetime
from supabase import create_client
from dotenv import load_dotenv
import asyncio
import os
import json
import psycopg2

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-here')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

CORS(app, resources={r"/api/*": {"origins": "*"}})
socketio = SocketIO(app, cors_allowed_origins="*")

# Init AML system
aml_system = None

# Supabase connection
supabase = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_PUBLIC_KEY')
)

# Jigsaw API
JIGSAW_API = os.getenv('JIGSAW_API_KEY')

# PostgreSQL credentials
USER = os.getenv("user")
PASSWORD = os.getenv("password")
HOST = os.getenv("host")
PORT = os.getenv("port")
DBNAME = os.getenv("dbname")


def check_postgres_connection():
    """Check direct PostgreSQL connection."""
    try:
        connection = psycopg2.connect(
            user=USER,
            password=PASSWORD,
            host=HOST,
            port=PORT,
            dbname=DBNAME
        )
        cursor = connection.cursor()
        cursor.execute("SELECT NOW();")
        result = cursor.fetchone()
        cursor.close()
        connection.close()
        print("Postgres connection successful. Time:", result)
        return True
    except Exception as e:
        print(f"Postgres connection failed: {e}")
        return False


def check_supabase_connection():
    """Check Supabase connection health."""
    try:
        supabase.table('regulatory_rules').select('id').limit(1).execute()
        return True
    except Exception as e:
        print("Supabase connection error:", e)
        return False


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'services': {
            'flask': True,
            'supabase': check_supabase_connection(),
            'postgres': check_postgres_connection(),
            'jigsaw': True
        }
    })

@app.route('/api/scrape', methods=['GET'])
def scrape_pdfs(url):
    pass


@app.route('/api/validate', methods=['POST'])
def validate_document():
    """
    Comprehensive document validation endpoint
    Performs all 4 components of analysis and returns detailed report
    """
    try:
        # Check if file is present in request
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['file']

        # Check if file is empty
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        # Check file extension
        allowed_extensions = {'.pdf', '.docx', '.doc', '.txt', '.png', '.jpg', '.jpeg', '.csv', '.xlsx', '.xls'}
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in allowed_extensions:
            return jsonify({'error': f'File type {file_ext} not allowed. Allowed types: {", ".join(allowed_extensions)}'}), 400

        # Ensure uploads directory exists
        uploads_dir = os.path.join(os.path.dirname(__file__), 'uploads')
        os.makedirs(uploads_dir, exist_ok=True)

        # Save file with secure filename
        file_path = os.path.join(uploads_dir, file.filename)
        file.save(file_path)

        # Import analysis modules
        from document_corroboration.processing_engine import RAGProcessor
        from document_corroboration.format_validator import FormatValidator
        from document_corroboration.image_analyzer import ImageAnalyzer
        from document_corroboration.risk_scorer import RiskScorer

        # Initialize results
        document_analysis = None
        format_validation = None
        image_analysis = None

        # Component 1: Document Processing (RAG Analysis)
        try:
            processor = RAGProcessor()
            rag_result = asyncio.run(processor.process_document(file_path))
            print(f"RAG result type: {type(rag_result)}")
            print(f"RAG result preview: {str(rag_result)[:200]}")

            # rag_result is already a JSON string, parse it
            if isinstance(rag_result, str):
                document_analysis = json.loads(rag_result)
            else:
                document_analysis = rag_result
        except json.JSONDecodeError as e:
            print(f"Document processing JSON error: {e}")
            print(f"Failed to parse: {str(rag_result)[:500]}")
            document_analysis = {"error": f"Invalid JSON response: {str(e)}"}
        except Exception as e:
            print(f"Document processing error: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            document_analysis = {"error": str(e)}

        # Component 2: Format Validation
        if file_ext in ['.pdf', '.txt', '.doc', '.docx']:
            try:
                validator = FormatValidator()
                format_validation = validator.validate_document(file_path)
            except Exception as e:
                print(f"Format validation error: {e}")
                format_validation = {"error": str(e)}

        # Component 3: Image Analysis
        if file_ext in ['.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.gif']:
            try:
                image_analyzer = ImageAnalyzer()
                image_analysis = image_analyzer.analyze_image(file_path)
            except Exception as e:
                print(f"Image analysis error: {e}")
                image_analysis = {"error": str(e)}

        # Component 4: Risk Scoring & Reporting
        risk_scorer = RiskScorer()
        risk_assessment = risk_scorer.calculate_comprehensive_risk(
            document_analysis=document_analysis,
            format_validation=format_validation,
            image_analysis=image_analysis
        )

        # Generate comprehensive report
        report = risk_scorer.generate_report(
            file_name=file.filename,
            risk_assessment=risk_assessment,
            document_analysis=document_analysis,
            format_validation=format_validation,
            image_analysis=image_analysis,
            save_to_file=True
        )

        # Clean up uploaded file after processing
        try:
            os.remove(file_path)
        except Exception as e:
            print(f"Warning: Could not delete temporary file {file_path}: {e}")

        return jsonify(report), 200

    except Exception as e:
        print(f"FATAL ERROR in validate_document: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'error': f'Document validation failed: {str(e)}',
            'error_type': type(e).__name__
        }), 500


@app.route('/api/validate/format', methods=['POST'])
def validate_format_only():
    """Format validation only (Component 2)"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['file']
        file_ext = os.path.splitext(file.filename)[1].lower()

        if file_ext not in ['.pdf', '.txt', '.doc', '.docx']:
            return jsonify({'error': 'Format validation only supports text/document files'}), 400

        uploads_dir = os.path.join(os.path.dirname(__file__), 'uploads')
        os.makedirs(uploads_dir, exist_ok=True)
        file_path = os.path.join(uploads_dir, file.filename)
        file.save(file_path)

        from document_corroboration.format_validator import FormatValidator
        validator = FormatValidator()
        result = validator.validate_document(file_path)

        os.remove(file_path)
        return jsonify(result), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/validate/image', methods=['POST'])
def validate_image_only():
    """Image analysis only (Component 3)"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['file']
        file_ext = os.path.splitext(file.filename)[1].lower()

        if file_ext not in ['.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.gif']:
            return jsonify({'error': 'Image analysis only supports image files'}), 400

        uploads_dir = os.path.join(os.path.dirname(__file__), 'uploads')
        os.makedirs(uploads_dir, exist_ok=True)
        file_path = os.path.join(uploads_dir, file.filename)
        file.save(file_path)

        from document_corroboration.image_analyzer import ImageAnalyzer
        analyzer = ImageAnalyzer()
        result = analyzer.analyze_image(file_path)

        os.remove(file_path)
        return jsonify(result), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/audit/history', methods=['GET'])
def get_audit_history():
    """Retrieve audit history"""
    try:
        from document_corroboration.risk_scorer import RiskScorer

        file_name = request.args.get('file_name')
        limit = int(request.args.get('limit', 10))

        scorer = RiskScorer()
        history = scorer.get_audit_history(file_name=file_name, limit=limit)

        return jsonify({'history': history, 'count': len(history)}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5001, debug=True)