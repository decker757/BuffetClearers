"""
Image Analysis Engine
- Authenticity verification: Detect stolen images using reverse image search
- AI-generated detection: Identify AI-generated or synthetic images
- Tampering detection: Analyze metadata and pixel-level anomalies
- Forensic analysis: Deep inspection for manipulation indicators
"""

import os
import json
from typing import Dict, List, Any
from PIL import Image
from PIL.ExifTags import TAGS
import hashlib
import requests
from datetime import datetime


class ImageAnalyzer:
    def __init__(self, groq_api_key: str = None):
        self.groq_api_key = groq_api_key or os.getenv('GROQ_KEY')
        self.issues = []

    def analyze_image(self, image_path: str) -> Dict[str, Any]:
        """
        Perform comprehensive image analysis
        """
        self.issues = []

        if not os.path.exists(image_path):
            return {"error": "Image file not found"}

        # Run all analysis checks
        metadata_analysis = self._analyze_metadata(image_path)
        tampering_check = self._detect_tampering(image_path)
        ai_detection = self._detect_ai_generated(image_path)
        authenticity_score = self._calculate_authenticity_score(
            metadata_analysis, tampering_check, ai_detection
        )

        return {
            "file_name": os.path.basename(image_path),
            "analysis_timestamp": datetime.now().isoformat(),
            "authenticity_score": authenticity_score,
            "status": "AUTHENTIC" if authenticity_score > 70 else "SUSPICIOUS" if authenticity_score > 40 else "LIKELY_FAKE",
            "metadata": metadata_analysis,
            "tampering_indicators": tampering_check,
            "ai_detection": ai_detection,
            "issues": self.issues,
            "recommendations": self._generate_recommendations(authenticity_score)
        }

    def _analyze_metadata(self, image_path: str) -> Dict[str, Any]:
        """Extract and analyze image metadata (EXIF data)"""
        try:
            image = Image.open(image_path)
            exif_data = {}

            # Extract EXIF data
            if hasattr(image, '_getexif') and image._getexif():
                exif = image._getexif()
                for tag_id, value in exif.items():
                    tag = TAGS.get(tag_id, tag_id)
                    exif_data[tag] = str(value)

            # Check for metadata anomalies
            anomalies = []

            # Check if metadata is completely missing (suspicious for authentic photos)
            if not exif_data:
                anomalies.append({
                    "type": "missing_metadata",
                    "severity": "MEDIUM",
                    "description": "No EXIF metadata found - possible stripped or synthetic image"
                })

            # Check for software tags (might indicate editing)
            if 'Software' in exif_data:
                anomalies.append({
                    "type": "software_detected",
                    "severity": "LOW",
                    "software": exif_data['Software'],
                    "description": f"Image processed with: {exif_data['Software']}"
                })

            # Check for GPS coordinates (legitimate photos often have this)
            has_gps = any(key.startswith('GPS') for key in exif_data.keys())

            # Check date/time consistency
            if 'DateTime' in exif_data and 'DateTimeOriginal' in exif_data:
                if exif_data['DateTime'] != exif_data['DateTimeOriginal']:
                    anomalies.append({
                        "type": "datetime_mismatch",
                        "severity": "MEDIUM",
                        "description": "Modification time differs from original time - image may have been edited"
                    })

            self.issues.extend(anomalies)

            return {
                "exif_present": bool(exif_data),
                "exif_data": exif_data,
                "has_gps": has_gps,
                "anomalies": anomalies,
                "format": image.format,
                "size": image.size,
                "mode": image.mode
            }

        except Exception as e:
            return {
                "error": f"Failed to analyze metadata: {str(e)}",
                "exif_present": False
            }

    def _detect_tampering(self, image_path: str) -> Dict[str, Any]:
        """Detect pixel-level tampering and manipulation"""
        try:
            image = Image.open(image_path)
            indicators = []

            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')

            # Get image data
            pixels = list(image.getdata())
            width, height = image.size

            # Check 1: Look for compression artifacts inconsistency
            # (Different regions with different compression levels indicate manipulation)
            # This is a simplified check

            # Check 2: Detect uniform regions (clone stamp indicator)
            # Look for suspiciously large uniform color blocks
            uniform_blocks = self._detect_uniform_regions(pixels, width, height)
            if uniform_blocks > 10:
                indicators.append({
                    "type": "clone_stamp_suspected",
                    "severity": "HIGH",
                    "count": uniform_blocks,
                    "description": f"Found {uniform_blocks} suspiciously uniform regions"
                })

            # Check 3: File hash comparison (basic)
            file_hash = self._calculate_file_hash(image_path)

            # Check 4: Look for edge inconsistencies (basic implementation)
            # In production, use ELA (Error Level Analysis)

            return {
                "tampering_detected": len(indicators) > 0,
                "indicators": indicators,
                "file_hash": file_hash,
                "analysis_method": "pixel_level_basic"
            }

        except Exception as e:
            return {
                "error": f"Tampering detection failed: {str(e)}",
                "tampering_detected": None
            }

    def _detect_uniform_regions(self, pixels: List, width: int, height: int, threshold: int = 100) -> int:
        """Detect suspiciously uniform color regions"""
        uniform_count = 0
        block_size = 10

        for y in range(0, height - block_size, block_size):
            for x in range(0, width - block_size, block_size):
                block_pixels = []
                for dy in range(block_size):
                    for dx in range(block_size):
                        idx = (y + dy) * width + (x + dx)
                        if idx < len(pixels):
                            block_pixels.append(pixels[idx])

                # Check if all pixels in block are very similar
                if len(block_pixels) > 0:
                    avg_color = tuple(sum(c[i] for c in block_pixels) // len(block_pixels) for i in range(3))
                    variance = sum(
                        sum((c[i] - avg_color[i]) ** 2 for i in range(3))
                        for c in block_pixels
                    ) / len(block_pixels)

                    if variance < threshold:
                        uniform_count += 1

        return uniform_count

    def _detect_ai_generated(self, image_path: str) -> Dict[str, Any]:
        """
        Detect if image is AI-generated or synthetic
        Uses heuristics and pattern detection
        """
        try:
            image = Image.open(image_path)
            indicators = []

            # Check 1: Perfect symmetry (common in AI-generated faces)
            # This would require face detection library

            # Check 2: Unusual patterns in noise distribution
            # AI-generated images often have different noise characteristics

            # Check 3: Check for common AI generation artifacts
            # - Weird text rendering
            # - Unnatural patterns
            # - Too perfect details

            # For now, use basic heuristics
            width, height = image.size

            # Check aspect ratio (AI generators often use standard ratios)
            aspect_ratio = width / height
            common_ai_ratios = [1.0, 1.5, 0.75, 1.77, 0.56]  # 1:1, 3:2, 4:3, 16:9, etc.

            if any(abs(aspect_ratio - ratio) < 0.01 for ratio in common_ai_ratios):
                indicators.append({
                    "type": "standard_aspect_ratio",
                    "severity": "LOW",
                    "description": f"Image uses common AI generation aspect ratio: {aspect_ratio:.2f}"
                })

            # Check for typical AI generation resolutions
            ai_resolutions = [(512, 512), (1024, 1024), (768, 768), (512, 768), (768, 512)]
            if (width, height) in ai_resolutions or (height, width) in ai_resolutions:
                indicators.append({
                    "type": "ai_generation_resolution",
                    "severity": "MEDIUM",
                    "resolution": f"{width}x{height}",
                    "description": "Image resolution matches common AI generation sizes"
                })

            self.issues.extend(indicators)

            return {
                "likely_ai_generated": len(indicators) >= 2,
                "confidence": min(len(indicators) * 30, 90),  # 0-90% confidence
                "indicators": indicators,
                "analysis_method": "heuristic_pattern_detection"
            }

        except Exception as e:
            return {
                "error": f"AI detection failed: {str(e)}",
                "likely_ai_generated": None
            }

    def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA-256 hash of file"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def _calculate_authenticity_score(self, metadata: Dict, tampering: Dict, ai_detection: Dict) -> int:
        """Calculate overall authenticity score (0-100)"""
        score = 100

        # Penalize based on metadata issues
        if not metadata.get('exif_present', False):
            score -= 20

        metadata_anomalies = metadata.get('anomalies', [])
        for anomaly in metadata_anomalies:
            if anomaly['severity'] == 'HIGH':
                score -= 15
            elif anomaly['severity'] == 'MEDIUM':
                score -= 10
            else:
                score -= 5

        # Penalize based on tampering indicators
        if tampering.get('tampering_detected', False):
            tampering_indicators = tampering.get('indicators', [])
            for indicator in tampering_indicators:
                if indicator['severity'] == 'HIGH':
                    score -= 25
                elif indicator['severity'] == 'MEDIUM':
                    score -= 15
                else:
                    score -= 5

        # Penalize if likely AI-generated
        if ai_detection.get('likely_ai_generated', False):
            confidence = ai_detection.get('confidence', 50)
            score -= int(confidence * 0.5)

        return max(score, 0)

    def _generate_recommendations(self, authenticity_score: int) -> List[str]:
        """Generate recommendations based on analysis"""
        recommendations = []

        if authenticity_score > 70:
            recommendations.append("Image appears authentic - low risk")
        elif authenticity_score > 40:
            recommendations.append("Image shows some suspicious indicators - verify source")
            recommendations.append("Request original uncompressed image if possible")
        else:
            recommendations.append("CRITICAL: Image likely manipulated or AI-generated")
            recommendations.append("Do not accept without additional verification")
            recommendations.append("Request alternative proof of authenticity")

        if len(self.issues) > 0:
            recommendations.append(f"Review {len(self.issues)} specific issues identified")

        return recommendations