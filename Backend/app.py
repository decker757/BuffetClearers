from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from datetime import datetime
from supabase import create_client
from dotenv import load_dotenv
import os
import json
import psycopg2  # <-- Added for PostgreSQL connection

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


if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5001, debug=True)