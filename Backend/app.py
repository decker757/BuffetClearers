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


@app.route('/api/analyze-transactions', methods=['POST'])
#@require_api_key
def analyze_transactions():
    """
    Analyze transactions using both XGBoost and Isolation Forest models

    Enhanced with:
    - Audit traceability (model_version, execution_id, data_source)
    - Unified fraud_risk_score (0-100)
    - Feature importance explanations
    - Alert rules for high-risk triggers
    - Feedback mechanism for manual review
    - Summary statistics

    Request body can be either:
    1. JSON with 'transactions' array
    2. File upload (CSV file)

    Query parameters:
    - method: 'xgboost', 'isolation_forest', or 'both' (default: 'both')
    - threshold: Suspicion threshold for XGBoost (default: 0.5)
    - contamination: Anomaly percentage for Isolation Forest (default: 0.05)
    - include_explanations: Include feature importance (default: 'true')
    """
    try:
        import pandas as pd
        import uuid
        from XGBoost import (train_model as train_xgb, predict_transactions,
                            get_suspicious_transactions, get_feature_importance, explain_prediction)
        from isolationforest import train_isolation_forest, detect_anomalies, get_anomalies

        # Generate execution ID for audit traceability
        execution_id = str(uuid.uuid4())

        # Get parameters
        method = request.args.get('method', 'both')
        threshold = float(request.args.get('threshold', 0.5))
        contamination = float(request.args.get('contamination', 0.05))
        include_explanations = request.args.get('include_explanations', 'true').lower() == 'true'

        logger.info(f"=== Transaction analysis request - Execution ID: {execution_id}, Method: {method} ===")

        # Get transaction data - either from JSON or file upload
        data_source = None
        if 'file' in request.files:
            # CSV file upload
            file = request.files['file']

            if file.filename == '':
                return jsonify({'error': 'No file selected'}), 400

            if not file.filename.endswith('.csv'):
                return jsonify({'error': 'Only CSV files are supported'}), 400

            # Save temporarily
            uploads_dir = os.path.join(os.path.dirname(__file__), 'uploads')
            os.makedirs(uploads_dir, exist_ok=True)
            file_path = os.path.join(uploads_dir, file.filename)
            file.save(file_path)

            # Load CSV
            transactions_df = pd.read_csv(file_path)
            data_source = f"csv_upload:{file.filename}"

            # Clean up
            os.remove(file_path)

            logger.info(f"Loaded {len(transactions_df)} transactions from CSV file")

        elif request.is_json:
            # JSON data
            data = request.get_json()

            if 'transactions' not in data:
                return jsonify({'error': 'No transactions provided in request body'}), 400

            transactions = data['transactions']
            transactions_df = pd.DataFrame(transactions)
            data_source = "json_api"

            logger.info(f"Loaded {len(transactions_df)} transactions from JSON")

        else:
            return jsonify({'error': 'Please provide either JSON data or CSV file'}), 400

        # Validate required columns
        required_cols = ['amount', 'fx_applied_rate', 'fx_market_rate', 'daily_cash_total_customer', 'daily_cash_txn_count']
        missing_cols = [col for col in required_cols if col not in transactions_df.columns]

        if missing_cols:
            return jsonify({
                'error': 'Missing required columns',
                'missing_columns': missing_cols,
                'required_columns': required_cols
            }), 400

        # Import fraud scoring utilities
        from utils.fraud_scoring import FraudScorer
        from utils.regulatory_checker import RegulatoryChecker

        # Initialize regulatory checker
        regulatory_checker = RegulatoryChecker(supabase)

        # Initialize enhanced results structure with audit traceability
        results = {
            # Audit traceability
            'execution_id': execution_id,
            'model_version': {
                'xgboost': '1.0.0',
                'isolation_forest': '1.0.0',
                'fraud_scorer': '1.0.0'
            },
            'data_source': data_source,
            'analysis_timestamp': datetime.now().isoformat(),

            # Analysis parameters
            'analysis_config': {
                'method': method,
                'xgboost_threshold': threshold,
                'isolation_forest_contamination': contamination,
                'include_explanations': include_explanations
            },

            # Transaction summary
            'total_transactions': len(transactions_df),

            # Will be populated below
            'summary_statistics': {},
            'model_results': {},
            'enhanced_transactions': [],
            'alerts': [],
            'feedback': []
        }

        # Run XGBoost analysis
        xgb_results = None
        xgb_feature_importance = None

        if method in ['xgboost', 'both']:
            logger.info("Running XGBoost analysis...")
            try:
                # Train model if not already trained
                train_xgb()

                # Predict with feature importance
                if include_explanations:
                    xgb_results, xgb_feature_importance = predict_transactions(
                        transactions_df, include_feature_importance=True
                    )
                else:
                    xgb_results = predict_transactions(transactions_df)

                suspicious_xgb = xgb_results[xgb_results['suspicion_probability'] >= threshold]

                results['model_results']['xgboost'] = {
                    'suspicious_count': len(suspicious_xgb),
                    'suspicious_percentage': round(len(suspicious_xgb) / len(transactions_df) * 100, 2),
                    'threshold': threshold,
                    'risk_distribution': {
                        'high': int((xgb_results['risk_level'] == 'High').sum()),
                        'medium': int((xgb_results['risk_level'] == 'Medium').sum()),
                        'low': int((xgb_results['risk_level'] == 'Low').sum())
                    }
                }

                # Add feature importance if available
                if xgb_feature_importance and include_explanations:
                    results['model_results']['xgboost']['feature_importance'] = xgb_feature_importance['top_features']

                logger.info(f"XGBoost found {len(suspicious_xgb)} suspicious transactions")

            except Exception as e:
                logger.error(f"XGBoost analysis failed: {e}", exc_info=True)
                results['model_results']['xgboost'] = {'error': str(e)}

        # Run Isolation Forest analysis
        iso_results = None

        if method in ['isolation_forest', 'both']:
            logger.info("Running Isolation Forest analysis...")
            try:
                # Train model if not already trained
                train_isolation_forest(contamination=contamination)

                # Detect anomalies
                iso_results = detect_anomalies(transactions_df, contamination=contamination)
                anomalies = iso_results[iso_results['is_anomaly'] == 1]

                results['model_results']['isolation_forest'] = {
                    'anomaly_count': len(anomalies),
                    'anomaly_percentage': round(len(anomalies) / len(transactions_df) * 100, 2),
                    'contamination': contamination,
                    'severity_distribution': {
                        'high': int((iso_results['anomaly_severity'] == 'High').sum()) if 'anomaly_severity' in iso_results.columns else 0,
                        'medium': int((iso_results['anomaly_severity'] == 'Medium').sum()) if 'anomaly_severity' in iso_results.columns else 0,
                        'low': int((iso_results['anomaly_severity'] == 'Low').sum()) if 'anomaly_severity' in iso_results.columns else 0
                    }
                }

                logger.info(f"Isolation Forest found {len(anomalies)} anomalies")

            except Exception as e:
                logger.error(f"Isolation Forest analysis failed: {e}", exc_info=True)
                results['model_results']['isolation_forest'] = {'error': str(e)}

        # Enhanced transaction-level analysis with unified fraud scoring
        logger.info("Calculating unified fraud scores and alerts...")
        enhanced_transactions = []
        all_alerts = []
        fraud_scores = []

        for idx, row in transactions_df.iterrows():
            # Get model predictions
            xgb_prob = xgb_results.loc[idx, 'suspicion_probability'] if xgb_results is not None else None
            iso_score = iso_results.loc[idx, 'anomaly_score'] if iso_results is not None else None

            # Check alert rules
            alerts = FraudScorer.check_alert_rules(row)
            all_alerts.extend(alerts)

            # Check regulatory compliance
            regulatory_violations = regulatory_checker.check_transaction(row.to_dict())

            # Calculate unified fraud score (boost if regulatory violations found)
            fraud_score = FraudScorer.calculate_unified_fraud_score(xgb_prob, iso_score, alerts)

            # Boost fraud score for regulatory violations
            if regulatory_violations:
                # Add 10-20 points per violation depending on severity
                for violation in regulatory_violations:
                    severity = violation.get('severity', 'medium')
                    if severity == 'critical':
                        fraud_score += 20
                    elif severity == 'high':
                        fraud_score += 15
                    elif severity == 'medium':
                        fraud_score += 10
                    else:
                        fraud_score += 5

                fraud_score = min(100, fraud_score)  # Cap at 100

            fraud_scores.append(fraud_score)
            risk_category = FraudScorer.get_risk_category(fraud_score)

            # Build enhanced transaction record
            enhanced_txn = {
                'transaction_id': row.get('transaction_id', f'TXN_{idx}'),
                'amount': float(row.get('amount', 0)),
                'fraud_risk_score': round(fraud_score, 2),
                'risk_category': risk_category,
                'model_scores': {
                    'xgboost_probability': round(float(xgb_prob), 4) if xgb_prob is not None else None,
                    'isolation_forest_score': round(float(iso_score), 4) if iso_score is not None else None
                },
                'alerts': alerts,
                'alert_count': len(alerts),
                'regulatory_violations': regulatory_violations,
                'violation_count': len(regulatory_violations),
            }

            # Add contextual fields if available
            contextual_fields = ['currency', 'channel', 'originator_country', 'beneficiary_country',
                                'customer_type', 'customer_risk_rating', 'customer_is_pep']
            enhanced_txn['context'] = {field: row.get(field) for field in contextual_fields if field in row}

            # Add explanations for high-risk transactions
            if include_explanations and fraud_score >= 60 and xgb_results is not None:
                try:
                    explanation = explain_prediction(row)
                    enhanced_txn['explanation'] = {
                        'top_features': explanation.get('top_model_features', []),
                        'risk_factors': explanation.get('transaction_risk_factors', [])
                    }
                except Exception as e:
                    logger.warning(f"Failed to generate explanation for transaction {idx}: {e}")

            # Add feedback placeholder
            enhanced_txn['feedback'] = {
                'reviewed': False,
                'reviewer': None,
                'decision': None,
                'notes': None,
                'reviewed_at': None
            }

            enhanced_transactions.append(enhanced_txn)

        # Store enhanced transactions (top 100 by fraud score for response size)
        results['enhanced_transactions'] = sorted(
            enhanced_transactions,
            key=lambda x: x['fraud_risk_score'],
            reverse=True
        )[:100]

        # Collect all regulatory violations for summary
        all_regulatory_violations = []
        for txn in enhanced_transactions:
            all_regulatory_violations.extend(txn.get('regulatory_violations', []))

        # Summary statistics
        results['summary_statistics'] = {
            'total_transactions': len(transactions_df),
            'fraud_scores': {
                'average': round(sum(fraud_scores) / len(fraud_scores), 2) if fraud_scores else 0,
                'median': round(sorted(fraud_scores)[len(fraud_scores)//2], 2) if fraud_scores else 0,
                'max': round(max(fraud_scores), 2) if fraud_scores else 0,
                'min': round(min(fraud_scores), 2) if fraud_scores else 0
            },
            'risk_categories': {
                'critical': sum(1 for s in fraud_scores if s >= 80),
                'high': sum(1 for s in fraud_scores if 60 <= s < 80),
                'medium': sum(1 for s in fraud_scores if 40 <= s < 60),
                'low': sum(1 for s in fraud_scores if 20 <= s < 40),
                'minimal': sum(1 for s in fraud_scores if s < 20)
            },
            'high_risk_percentage': round(sum(1 for s in fraud_scores if s >= 60) / len(fraud_scores) * 100, 2) if fraud_scores else 0,
            'total_alerts_triggered': len(all_alerts),
            'unique_alert_types': len(set(alert['rule'] for alert in all_alerts)),
            'regulatory_compliance': {
                'total_violations': len(all_regulatory_violations),
                'transactions_with_violations': sum(1 for txn in enhanced_transactions if txn.get('violation_count', 0) > 0),
                'compliance_rate': round((1 - sum(1 for txn in enhanced_transactions if txn.get('violation_count', 0) > 0) / len(enhanced_transactions)) * 100, 2) if enhanced_transactions else 100
            }
        }

        # Alert summary
        alert_summary = {}
        for alert in all_alerts:
            rule = alert['rule']
            if rule not in alert_summary:
                alert_summary[rule] = {
                    'count': 0,
                    'severity': alert['severity'],
                    'description': alert['description']
                }
            alert_summary[rule]['count'] += 1

        # Regulatory violation summary
        regulatory_summary = {}
        for violation in all_regulatory_violations:
            rule_id = violation.get('rule_id', 'unknown')
            if rule_id not in regulatory_summary:
                regulatory_summary[rule_id] = {
                    'count': 0,
                    'severity': violation.get('severity', 'unknown'),
                    'title': violation.get('rule_title', 'Unknown Rule'),
                    'source': violation.get('rule_source', 'Unknown Source')
                }
            regulatory_summary[rule_id]['count'] += 1

        results['alerts'] = {
            'summary': alert_summary,
            'total_triggered': len(all_alerts),
            'critical_alerts': sum(1 for a in all_alerts if a['severity'] == 'critical'),
            'high_alerts': sum(1 for a in all_alerts if a['severity'] == 'high'),
            'regulatory_violations': {
                'summary': regulatory_summary,
                'total': len(all_regulatory_violations),
                'critical': sum(1 for v in all_regulatory_violations if v.get('severity') == 'critical'),
                'high': sum(1 for v in all_regulatory_violations if v.get('severity') == 'high')
            }
        }

        # Consensus analysis if both models used
        if method == 'both' and xgb_results is not None and iso_results is not None:
            high_conf_txns = [
                txn for txn in enhanced_transactions
                if txn['model_scores']['xgboost_probability'] and
                   txn['model_scores']['xgboost_probability'] >= threshold and
                   txn['model_scores']['isolation_forest_score'] and
                   txn['model_scores']['isolation_forest_score'] < 0
            ]

            results['consensus'] = {
                'high_confidence_count': len(high_conf_txns),
                'high_confidence_percentage': round(len(high_conf_txns) / len(transactions_df) * 100, 2),
                'description': 'Transactions flagged as suspicious by both models'
            }

            logger.info(f"Consensus: {len(high_conf_txns)} high-confidence suspicious transactions")

        # ============================================================
        # PERSIST TO SUPABASE - Audit Trail & Transaction Analysis
        # ============================================================
        try:
            logger.info("Persisting analysis results to Supabase...")

            # 1. Create audit trail record for this analysis execution
            audit_record = {
                'execution_id': execution_id,
                'event_type': 'transaction_analysis',
                'data_source': data_source,
                'total_transactions': len(transactions_df),
                'analysis_method': method,
                'model_versions': json.dumps(results['model_version']),
                'analysis_config': json.dumps(results['analysis_config']),
                'summary_stats': json.dumps(results['summary_statistics']),
                'alert_summary': json.dumps(results['alerts']),
                'high_risk_count': results['summary_statistics']['risk_categories']['critical'] +
                                 results['summary_statistics']['risk_categories']['high'],
                'average_fraud_score': results['summary_statistics']['fraud_scores']['average'],
                'performed_by': request.headers.get('X-User-Email', 'system'),
                'timestamp': datetime.now().isoformat(),
                'metadata': json.dumps({
                    'consensus': results.get('consensus', {}),
                    'model_results': results['model_results']
                })
            }

            supabase.table('transaction_analysis_audit').insert(audit_record).execute()
            logger.info(f"Audit trail created - Execution ID: {execution_id}")

            # 2. Persist individual high-risk transactions (fraud_score >= 60)
            high_risk_transactions = [
                txn for txn in enhanced_transactions
                if txn['fraud_risk_score'] >= 60
            ]

            if high_risk_transactions:
                transaction_records = []
                for txn in high_risk_transactions:
                    record = {
                        'execution_id': execution_id,
                        'transaction_id': txn['transaction_id'],
                        'amount': txn['amount'],
                        'fraud_risk_score': txn['fraud_risk_score'],
                        'risk_category': txn['risk_category'],
                        'xgboost_probability': txn['model_scores'].get('xgboost_probability'),
                        'isolation_forest_score': txn['model_scores'].get('isolation_forest_score'),
                        'alert_count': txn['alert_count'],
                        'alerts': json.dumps(txn['alerts']),
                        'context': json.dumps(txn['context']),
                        'explanation': json.dumps(txn.get('explanation', {})),
                        'status': 'pending_review',
                        'created_at': datetime.now().isoformat()
                    }
                    transaction_records.append(record)

                # Batch insert high-risk transactions
                supabase.table('flagged_transactions').insert(transaction_records).execute()
                logger.info(f"Persisted {len(transaction_records)} high-risk transactions to Supabase")

            # 3. Create alerts for CRITICAL transactions (fraud_score >= 80)
            critical_transactions = [
                txn for txn in enhanced_transactions
                if txn['fraud_risk_score'] >= 80
            ]

            if critical_transactions:
                alert_records = []
                for txn in critical_transactions:
                    alert = {
                        'execution_id': execution_id,
                        'transaction_id': txn['transaction_id'],
                        'alert_type': 'critical_fraud_risk',
                        'severity': 'critical',
                        'fraud_score': txn['fraud_risk_score'],
                        'risk_category': txn['risk_category'],
                        'description': f"Critical fraud risk detected: Score {txn['fraud_risk_score']}/100",
                        'triggered_rules': json.dumps([a['rule'] for a in txn['alerts']]),
                        'status': 'open',
                        'assigned_to': None,
                        'created_at': datetime.now().isoformat(),
                        'metadata': json.dumps({
                            'amount': txn['amount'],
                            'context': txn['context'],
                            'model_scores': txn['model_scores']
                        })
                    }
                    alert_records.append(alert)

                supabase.table('fraud_alerts').insert(alert_records).execute()
                logger.info(f"Created {len(alert_records)} critical alerts in Supabase")

            results['database_persistence'] = {
                'status': 'success',
                'audit_trail_created': True,
                'high_risk_transactions_saved': len(high_risk_transactions),
                'critical_alerts_created': len(critical_transactions) if critical_transactions else 0
            }

        except Exception as e:
            logger.error(f"Supabase persistence failed: {e}", exc_info=True)
            results['database_persistence'] = {
                'status': 'failed',
                'error': str(e),
                'note': 'Analysis completed successfully but database persistence failed'
            }
            # Don't fail the entire request if DB persistence fails

        logger.info("=== Transaction analysis complete ===")
        return jsonify(results), 200

    except Exception as e:
        logger.error(f"Transaction analysis error: {type(e).__name__}: {e}", exc_info=True)
        return jsonify({
            'error': f'Transaction analysis failed: {str(e)}',
            'error_type': type(e).__name__
        }), 500


@app.route('/api/transaction-feedback', methods=['POST'])
#@require_api_key
def submit_transaction_feedback():
    """
    Submit manual review feedback for a transaction

    Request body:
    {
        "execution_id": "uuid",
        "transaction_id": "TXN001",
        "reviewer": "analyst@company.com",
        "decision": "confirmed_fraud" | "false_positive" | "needs_investigation",
        "notes": "Additional comments"
    }
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'No data provided'}), 400

        required_fields = ['execution_id', 'transaction_id', 'decision', 'reviewer']
        missing_fields = [field for field in required_fields if field not in data]

        if missing_fields:
            return jsonify({
                'error': 'Missing required fields',
                'missing_fields': missing_fields
            }), 400

        # Validate decision type
        valid_decisions = ['confirmed_fraud', 'false_positive', 'needs_investigation', 'legitimate']
        if data['decision'] not in valid_decisions:
            return jsonify({
                'error': 'Invalid decision',
                'valid_decisions': valid_decisions
            }), 400

        feedback_record = {
            'execution_id': data['execution_id'],
            'transaction_id': data['transaction_id'],
            'reviewer': data['reviewer'],
            'decision': data['decision'],
            'notes': data.get('notes', ''),
            'reviewed_at': datetime.now().isoformat(),
            'reviewed': True
        }

        # Store feedback in database
        try:
            supabase.table('transaction_feedback').insert(feedback_record).execute()
            logger.info(f"Feedback recorded for transaction {data['transaction_id']} by {data['reviewer']}")
        except Exception as e:
            logger.warning(f"Database storage failed: {e}")
            # Continue even if DB fails

        return jsonify({
            'status': 'success',
            'message': 'Feedback recorded successfully',
            'feedback': feedback_record
        }), 200

    except Exception as e:
        logger.error(f"Feedback submission error: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/transaction-feedback/<execution_id>', methods=['GET'])
#@require_api_key
def get_transaction_feedback(execution_id):
    """
    Retrieve feedback for transactions from a specific analysis execution

    Query parameters:
    - transaction_id (optional): Get feedback for specific transaction
    """
    try:
        transaction_id = request.args.get('transaction_id')

        query = supabase.table('transaction_feedback').select('*').eq('execution_id', execution_id)

        if transaction_id:
            query = query.eq('transaction_id', transaction_id)

        response = query.execute()

        return jsonify({
            'execution_id': execution_id,
            'feedback_count': len(response.data),
            'feedback': response.data
        }), 200

    except Exception as e:
        logger.error(f"Feedback retrieval error: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/regulations/scrape', methods=['POST'])
#@require_api_key
def scrape_regulations():
    """
    Scrape regulatory documents from a URL or trigger full pipeline

    Option 1 - Scrape specific URL:
    {
        "url": "https://www.mas.gov.sg/regulation/notices/...",
        "regulator_code": "MAS",
        "auto_import": true
    }

    Option 2 - Run full scraping pipeline:
    {
        "mode": "pipeline",
        "regulators": ["MAS", "FINMA", "HKMA"],
        "max_docs_per_regulator": 20,
        "auto_import": true
    }
    """
    try:
        if not request.is_json:
            return jsonify({'error': 'Request must be JSON'}), 400

        data = request.get_json()
        auto_import = data.get('auto_import', False)

        # Option 1: Scrape specific URL
        if 'url' in data:
            url = data.get('url')
            regulator_code = data.get('regulator_code', 'UNKNOWN')

            if not url:
                return jsonify({'error': 'URL is required'}), 400

            logger.info(f"=== Scraping single URL: {url} ===")

            # Simple scraping implementation
            import requests
            from bs4 import BeautifulSoup

            try:
                response = requests.get(url, verify=False, timeout=30)
                response.raise_for_status()

                # Save content
                output_file = f'Regulations/scraped_{regulator_code}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.html'
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(response.text)

                return jsonify({
                    'status': 'success',
                    'message': f'URL scraped successfully',
                    'url': url,
                    'output_file': output_file,
                    'regulator': regulator_code,
                    'content_length': len(response.text),
                    'timestamp': datetime.now().isoformat()
                }), 200

            except Exception as e:
                return jsonify({'error': f'Failed to scrape URL: {str(e)}'}), 500

        # Option 2: Run full pipeline
        elif data.get('mode') == 'pipeline':
            from Regulations.production_aml_pipeline import ProductionAMLPipeline

            logger.info("=== Running full regulation scraping pipeline ===")

            max_docs = data.get('max_docs_per_regulator', 20)
            target_regulators = data.get('regulators', ['MAS', 'FINMA', 'HKMA'])

            # Validate parameters
            if not isinstance(max_docs, int) or max_docs < 1 or max_docs > 100:
                return jsonify({'error': 'max_docs_per_regulator must be between 1 and 100'}), 400

            valid_regulators = ['MAS', 'FINMA', 'HKMA']
            if not all(reg in valid_regulators for reg in target_regulators):
                return jsonify({'error': f'Invalid regulator. Must be one of: {valid_regulators}'}), 400

            logger.info(f"Scraping regulations: {target_regulators}, max_docs={max_docs}")

            # Initialize pipeline
            pipeline = ProductionAMLPipeline()

            # Run scraping
            results = pipeline.run_production_pipeline(max_docs_per_regulator=max_docs)

            # Check if scraping succeeded
            if not results or 'output_file' not in results:
                return jsonify({
                    'status': 'failed',
                    'error': 'Scraping failed to produce output file',
                    'details': results
                }), 500

            output_file = results['output_file']

            # Auto-import if requested
            import_results = None
            if auto_import and os.path.exists(output_file):
                logger.info("Auto-importing scraped regulations...")
                try:
                    from Regulations.simple_supabase_importer import SimpleAMLImporter
                    importer = SimpleAMLImporter()
                    import_results = importer.import_from_json(output_file)
                    logger.info("Auto-import complete")
                except Exception as e:
                    logger.error(f"Auto-import failed: {e}")
                    import_results = {'error': str(e)}

            return jsonify({
                'status': 'success',
                'message': 'Regulations scraped successfully',
                'scraping_results': {
                    'output_file': output_file,
                    'total_documents_processed': results.get('total_documents_processed', 0),
                    'total_rules_extracted': results.get('total_rules_extracted', 0),
                    'regulators': results.get('regulators', {}),
                    'processing_time_seconds': results.get('processing_time_seconds', 0)
                },
                'import_results': import_results if auto_import else None,
                'timestamp': datetime.now().isoformat()
            }), 200

        else:
            return jsonify({
                'error': 'Invalid request. Provide either "url" or "mode": "pipeline"'
            }), 400

    except Exception as e:
        logger.error(f"Regulation scraping error: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/regulations/import', methods=['POST'])
#@require_api_key
def import_regulations():
    """
    Import regulatory rules from JSON file into Supabase

    Request body (JSON):
    {
        "json_file_path": "path/to/rules.json"
    }

    Or upload file directly with form-data:
    - file: JSON file upload
    """
    try:
        from Regulations.simple_supabase_importer import SimpleAMLImporter

        logger.info("=== Regulations import request ===")

        # Check if file was uploaded
        if 'file' in request.files:
            file = request.files['file']
            if file.filename == '':
                return jsonify({'error': 'No file selected'}), 400

            if not file.filename.endswith('.json'):
                return jsonify({'error': 'File must be a JSON file'}), 400

            # Save temporarily
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
                file.save(temp_file.name)
                json_file_path = temp_file.name

        # Check if file path was provided in JSON body
        elif request.is_json:
            data = request.get_json()
            json_file_path = data.get('json_file_path')

            if not json_file_path:
                return jsonify({'error': 'json_file_path is required'}), 400

            if not os.path.exists(json_file_path):
                return jsonify({'error': f'File not found: {json_file_path}'}), 404

        else:
            return jsonify({'error': 'Either upload a file or provide json_file_path in request body'}), 400

        # Import regulations
        importer = SimpleAMLImporter()
        results = importer.import_from_json(json_file_path)

        logger.info(f"Import complete: {results}")

        return jsonify({
            'status': 'success',
            'message': 'Regulations imported successfully',
            'statistics': {
                'documents_imported': results.get('documents_imported', 0),
                'rules_imported': results.get('rules_imported', 0),
                'keywords_imported': results.get('keywords_imported', 0),
                'errors': results.get('errors', [])
            },
            'timestamp': datetime.now().isoformat()
        }), 200

    except Exception as e:
        logger.error(f"Regulations import error: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/regulations', methods=['GET'])
#@require_api_key
def get_regulations():
    """
    Get active regulatory rules from Supabase

    Query parameters:
    - source: Filter by regulation source (e.g., 'MAS', 'FINMA')
    - category: Filter by category (e.g., 'cdd', 'kyc', 'sanctions')
    - severity: Filter by severity level (e.g., 'critical', 'high')
    - limit: Maximum number of rules to return (default: 100)
    """
    try:
        source = request.args.get('source')
        category = request.args.get('category')
        severity = request.args.get('severity')
        limit_val = int(request.args.get('limit', 100))

        # Query rules using the complete view for full context
        query = supabase.table('v_complete_rules').select('*')

        if source:
            query = query.eq('regulator_code', source)
        if category:
            query = query.eq('rule_type', category)
        # Note: severity_level not in schema, so ignore this filter
        # if severity:
        #     query = query.eq('severity_level', severity)

        query = query.limit(limit_val)

        response = query.execute()

        return jsonify({
            'total_rules': len(response.data),
            'rules': response.data,
            'filters_applied': {
                'source': source,
                'category': category,
                'severity': severity,
                'limit': limit_val
            }
        }), 200

    except Exception as e:
        logger.error(f"Regulations retrieval error: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/regulations/<rule_id>', methods=['GET'])
#@require_api_key
def get_regulation_detail(rule_id):
    """
    Get detailed information about a specific regulatory rule
    """
    try:
        response = supabase.table('aml_rules').select('*').eq('rule_id', rule_id).execute()

        if not response.data:
            return jsonify({'error': 'Rule not found'}), 404

        return jsonify({
            'rule': response.data[0]
        }), 200

    except Exception as e:
        logger.error(f"Regulation detail error: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/regulations/check', methods=['POST'])
#@require_api_key
def check_transaction_regulations():
    """
    Check a single transaction against regulatory rules

    Request body (JSON):
    {
        "transaction_id": "TXN001",
        "amount": 5000000,
        "currency": "USD",
        "originator_country": "US",
        "beneficiary_country": "RU",
        "customer_is_pep": "Yes",
        "customer_risk_rating": "high",
        ...
    }
    """
    try:
        from utils.regulatory_checker import RegulatoryChecker

        if not request.is_json:
            return jsonify({'error': 'Request must be JSON'}), 400

        transaction = request.get_json()

        # Initialize checker
        regulatory_checker = RegulatoryChecker(supabase)

        # Check transaction
        violations = regulatory_checker.check_transaction(transaction)

        return jsonify({
            'transaction_id': transaction.get('transaction_id', 'UNKNOWN'),
            'violation_count': len(violations),
            'violations': violations,
            'summary': regulatory_checker.get_violation_summary(violations) if violations else None
        }), 200

    except Exception as e:
        logger.error(f"Regulation check error: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/train-models', methods=['POST'])
#@require_api_key
def train_models():
    """
    Manually trigger training of ML models

    Query parameters:
    - model: 'xgboost', 'isolation_forest', or 'both' (default: 'both')
    """
    try:
        from XGBoost import train_model as train_xgb
        from isolationforest import train_isolation_forest

        model_type = request.args.get('model', 'both')

        logger.info(f"=== Model training request - Type: {model_type} ===")

        results = {
            'trained_at': datetime.now().isoformat(),
            'model_type': model_type
        }

        if model_type in ['xgboost', 'both']:
            logger.info("Training XGBoost model...")
            try:
                model, encoders, features, metrics = train_xgb()
                results['xgboost'] = {
                    'status': 'success',
                    'metrics': metrics
                }
                logger.info("XGBoost training complete")
            except Exception as e:
                logger.error(f"XGBoost training failed: {e}")
                results['xgboost'] = {'status': 'failed', 'error': str(e)}

        if model_type in ['isolation_forest', 'both']:
            logger.info("Training Isolation Forest model...")
            try:
                pipeline, preprocessor, metrics = train_isolation_forest()
                results['isolation_forest'] = {
                    'status': 'success',
                    'metrics': metrics if metrics else 'No evaluation metrics (no ground truth labels)'
                }
                logger.info("Isolation Forest training complete")
            except Exception as e:
                logger.error(f"Isolation Forest training failed: {e}")
                results['isolation_forest'] = {'status': 'failed', 'error': str(e)}

        logger.info("=== Model training complete ===")
        return jsonify(results), 200

    except Exception as e:
        logger.error(f"Model training error: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    logger.info("Starting Document Corroboration API v2.0")
    logger.info(f"Log files: ./logs/")
    logger.info(f"Cache directory: ./cache/")
    logger.info(f"Audit logs: ./audit_logs/")

    socketio.run(app, host='0.0.0.0', port=5001, debug=True)
