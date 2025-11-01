"""
File validation utilities
- MIME type checking
- File hash generation
- File size validation
"""

import hashlib
import os
from typing import Tuple, Optional

# Try to import python-magic, fall back to extension-based detection
try:
    import magic
    MAGIC_AVAILABLE = True
except ImportError:
    MAGIC_AVAILABLE = False
    print("Warning: python-magic not available, using extension-based MIME detection")


class FileValidator:
    # Allowed MIME types mapping
    ALLOWED_MIME_TYPES = {
        # Documents
        'application/pdf': ['.pdf'],
        'application/msword': ['.doc'],
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
        'text/plain': ['.txt'],

        # Spreadsheets
        'text/csv': ['.csv'],
        'application/vnd.ms-excel': ['.xls'],
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],

        # Images
        'image/jpeg': ['.jpg', '.jpeg'],
        'image/png': ['.png'],
        'image/gif': ['.gif'],
        'image/bmp': ['.bmp'],
        'image/tiff': ['.tiff', '.tif'],
    }

    @staticmethod
    def calculate_file_hash(file_path: str) -> str:
        """Calculate SHA-256 hash of file"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            # Read in chunks to handle large files
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    @staticmethod
    def get_mime_type(file_path: str) -> str:
        """Get MIME type of file using python-magic or fallback to extension"""
        if MAGIC_AVAILABLE:
            try:
                mime = magic.Magic(mime=True)
                return mime.from_file(file_path)
            except Exception:
                # Fallback to extension-based detection if magic fails
                return FileValidator._get_mime_from_extension(file_path)
        else:
            # Use extension-based detection when magic not available
            return FileValidator._get_mime_from_extension(file_path)

    @staticmethod
    def _get_mime_from_extension(file_path: str) -> str:
        """Fallback MIME type detection from extension"""
        ext = os.path.splitext(file_path)[1].lower()
        mime_map = {
            '.pdf': 'application/pdf',
            '.doc': 'application/msword',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.txt': 'text/plain',
            '.csv': 'text/csv',
            '.xls': 'application/vnd.ms-excel',
            '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.bmp': 'image/bmp',
            '.tiff': 'image/tiff',
            '.tif': 'image/tiff',
        }
        return mime_map.get(ext, 'application/octet-stream')

    @staticmethod
    def validate_file(file_path: str, max_size_mb: int = 16) -> Tuple[bool, Optional[str], dict]:
        """
        Validate file comprehensively

        Returns:
            (is_valid, error_message, metadata)
        """
        metadata = {
            'file_path': file_path,
            'file_name': os.path.basename(file_path),
            'file_size': 0,
            'file_hash': None,
            'mime_type': None,
            'extension': None
        }

        # Check if file exists
        if not os.path.exists(file_path):
            return False, "File does not exist", metadata

        # Get file size
        file_size = os.path.getsize(file_path)
        metadata['file_size'] = file_size

        # Check file size
        max_size_bytes = max_size_mb * 1024 * 1024
        if file_size > max_size_bytes:
            return False, f"File size ({file_size / 1024 / 1024:.2f} MB) exceeds maximum allowed ({max_size_mb} MB)", metadata

        # Check for empty files
        if file_size == 0:
            return False, "File is empty", metadata

        # Get extension
        ext = os.path.splitext(file_path)[1].lower()
        metadata['extension'] = ext

        # Get MIME type
        mime_type = FileValidator.get_mime_type(file_path)
        metadata['mime_type'] = mime_type

        # Validate MIME type matches extension
        if mime_type not in FileValidator.ALLOWED_MIME_TYPES:
            return False, f"File type not allowed: {mime_type}", metadata

        allowed_extensions = FileValidator.ALLOWED_MIME_TYPES[mime_type]
        if ext not in allowed_extensions:
            return False, f"Extension {ext} does not match MIME type {mime_type}", metadata

        # Calculate file hash
        try:
            file_hash = FileValidator.calculate_file_hash(file_path)
            metadata['file_hash'] = file_hash
        except Exception as e:
            return False, f"Failed to calculate file hash: {str(e)}", metadata

        return True, None, metadata
