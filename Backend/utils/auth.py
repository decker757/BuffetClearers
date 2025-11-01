"""
API Authentication utilities
Provides API key-based authentication for endpoints
"""

from functools import wraps
from flask import request, jsonify
import os
from dotenv import load_dotenv

load_dotenv()

# Get API key from environment
API_KEY = os.getenv('API_KEY', 'dev-key-12345')  # Default for development


def require_api_key(f):
    """
    Decorator to require API key for endpoint access
    Usage:
        @app.route('/api/validate')
        @require_api_key
        def validate_document():
            ...
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check for API key in headers
        provided_key = request.headers.get('x-api-key')

        if not provided_key:
            return jsonify({
                'error': 'Missing API key',
                'message': 'Please provide x-api-key header'
            }), 401

        if provided_key != API_KEY:
            return jsonify({
                'error': 'Invalid API key',
                'message': 'The provided API key is not valid'
            }), 403

        # API key is valid, proceed with request
        return f(*args, **kwargs)

    return decorated_function


def optional_api_key(f):
    """
    Decorator that checks for API key but doesn't require it
    Useful for endpoints that have different behavior based on auth
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        provided_key = request.headers.get('x-api-key')
        is_authenticated = provided_key == API_KEY if provided_key else False

        # Pass authentication status to the function
        return f(*args, is_authenticated=is_authenticated, **kwargs)

    return decorated_function
