"""
Risk Scoring & Reporting System
- Risk assessment: Calculate risk scores based on multiple factors
- Real-time feedback: Provide immediate feedback to compliance officers
- Report generation: Create detailed reports highlighting issues
- Audit trail: Maintain comprehensive logs of all analysis performed
"""

import os
import json
from typing import Dict, List, Any
from datetime import datetime
import hashlib


class RiskScorer:
    def __init__(self):
        self.audit_log_dir = "./audit_logs"
        os.makedirs(self.audit_log_dir, exist_ok=True)

    def calculate_comprehensive_risk(
        self,
        document_analysis: Dict = None,
        format_validation: Dict = None,
        image_analysis: Dict = None
    ) -> Dict[str, Any]:
        """
        Calculate comprehensive risk score based on all analysis components
        """
        risk_factors = []
        total_risk = 0
        max_severity = "LOW"

        # Component 1: Document Processing Risk
        if document_analysis:
            doc_risk = self._assess_document_risk(document_analysis)
            risk_factors.append(doc_risk)
            total_risk += doc_risk['score']
            max_severity = self._max_severity(max_severity, doc_risk['severity'])

        # Component 2: Format Validation Risk
        if format_validation:
            format_risk = self._assess_format_risk(format_validation)
            risk_factors.append(format_risk)
            total_risk += format_risk['score']
            max_severity = self._max_severity(max_severity, format_risk['severity'])

        # Component 3: Image Analysis Risk
        if image_analysis:
            image_risk = self._assess_image_risk(image_analysis)
            risk_factors.append(image_risk)
            total_risk += image_risk['score']
            max_severity = self._max_severity(max_severity, image_risk['severity'])

        # Normalize total risk to 0-100 scale
        num_components = len(risk_factors)
        normalized_risk = min(total_risk / num_components if num_components > 0 else 0, 100)

        # Determine overall status
        status = self._determine_status(normalized_risk, max_severity)

        return {
            "overall_risk_score": round(normalized_risk, 2),
            "status": status,
            "max_severity": max_severity,
            "risk_factors": risk_factors,
            "components_analyzed": num_components,
            "timestamp": datetime.now().isoformat(),
            "recommendation": self._get_recommendation(status, normalized_risk)
        }

    def _assess_document_risk(self, analysis: Dict) -> Dict[str, Any]:
        """Assess risk from document processing analysis with dynamic calculation"""
        # Ensure analysis is a dictionary
        if not isinstance(analysis, dict):
            return {
                "component": "document_processing",
                "score": 80,
                "severity": "HIGH",
                "issues": ["Invalid analysis format - expected dictionary"],
                "confidence": 0,
                "details": {}
            }

        risk_score = 0
        issues = []
        details = {}

        # Check if document was processed successfully
        if analysis.get('error'):
            risk_score = 80
            issues.append(f"Document processing failed: {analysis.get('error')}")
            severity = "HIGH"
            confidence = 0
        else:
            # Extract structured data from enhanced analysis
            status = analysis.get('status', 'unknown')
            completeness = analysis.get('completeness', {})
            metadata = analysis.get('metadata', {})
            confidence = analysis.get('confidence_score', 50)
            detected_issues = analysis.get('issues_detected', [])

            # Status-based risk
            status_risk_map = {
                "FAILED": 80,
                "INCOMPLETE": 60,
                "REVIEW_REQUIRED": 40,
                "PASS": 10
            }
            risk_score += status_risk_map.get(status, 50)

            # Completeness-based risk
            completeness_score = completeness.get('completeness_score', 0)
            if completeness_score < 50:
                risk_score += 30
                issues.append(f"Low completeness: {completeness_score:.0f}%")
            elif completeness_score < 80:
                risk_score += 15
                issues.append(f"Moderate completeness concerns: {completeness_score:.0f}%")

            # Text coverage risk (scanned docs are riskier)
            text_coverage = metadata.get('text_coverage_percent', 0)
            if text_coverage < 30:
                risk_score += 20
                issues.append(f"Very low text coverage: {text_coverage:.0f}% - likely scanned")
            elif text_coverage < 60:
                risk_score += 10
                issues.append(f"Low text coverage: {text_coverage:.0f}%")

            # Document type classification
            doc_type = metadata.get('document_type', 'unknown')
            type_confidence = metadata.get('confidence', 0)
            if doc_type == 'unknown' or type_confidence < 30:
                risk_score += 15
                issues.append("Document type could not be reliably classified")

            # Add specific detected issues
            for issue in detected_issues:
                issue_desc = issue.get('description', '')
                if issue_desc and issue_desc not in [i for i in issues]:
                    issues.append(issue_desc)

            # Missing elements
            missing = completeness.get('missing_elements', [])
            if missing:
                details['missing_elements'] = missing

            # Metadata details
            details['document_type'] = doc_type
            details['page_count'] = metadata.get('page_count', 0)
            details['text_coverage'] = f"{text_coverage:.1f}%"
            details['is_scanned'] = metadata.get('is_scanned', False)
            details['completeness_score'] = f"{completeness_score:.0f}%"

            severity = "HIGH" if risk_score > 60 else "MEDIUM" if risk_score > 30 else "LOW"

        return {
            "component": "document_processing",
            "score": min(100, risk_score),  # Cap at 100
            "severity": severity,
            "issues": issues[:5],  # Top 5 issues
            "confidence": confidence,
            "details": details
        }

    def _assess_format_risk(self, validation: Dict) -> Dict[str, Any]:
        """Assess risk from format validation"""
        # Ensure validation is a dictionary
        if not isinstance(validation, dict):
            return {
                "component": "format_validation",
                "score": 80,
                "severity": "HIGH",
                "issues": ["Invalid validation format - expected dictionary"],
                "total_issues": 0
            }

        risk_score = validation.get('risk_score', 0)
        total_issues = validation.get('total_issues', 0)

        severity = "HIGH" if risk_score > 70 else "MEDIUM" if risk_score > 30 else "LOW"

        issues = []
        if validation.get('issues'):
            for category, category_issues in validation['issues'].items():
                if isinstance(category_issues, list):
                    for issue in category_issues:
                        if isinstance(issue, dict):
                            issues.append(f"{category}: {issue.get('description', 'Unknown issue')}")
                        else:
                            issues.append(f"{category}: {str(issue)}")

        return {
            "component": "format_validation",
            "score": risk_score,
            "severity": severity,
            "issues": issues[:5],  # Top 5 issues
            "total_issues": total_issues
        }

    def _assess_image_risk(self, analysis: Dict) -> Dict[str, Any]:
        """Assess risk from image analysis"""
        # Ensure analysis is a dictionary
        if not isinstance(analysis, dict):
            return {
                "component": "image_analysis",
                "score": 80,
                "severity": "HIGH",
                "issues": ["Invalid analysis format - expected dictionary"]
            }

        # Invert authenticity score to get risk score
        authenticity = analysis.get('authenticity_score', 100)
        risk_score = 100 - authenticity

        severity = "HIGH" if risk_score > 60 else "MEDIUM" if risk_score > 30 else "LOW"

        issues = analysis.get('issues', [])
        issue_descriptions = []

        if isinstance(issues, list):
            for issue in issues:
                if isinstance(issue, dict):
                    issue_descriptions.append(issue.get('description', ''))
                else:
                    issue_descriptions.append(str(issue))

        if isinstance(analysis.get('tampering_indicators'), dict):
            if analysis['tampering_indicators'].get('tampering_detected'):
                issue_descriptions.append("Image tampering detected")

        if isinstance(analysis.get('ai_detection'), dict):
            if analysis['ai_detection'].get('likely_ai_generated'):
                issue_descriptions.append("Image likely AI-generated")

        return {
            "component": "image_analysis",
            "score": risk_score,
            "severity": severity,
            "issues": issue_descriptions
        }

    def _max_severity(self, current: str, new: str) -> str:
        """Return the higher severity level"""
        severity_order = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}
        return current if severity_order.get(current, 0) > severity_order.get(new, 0) else new

    def _determine_status(self, risk_score: float, max_severity: str) -> str:
        """Determine overall document status"""
        if risk_score < 20 and max_severity in ["LOW"]:
            return "APPROVED"
        elif risk_score < 40 and max_severity in ["LOW", "MEDIUM"]:
            return "APPROVED_WITH_NOTES"
        elif risk_score < 70:
            return "REVIEW_REQUIRED"
        else:
            return "REJECTED"

    def _get_recommendation(self, status: str, risk_score: float) -> str:
        """Get recommendation based on status"""
        recommendations = {
            "APPROVED": f"Document meets all requirements and can be approved. (Risk Score: {risk_score:.1f})",
            "APPROVED_WITH_NOTES": f"Document is acceptable but has minor issues that should be noted. (Risk Score: {risk_score:.1f})",
            "REVIEW_REQUIRED": f"Document requires manual review by compliance officer before proceeding. (Risk Score: {risk_score:.1f})",
            "REJECTED": f"Document does not meet requirements and should be rejected. (Risk Score: {risk_score:.1f})"
        }
        return recommendations.get(status, f"Unknown status (Risk Score: {risk_score:.1f})")

    def generate_report(
        self,
        file_name: str,
        risk_assessment: Dict,
        document_analysis: Dict = None,
        format_validation: Dict = None,
        image_analysis: Dict = None,
        save_to_file: bool = True
    ) -> Dict[str, Any]:
        """
        Generate comprehensive analysis report
        """
        report = {
            "report_id": self._generate_report_id(file_name),
            "file_name": file_name,
            "analysis_timestamp": datetime.now().isoformat(),
            "analyst": "Automated System",
            "summary": {
                "overall_risk_score": risk_assessment['overall_risk_score'],
                "status": risk_assessment['status'],
                "max_severity": risk_assessment['max_severity'],
                "recommendation": risk_assessment['recommendation']
            },
            "detailed_analysis": {
                "document_processing": self._format_analysis_section(document_analysis),
                "format_validation": self._format_analysis_section(format_validation),
                "image_analysis": self._format_analysis_section(image_analysis)
            },
            "risk_factors": risk_assessment['risk_factors'],
            "action_items": self._generate_action_items(risk_assessment),
            "audit_trail": {
                "components_analyzed": risk_assessment['components_analyzed'],
                "analysis_timestamp": risk_assessment['timestamp']
            }
        }

        # Save to audit log
        if save_to_file:
            self._save_audit_log(report)

        return report

    def _generate_report_id(self, file_name: str) -> str:
        """Generate unique report ID"""
        timestamp = datetime.now().isoformat()
        hash_input = f"{file_name}{timestamp}".encode()
        return hashlib.md5(hash_input).hexdigest()[:12]

    def _format_analysis_section(self, analysis: Dict) -> Dict:
        """Format analysis section for report"""
        if not analysis:
            return {"status": "not_analyzed"}

        return {
            "status": analysis.get('status') or analysis.get('validation_status', 'unknown'),
            "key_findings": self._extract_key_findings(analysis),
            "issues_count": len(analysis.get('issues', [])) if isinstance(analysis.get('issues'), list) else analysis.get('total_issues', 0)
        }

    def _extract_key_findings(self, analysis: Dict) -> List[str]:
        """Extract key findings from analysis"""
        findings = []

        # Extract from different analysis types
        if 'issues' in analysis:
            if isinstance(analysis['issues'], dict):
                for category, issues in analysis['issues'].items():
                    if issues and len(issues) > 0:
                        findings.append(f"{category.title()}: {len(issues)} issue(s) found")
            elif isinstance(analysis['issues'], list):
                findings.extend([issue.get('description', str(issue)) for issue in analysis['issues'][:3]])

        if 'recommendations' in analysis:
            findings.extend(analysis['recommendations'][:2])

        return findings[:5]  # Top 5 findings

    def _generate_action_items(self, risk_assessment: Dict) -> List[Dict[str, str]]:
        """Generate action items based on risk assessment"""
        action_items = []
        status = risk_assessment['status']
        risk_factors = risk_assessment.get('risk_factors', [])

        if status == "REJECTED":
            action_items.append({
                "priority": "HIGH",
                "action": "Reject document and request resubmission",
                "assignee": "Compliance Officer"
            })

        if status == "REVIEW_REQUIRED":
            action_items.append({
                "priority": "MEDIUM",
                "action": "Conduct manual review of document",
                "assignee": "Compliance Officer"
            })

        # Add specific actions based on risk factors
        for factor in risk_factors:
            if factor['severity'] in ['HIGH', 'CRITICAL'] and factor.get('issues'):
                action_items.append({
                    "priority": factor['severity'],
                    "action": f"Address {factor['component']} issues: {factor['issues'][0] if factor['issues'] else 'Review required'}",
                    "assignee": "Document Submitter"
                })

        return action_items

    def _save_audit_log(self, report: Dict) -> None:
        """Save report to audit log"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(
            self.audit_log_dir,
            f"audit_{report['report_id']}_{timestamp}.json"
        )

        try:
            with open(log_file, 'w') as f:
                json.dump(report, f, indent=2)
            print(f"Audit log saved: {log_file}")
        except Exception as e:
            print(f"Failed to save audit log: {e}")

    def get_audit_history(self, file_name: str = None, limit: int = 10) -> List[Dict]:
        """Retrieve audit history"""
        audit_files = sorted(
            [f for f in os.listdir(self.audit_log_dir) if f.endswith('.json')],
            reverse=True
        )[:limit]

        history = []
        for audit_file in audit_files:
            try:
                with open(os.path.join(self.audit_log_dir, audit_file), 'r') as f:
                    report = json.load(f)
                    if file_name is None or report.get('file_name') == file_name:
                        history.append({
                            "report_id": report['report_id'],
                            "file_name": report['file_name'],
                            "timestamp": report['analysis_timestamp'],
                            "status": report['summary']['status'],
                            "risk_score": report['summary']['overall_risk_score']
                        })
            except Exception as e:
                print(f"Error reading audit file {audit_file}: {e}")

        return history
