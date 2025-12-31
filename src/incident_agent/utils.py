"""Utility functions for the incident triage agent."""

import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from .schemas import IncidentReport, IncidentData


def generate_incident_id() -> str:
    """Generate a unique incident ID."""
    return f"INC-{uuid.uuid4().hex[:8].upper()}"


def current_timestamp() -> datetime:
    """Get current timestamp in UTC."""
    return datetime.now(timezone.utc)


def parse_incident_data(raw_data: Dict[str, Any]) -> IncidentReport:
    """Parse raw incident data into structured IncidentReport."""
    # Generate ID if not provided
    incident_id = raw_data.get("id") or generate_incident_id()
    
    # Parse timestamp
    timestamp_str = raw_data.get("timestamp")
    if timestamp_str:
        if isinstance(timestamp_str, str):
            try:
                timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            except ValueError:
                timestamp = current_timestamp()
        else:
            timestamp = timestamp_str
    else:
        timestamp = current_timestamp()
    
    # Extract affected systems
    affected_systems = raw_data.get("affected_systems", [])
    if isinstance(affected_systems, str):
        affected_systems = [s.strip() for s in affected_systems.split(",")]
    
    # Extract severity indicators
    severity_indicators = raw_data.get("severity_indicators", [])
    if isinstance(severity_indicators, str):
        severity_indicators = [s.strip() for s in severity_indicators.split(",")]
    
    return IncidentReport(
        id=incident_id,
        title=raw_data.get("title", "Untitled Incident"),
        description=raw_data.get("description", ""),
        source=raw_data.get("source", "api"),
        timestamp=timestamp,
        reporter=raw_data.get("reporter", "unknown"),
        affected_systems=affected_systems,
        error_logs=raw_data.get("error_logs"),
        metrics_data=raw_data.get("metrics_data"),
        severity_indicators=severity_indicators
    )


def extract_severity_keywords(text: str) -> List[str]:
    """Extract severity-related keywords from incident text."""
    severity_keywords = {
        "critical": ["down", "outage", "critical", "emergency", "urgent", "production", "p0", "sev1"],
        "high": ["slow", "degraded", "error", "failing", "timeout", "p1", "sev2"],
        "medium": ["warning", "issue", "problem", "concern", "p2", "sev3"],
        "low": ["minor", "cosmetic", "enhancement", "p3", "sev4"]
    }
    
    text_lower = text.lower()
    found_keywords = []
    
    for severity, keywords in severity_keywords.items():
        for keyword in keywords:
            if keyword in text_lower:
                found_keywords.append(f"{severity}:{keyword}")
    
    return found_keywords


def extract_security_indicators(text: str) -> List[str]:
    """Extract security-related indicators from incident text."""
    security_keywords = [
        "security", "breach", "unauthorized", "malicious", "attack", "vulnerability",
        "exploit", "intrusion", "compromise", "suspicious", "phishing", "malware",
        "ddos", "injection", "xss", "csrf", "authentication", "authorization"
    ]
    
    text_lower = text.lower()
    found_indicators = []
    
    for keyword in security_keywords:
        if keyword in text_lower:
            found_indicators.append(keyword)
    
    return found_indicators


def format_incident_summary(incident: IncidentReport) -> str:
    """Format incident data for display or logging."""
    return (
        f"Incident {incident.id}: {incident.title}\n"
        f"Severity Indicators: {', '.join(incident.severity_indicators)}\n"
        f"Affected Systems: {', '.join(incident.affected_systems)}\n"
        f"Reporter: {incident.reporter}\n"
        f"Source: {incident.source}\n"
        f"Timestamp: {incident.timestamp.isoformat()}"
    )


def validate_team_assignment(team: str, available_teams: List[str]) -> bool:
    """Validate that a team assignment is valid."""
    return team in available_teams


def calculate_incident_priority_score(
    severity: str, 
    affected_systems_count: int, 
    security_incident: bool = False
) -> int:
    """Calculate a numeric priority score for incident ordering."""
    severity_scores = {
        "critical": 1000,
        "high": 100,
        "medium": 10,
        "low": 1
    }
    
    base_score = severity_scores.get(severity, 1)
    
    # Multiply by affected systems count
    system_multiplier = max(1, affected_systems_count)
    
    # Security incidents get priority boost
    security_multiplier = 2 if security_incident else 1
    
    return base_score * system_multiplier * security_multiplier