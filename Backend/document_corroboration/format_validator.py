"""
Format Validation System
- Formatting checks: Detect double spacing, irregular fonts, inconsistent indentation
- Content validation: Identify spelling mistakes, incorrect headers, missing sections
- Structure analysis: Verify document organization and completeness
- Template matching: Compare against standard document templates
"""

import re
import os
from typing import Dict, List, Any
from collections import Counter
import json
try:
    import fitz  # PyMuPDF for PDF font analysis
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False


class FormatValidator:
    def __init__(self):
        self.issues = []
        self.risk_score = 0

    def validate_document(self, file_path: str, extracted_text: str = None) -> Dict[str, Any]:
        """
        Perform comprehensive format validation on a document
        """
        self.issues = []
        self.risk_score = 0

        # If no text provided, try to extract it
        if extracted_text is None:
            extracted_text = self._extract_text(file_path)

        # Run all validation checks
        formatting_issues = self._check_formatting(extracted_text)
        content_issues = self._check_content_validation(extracted_text)
        structure_issues = self._check_structure(extracted_text)

        # PDF-specific checks
        font_issues = []
        if file_path.lower().endswith('.pdf'):
            font_issues = self._analyze_pdf_fonts(file_path)

        # Calculate risk score
        self.risk_score = self._calculate_risk_score(
            formatting_issues, content_issues, structure_issues, font_issues
        )

        return {
            "file_name": os.path.basename(file_path),
            "validation_status": "PASS" if self.risk_score < 30 else "WARNING" if self.risk_score < 70 else "FAIL",
            "risk_score": self.risk_score,
            "issues": {
                "formatting": formatting_issues,
                "content": content_issues,
                "structure": structure_issues,
                "fonts": font_issues
            },
            "total_issues": len(formatting_issues) + len(content_issues) + len(structure_issues) + len(font_issues),
            "recommendations": self._generate_recommendations()
        }

    def _extract_text(self, file_path: str) -> str:
        """Extract text from various file formats"""
        ext = os.path.splitext(file_path)[1].lower()

        if ext == '.txt':
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        elif ext == '.pdf':
            # Use PyPDF2 or similar
            try:
                from PyPDF2 import PdfReader
                reader = PdfReader(file_path)
                text = ""
                for page in reader.pages:
                    text += page.extract_text()
                return text
            except:
                return ""
        else:
            # For other formats, return empty for now
            return ""

    def _check_formatting(self, text: str) -> List[Dict[str, str]]:
        """Detect formatting issues"""
        issues = []

        # Check for double spacing
        double_spaces = len(re.findall(r'  +', text))
        if double_spaces > 5:
            issues.append({
                "type": "double_spacing",
                "severity": "LOW",
                "count": double_spaces,
                "description": f"Found {double_spaces} instances of double spacing"
            })

        # Check for inconsistent indentation
        lines = text.split('\n')
        indent_patterns = [len(line) - len(line.lstrip()) for line in lines if line.strip()]
        if len(set(indent_patterns)) > 5:
            issues.append({
                "type": "inconsistent_indentation",
                "severity": "MEDIUM",
                "description": f"Inconsistent indentation detected across {len(set(indent_patterns))} different levels"
            })

        # Check for mixed line endings
        crlf_count = text.count('\r\n')
        lf_count = text.count('\n') - crlf_count
        if crlf_count > 0 and lf_count > 0:
            issues.append({
                "type": "mixed_line_endings",
                "severity": "LOW",
                "description": "Mixed line endings detected (CRLF and LF)"
            })

        # Check for trailing whitespace
        trailing_whitespace = sum(1 for line in lines if line.endswith(' ') or line.endswith('\t'))
        if trailing_whitespace > 10:
            issues.append({
                "type": "trailing_whitespace",
                "severity": "LOW",
                "count": trailing_whitespace,
                "description": f"{trailing_whitespace} lines have trailing whitespace"
            })

        return issues

    def _check_content_validation(self, text: str) -> List[Dict[str, str]]:
        """Validate content for common issues"""
        issues = []

        # Check for common spelling mistakes (basic check)
        common_mistakes = {
            r'\bteh\b': 'the',
            r'\brecieve\b': 'receive',
            r'\boccured\b': 'occurred',
            r'\bseperate\b': 'separate',
        }

        for pattern, correction in common_mistakes.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                issues.append({
                    "type": "spelling_error",
                    "severity": "MEDIUM",
                    "word": matches[0],
                    "suggestion": correction,
                    "count": len(matches),
                    "description": f"Possible spelling error: '{matches[0]}' (should be '{correction}')"
                })

        # Check for missing standard sections (for financial documents)
        required_sections = ['date', 'amount', 'signature', 'party', 'terms']
        missing_sections = [
            section for section in required_sections
            if not re.search(section, text, re.IGNORECASE)
        ]

        if missing_sections:
            issues.append({
                "type": "missing_sections",
                "severity": "HIGH",
                "sections": missing_sections,
                "description": f"Missing potential required sections: {', '.join(missing_sections)}"
            })

        # Check for incomplete sentences (ending without punctuation)
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        incomplete_sentences = [
            line for line in lines
            if len(line) > 20 and not line[-1] in '.!?;:'
        ]
        if len(incomplete_sentences) > 5:
            issues.append({
                "type": "incomplete_sentences",
                "severity": "MEDIUM",
                "count": len(incomplete_sentences),
                "description": f"{len(incomplete_sentences)} lines appear to be incomplete sentences"
            })

        return issues

    def _check_structure(self, text: str) -> List[Dict[str, str]]:
        """Verify document structure and organization"""
        issues = []

        lines = text.split('\n')
        non_empty_lines = [line for line in lines if line.strip()]

        # Check document length
        if len(non_empty_lines) < 10:
            issues.append({
                "type": "insufficient_content",
                "severity": "HIGH",
                "line_count": len(non_empty_lines),
                "description": f"Document appears too short ({len(non_empty_lines)} lines)"
            })

        # Check for headers (capitalized lines or numbered sections)
        headers = [
            line for line in non_empty_lines
            if re.match(r'^[A-Z\s\d\.]+$', line.strip()) or re.match(r'^\d+\.', line.strip())
        ]

        if len(headers) == 0 and len(non_empty_lines) > 50:
            issues.append({
                "type": "missing_headers",
                "severity": "MEDIUM",
                "description": "No clear section headers detected in document"
            })

        # Check for consistent numbering
        numbered_items = re.findall(r'^(\d+)\.', text, re.MULTILINE)
        if numbered_items:
            numbers = [int(n) for n in numbered_items]
            if numbers != list(range(1, len(numbers) + 1)):
                issues.append({
                    "type": "inconsistent_numbering",
                    "severity": "MEDIUM",
                    "description": "Numbering sequence appears inconsistent"
                })

        # Check for balanced brackets/parentheses
        open_parens = text.count('(')
        close_parens = text.count(')')
        if open_parens != close_parens:
            issues.append({
                "type": "unbalanced_parentheses",
                "severity": "MEDIUM",
                "description": f"Unbalanced parentheses: {open_parens} opening, {close_parens} closing"
            })

        return issues

    def _analyze_pdf_fonts(self, file_path: str) -> List[Dict[str, str]]:
        """
        Analyze fonts in PDF to detect irregular usage and copy-paste forgery
        """
        issues = []

        if not PYMUPDF_AVAILABLE:
            return [{
                "type": "font_analysis_unavailable",
                "severity": "LOW",
                "description": "Install PyMuPDF (pip install PyMuPDF) for font analysis"
            }]

        try:
            doc = fitz.open(file_path)
            font_usage = {}  # Track font usage across document
            font_sizes = []
            page_fonts = []  # Fonts per page

            for page_num, page in enumerate(doc):
                page_font_set = set()
                blocks = page.get_text("dict")["blocks"]

                for block in blocks:
                    if "lines" in block:
                        for line in block["lines"]:
                            for span in line["spans"]:
                                font_name = span.get("font", "Unknown")
                                font_size = span.get("size", 0)

                                # Track font usage
                                if font_name not in font_usage:
                                    font_usage[font_name] = {
                                        "count": 0,
                                        "sizes": [],
                                        "pages": set()
                                    }

                                font_usage[font_name]["count"] += 1
                                font_usage[font_name]["sizes"].append(font_size)
                                font_usage[font_name]["pages"].add(page_num)
                                page_font_set.add(font_name)
                                font_sizes.append(font_size)

                page_fonts.append(page_font_set)

            doc.close()

            # Analysis 1: Too many different fonts (copy-paste indicator)
            unique_fonts = len(font_usage)
            if unique_fonts > 5:
                issues.append({
                    "type": "excessive_fonts",
                    "severity": "HIGH",
                    "count": unique_fonts,
                    "fonts": list(font_usage.keys()),
                    "description": f"Document uses {unique_fonts} different fonts - possible copy-paste forgery"
                })
            elif unique_fonts > 3:
                issues.append({
                    "type": "multiple_fonts",
                    "severity": "MEDIUM",
                    "count": unique_fonts,
                    "fonts": list(font_usage.keys()),
                    "description": f"Document uses {unique_fonts} different fonts - verify consistency"
                })

            # Analysis 2: Inconsistent font sizes
            if font_sizes:
                from collections import Counter
                size_counts = Counter([round(size, 1) for size in font_sizes])

                if len(size_counts) > 10:
                    issues.append({
                        "type": "inconsistent_font_sizes",
                        "severity": "MEDIUM",
                        "unique_sizes": len(size_counts),
                        "description": f"{len(size_counts)} different font sizes detected - possible editing"
                    })

            # Analysis 3: Font changes mid-page (suspicious)
            for page_num, fonts_on_page in enumerate(page_fonts):
                if len(fonts_on_page) > 3:
                    issues.append({
                        "type": "mixed_fonts_on_page",
                        "severity": "MEDIUM",
                        "page": page_num + 1,
                        "fonts": list(fonts_on_page),
                        "description": f"Page {page_num + 1} uses {len(fonts_on_page)} different fonts"
                    })

            # Analysis 4: Embedded vs System fonts (embedded fonts are more authentic)
            system_fonts = ["Arial", "Times", "Helvetica", "Courier", "TimesNewRoman"]
            embedded_count = sum(1 for font in font_usage.keys()
                               if not any(sys_font in font for sys_font in system_fonts))

            if embedded_count == 0 and unique_fonts > 1:
                issues.append({
                    "type": "only_system_fonts",
                    "severity": "LOW",
                    "description": "Only system fonts detected - original documents often have embedded fonts"
                })

            # Analysis 5: Single character in unusual font (insertion indicator)
            for font_name, data in font_usage.items():
                if data["count"] < 5:  # Very rarely used font
                    issues.append({
                        "type": "rarely_used_font",
                        "severity": "MEDIUM",
                        "font": font_name,
                        "occurrences": data["count"],
                        "description": f"Font '{font_name}' used only {data['count']} times - possible text insertion"
                    })

        except Exception as e:
            issues.append({
                "type": "font_analysis_error",
                "severity": "LOW",
                "description": f"Font analysis failed: {str(e)}"
            })

        return issues

    def _calculate_risk_score(self, formatting_issues: List, content_issues: List,
                             structure_issues: List, font_issues: List = None) -> int:
        """Calculate overall risk score (0-100)"""
        score = 0

        severity_weights = {
            "LOW": 5,
            "MEDIUM": 15,
            "HIGH": 30
        }

        all_issues = formatting_issues + content_issues + structure_issues
        if font_issues:
            all_issues.extend(font_issues)

        for issue in all_issues:
            score += severity_weights.get(issue.get("severity", "LOW"), 5)

        return min(score, 100)  # Cap at 100

    def _generate_recommendations(self) -> List[str]:
        """Generate actionable recommendations based on issues found"""
        recommendations = []

        if self.risk_score < 30:
            recommendations.append("Document formatting appears acceptable")
        elif self.risk_score < 70:
            recommendations.append("Review and correct identified formatting issues")
            recommendations.append("Verify all required sections are present")
        else:
            recommendations.append("CRITICAL: Document requires significant revision")
            recommendations.append("Consider regenerating document from template")
            recommendations.append("Manual review recommended before acceptance")

        return recommendations