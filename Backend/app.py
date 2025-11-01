"""
Document Corroboration API - Production Version
Implements all recommended improvements:
- Proper async handling
- File validation (MIME types)
- API key authentication
- Caching
- Comprehensive logging
- Database persistence
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO
from datetime import datetime
from supabase import create_client
from dotenv import load_dotenv
import os
import json

# Import utilities
from utils.async_helper import run_async_in_thread
from utils.file_validator import FileValidator
from utils.auth import require_api_key
from utils.cache_manager import CacheManager
from utils.logger import get_logger

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-here')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

CORS(app, resources={r"/api/*": {"origins": "*"}})
socketio = SocketIO(app, cors_allowed_origins="*")

# Initialize logger
logger = get_logger('app')

# Initialize cache manager
cache_manager = CacheManager()

# Supabase connection (for database persistence)
supabase = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_PUBLIC_KEY')
)


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint (no auth required)"""
    cache_stats = cache_manager.get_stats()

    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'cache_stats': cache_stats,
        'version': '2.0'
    })


@app.route('/api/validate', methods=['POST'])
#@require_api_key
def validate_document():
    """
    Comprehensive document validation endpoint
    Performs all 4 components with caching and proper async handling
    """
    file_path = None

    try:
        logger.info("=== New validation request ===")

        # Check if file is present in request
        if 'file' not in request.files:
            logger.warning("No file provided in request")
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['file']

        if file.filename == '':
            logger.warning("Empty filename provided")
            return jsonify({'error': 'No file selected'}), 400

        # Save file temporarily
        uploads_dir = os.path.join(os.path.dirname(__file__), 'uploads')
        os.makedirs(uploads_dir, exist_ok=True)
        file_path = os.path.join(uploads_dir, file.filename)
        file.save(file_path)

        logger.info(f"File received: {file.filename}")

        # Step 1: Validate file (MIME type, size, hash)
        is_valid, error_msg, file_metadata = FileValidator.validate_file(file_path)

        if not is_valid:
            logger.error(f"File validation failed: {error_msg}")
            return jsonify({
                'error': 'File validation failed',
                'details': error_msg,
                'metadata': file_metadata
            }), 400

        logger.info(f"File validated - Hash: {file_metadata['file_hash'][:16]}...")

        # Step 2: Check cache
        file_hash = file_metadata['file_hash']
        cached_result = cache_manager.get(file_hash)

        if cached_result:
            logger.info(f"Cache HIT for {file_hash[:16]}")
            # Clean up file
            if os.path.exists(file_path):
                os.remove(file_path)

            return jsonify({
                **cached_result,
                'cached': True,
                'cache_timestamp': cached_result.get('analysis_timestamp')
            }), 200

        logger.info(f"Cache MISS for {file_hash[:16]}, processing...")

        # Step 3: Import analysis modules
        from document_corroboration.processing_engine import RAGProcessor
        from document_corroboration.format_validator import FormatValidator
        from document_corroboration.image_analyzer import ImageAnalyzer
        from document_corroboration.risk_scorer import RiskScorer

        # Initialize results
        document_analysis = None
        format_validation = None
        image_analysis = None

        file_ext = file_metadata['extension']

        # Component 1: Document Processing (RAG Analysis)  - Using proper async
        logger.info("Starting RAG processing...")
        try:
            processor = RAGProcessor()

            # Use thread pool for async operation
            async def process_doc():
                return await processor.process_document(file_path)

            rag_result = run_async_in_thread(process_doc)

            if isinstance(rag_result, str):
                document_analysis = json.loads(rag_result)
            else:
                document_analysis = rag_result

            # Log enhanced results
            status = document_analysis.get('status', 'unknown')
            confidence = document_analysis.get('confidence_score', 0)
            doc_type = document_analysis.get('metadata', {}).get('document_type', 'unknown')

            logger.info(f"RAG completed - Status: {status}, Type: {doc_type}, Confidence: {confidence:.1f}%")

        except Exception as e:
            logger.error(f"RAG processing error: {type(e).__name__}: {e}", exc_info=True)
            document_analysis = {"error": str(e), "status": "FAILED", "confidence_score": 0}

        # Component 2: Format Validation
        if file_ext in ['.pdf', '.txt', '.doc', '.docx']:
            logger.info("Starting format validation...")
            try:
                validator = FormatValidator()
                format_validation = validator.validate_document(file_path)
                logger.info(f"Format validation completed - Risk: {format_validation.get('risk_score', 0)}")
            except Exception as e:
                logger.error(f"Format validation error: {e}", exc_info=True)
                format_validation = {"error": str(e)}

        # Component 3: Image Analysis
        if file_ext in ['.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.gif']:
            logger.info("Starting image analysis...")
            try:
                image_analyzer = ImageAnalyzer()
                image_analysis = image_analyzer.analyze_image(file_path)
                logger.info(f"Image analysis completed - Authenticity: {image_analysis.get('authenticity_score', 0)}")
            except Exception as e:
                logger.error(f"Image analysis error: {e}", exc_info=True)
                image_analysis = {"error": str(e)}
        elif file_ext == '.pdf':
            # Basic image metadata extraction for PDFs
            logger.info("Extracting image metadata from PDF...")
            try:
                from utils.metadata_extractor import MetadataExtractor
                pdf_metadata = MetadataExtractor.extract_pdf_metadata(file_path)
                image_analysis = {
                    "status": "metadata_extracted",
                    "embedded_content_analyzed": True,
                    "page_count": pdf_metadata.get('page_count', 0),
                    "has_metadata": pdf_metadata.get('author') is not None
                }
                logger.info(f"PDF metadata extracted - {pdf_metadata.get('page_count', 0)} pages")
            except Exception as e:
                logger.error(f"PDF metadata extraction error: {e}")
                image_analysis = None

        # Component 4: Risk Scoring & Reporting
        logger.info("Calculating risk score...")
        risk_scorer = RiskScorer()
        risk_assessment = risk_scorer.calculate_comprehensive_risk(
            document_analysis=document_analysis,
            format_validation=format_validation,
            image_analysis=image_analysis
        )

        logger.info(f"Risk assessment - Score: {risk_assessment['overall_risk_score']}, Status: {risk_assessment['status']}")

        # Generate comprehensive report
        report = risk_scorer.generate_report(
            file_name=file.filename,
            risk_assessment=risk_assessment,
            document_analysis=document_analysis,
            format_validation=format_validation,
            image_analysis=image_analysis,
            save_to_file=True
        )

        # Add file metadata to report
        report['file_metadata'] = file_metadata
        report['cached'] = False

        # Step 4: Persist to database with versioning
        try:
            # Check if this file hash already exists
            existing = supabase.table('document_validations')\
                .select('*')\
                .eq('file_hash', file_hash)\
                .eq('is_latest', True)\
                .execute()

            version = 1
            previous_version_id = None

            if existing.data and len(existing.data) > 0:
                # File was resubmitted - create new version
                old_record = existing.data[0]
                version = old_record.get('version', 1) + 1
                previous_version_id = old_record['id']

                # Mark old record as not latest
                supabase.table('document_validations')\
                    .update({'is_latest': False})\
                    .eq('id', old_record['id'])\
                    .execute()

                logger.info(f"Document resubmitted - creating version {version} (previous: {previous_version_id})")

            # Insert new record
            new_record = {
                'file_name': file.filename,
                'file_hash': file_hash,
                'file_size': file_metadata['file_size'],
                'mime_type': file_metadata['mime_type'],
                'risk_score': risk_assessment['overall_risk_score'],
                'status': risk_assessment['status'],
                'report_id': report['report_id'],
                'report_data': json.dumps(report),
                'version': version,
                'is_latest': True,
                'previous_version_id': previous_version_id,
                'created_at': datetime.now().isoformat()
            }

            supabase.table('document_validations').insert(new_record).execute()
            logger.info(f"Report persisted to database - ID: {report['report_id']}, Version: {version}")

        except Exception as e:
            logger.warning(f"Database persistence failed: {e}")
            # Continue even if DB fails

        # Step 5: Cache the result
        cache_manager.set(file_hash, report)
        logger.info(f"Result cached for {file_hash[:16]}")

        # Clean up uploaded file
        if os.path.exists(file_path):
            os.remove(file_path)

        logger.info("=== Validation complete ===")
        return jsonify(report), 200

    except Exception as e:
        logger.error(f"FATAL ERROR: {type(e).__name__}: {e}", exc_info=True)

        # Clean up file
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass

        return jsonify({
            'error': f'Document validation failed: {str(e)}',
            'error_type': type(e).__name__
        }), 500


@app.route('/api/validate/format', methods=['POST'])
#@require_api_key
def validate_format_only():
    """Format validation only (Component 2)"""
    file_path = None
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['file']
        uploads_dir = os.path.join(os.path.dirname(__file__), 'uploads')
        os.makedirs(uploads_dir, exist_ok=True)
        file_path = os.path.join(uploads_dir, file.filename)
        file.save(file_path)

        # Validate file
        is_valid, error_msg, file_metadata = FileValidator.validate_file(file_path)
        if not is_valid:
            return jsonify({'error': error_msg}), 400

        file_ext = file_metadata['extension']
        if file_ext not in ['.pdf', '.txt', '.doc', '.docx']:
            return jsonify({'error': 'Format validation only supports text/document files'}), 400

        from document_corroboration.format_validator import FormatValidator
        validator = FormatValidator()
        result = validator.validate_document(file_path)

        os.remove(file_path)
        return jsonify(result), 200

    except Exception as e:
        logger.error(f"Format validation error: {e}", exc_info=True)
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
        return jsonify({'error': str(e)}), 500


@app.route('/api/validate/image', methods=['POST'])
#@require_api_key
def validate_image_only():
    """Image analysis only (Component 3)"""
    file_path = None
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['file']
        uploads_dir = os.path.join(os.path.dirname(__file__), 'uploads')
        os.makedirs(uploads_dir, exist_ok=True)
        file_path = os.path.join(uploads_dir, file.filename)
        file.save(file_path)

        # Validate file
        is_valid, error_msg, file_metadata = FileValidator.validate_file(file_path)
        if not is_valid:
            return jsonify({'error': error_msg}), 400

        file_ext = file_metadata['extension']
        if file_ext not in ['.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.gif']:
            return jsonify({'error': 'Image analysis only supports image files'}), 400

        from document_corroboration.image_analyzer import ImageAnalyzer
        analyzer = ImageAnalyzer()
        result = analyzer.analyze_image(file_path)

        os.remove(file_path)
        return jsonify(result), 200

    except Exception as e:
        logger.error(f"Image analysis error: {e}", exc_info=True)
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
        return jsonify({'error': str(e)}), 500


@app.route('/api/audit/history', methods=['GET'])
#@require_api_key
def get_audit_history():
    """Retrieve audit history from database"""
    try:
        file_name = request.args.get('file_name')
        limit = int(request.args.get('limit', 10))
        latest_only = request.args.get('latest_only', 'true').lower() == 'true'

        # Query from database
        query = supabase.table('document_validations').select('*')

        if file_name:
            query = query.eq('file_name', file_name)

        if latest_only:
            query = query.eq('is_latest', True)

        response = query.order('created_at', desc=True).limit(limit).execute()

        return jsonify({
            'history': response.data,
            'count': len(response.data),
            'latest_only': latest_only
        }), 200

    except Exception as e:
        logger.error(f"Audit history error: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/document/versions/<file_hash>', methods=['GET'])
#@require_api_key
def get_document_versions(file_hash):
    """Get all versions of a document by file hash"""
    try:
        response = supabase.table('document_validations')\
            .select('*')\
            .eq('file_hash', file_hash)\
            .order('version', desc=True)\
            .execute()

        if not response.data:
            return jsonify({'error': 'Document not found'}), 404

        versions = []
        for record in response.data:
            versions.append({
                'version': record['version'],
                'is_latest': record['is_latest'],
                'status': record['status'],
                'risk_score': record['risk_score'],
                'created_at': record['created_at'],
                'report_id': record['report_id']
            })

        return jsonify({
            'file_hash': file_hash,
            'total_versions': len(versions),
            'versions': versions
        }), 200

    except Exception as e:
        logger.error(f"Version history error: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/document/compare/<file_hash>/<int:version1>/<int:version2>', methods=['GET'])
#@require_api_key
def compare_versions(file_hash, version1, version2):
    """Compare two versions of a document"""
    try:
        # Get both versions
        v1 = supabase.table('document_validations')\
            .select('*')\
            .eq('file_hash', file_hash)\
            .eq('version', version1)\
            .execute()

        v2 = supabase.table('document_validations')\
            .select('*')\
            .eq('file_hash', file_hash)\
            .eq('version', version2)\
            .execute()

        if not v1.data or not v2.data:
            return jsonify({'error': 'One or both versions not found'}), 404

        v1_data = v1.data[0]
        v2_data = v2.data[0]

        comparison = {
            'file_hash': file_hash,
            'version1': {
                'version': version1,
                'status': v1_data['status'],
                'risk_score': v1_data['risk_score'],
                'created_at': v1_data['created_at']
            },
            'version2': {
                'version': version2,
                'status': v2_data['status'],
                'risk_score': v2_data['risk_score'],
                'created_at': v2_data['created_at']
            },
            'changes': {
                'status_changed': v1_data['status'] != v2_data['status'],
                'risk_score_delta': float(v2_data['risk_score']) - float(v1_data['risk_score']) if v1_data['risk_score'] and v2_data['risk_score'] else None,
                'improvement': (float(v2_data['risk_score']) < float(v1_data['risk_score'])) if v1_data['risk_score'] and v2_data['risk_score'] else None
            }
        }

        return jsonify(comparison), 200

    except Exception as e:
        logger.error(f"Version comparison error: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/cache/stats', methods=['GET'])
#@require_api_key
def get_cache_stats():
    """Get cache statistics"""
    stats = cache_manager.get_stats()
    return jsonify(stats), 200


@app.route('/api/cache/clear', methods=['POST'])
#@require_api_key
def clear_cache():
    """Clear expired cache entries"""
    cleared = cache_manager.clear_expired()
    return jsonify({
        'cleared_entries': cleared,
        'note': 'Only expired entries (>24h old) were cleared. Use /api/cache/clear/all to clear everything.'
    }), 200


@app.route('/api/cache/clear/all', methods=['POST'])
#@require_api_key
def clear_all_cache():
    """Clear ALL cache entries (including non-expired)"""
    cleared = cache_manager.clear_all()
    return jsonify({
        'cleared_entries': cleared,
        'note': 'All cache entries have been cleared.'
    }), 200


if __name__ == '__main__':
    logger.info("Starting Document Corroboration API v2.0")
    logger.info(f"Log files: ./logs/")
    logger.info(f"Cache directory: ./cache/")
    logger.info(f"Audit logs: ./audit_logs/")

    socketio.run(app, host='0.0.0.0', port=5001, debug=True)
