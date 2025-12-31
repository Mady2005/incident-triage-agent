"""Test configuration and fixtures for incident agent tests."""

import pytest
from datetime import datetime, timezone
from typing import Dict, Any, List

from hypothesis import strategies as st
from hypothesis.strategies import composite

from src.incident_agent.schemas import IncidentReport
from src.incident_agent.models.incident import Incident
from src.incident_agent.models.team import ResponseTeam, TeamRegistry, TeamCapability, TeamType
from src.incident_agent.configuration import Configuration


@pytest.fixture
def config():
    """Provide test configuration."""
    return Configuration()


@pytest.fixture
def team_registry():
    """Provide a team registry for testing."""
    return TeamRegistry()


@pytest.fixture
def sample_incident_report():
    """Provide a sample incident report for testing."""
    return IncidentReport(
        id="INC-TEST001",
        title="Test Database Connection Issue",
        description="Database connections are timing out intermittently",
        source="monitoring",
        timestamp=datetime.now(timezone.utc),
        reporter="monitoring-system",
        affected_systems=["database", "api"],
        error_logs="Connection timeout after 30 seconds",
        severity_indicators=["timeout", "database", "intermittent"]
    )


@pytest.fixture
def sample_incident(sample_incident_report):
    """Provide a sample incident for testing."""
    return Incident(sample_incident_report)


# Hypothesis strategies for property-based testing

@st.composite
def incident_titles(draw):
    """Generate realistic incident titles."""
    prefixes = ["Database", "API", "Service", "Network", "Security", "Performance"]
    issues = ["outage", "timeout", "error", "failure", "slowness", "breach"]
    systems = ["connection", "response", "query", "authentication", "processing"]
    
    prefix = draw(st.sampled_from(prefixes))
    issue = draw(st.sampled_from(issues))
    system = draw(st.sampled_from(systems))
    
    return f"{prefix} {system} {issue}"


@st.composite
def incident_descriptions(draw):
    """Generate realistic incident descriptions."""
    templates = [
        "Users are experiencing {} with {} functionality",
        "System is showing {} errors in {} component",
        "Performance degradation detected in {} service",
        "Security alert: {} detected in {} system",
        "Monitoring shows {} issues with {} infrastructure"
    ]
    
    template = draw(st.sampled_from(templates))
    issue_type = draw(st.sampled_from(["timeout", "connection", "authentication", "performance", "error"]))
    component = draw(st.sampled_from(["database", "api", "frontend", "backend", "network"]))
    
    return template.format(issue_type, component)


@st.composite
def severity_levels(draw):
    """Generate valid severity levels."""
    return draw(st.sampled_from(["critical", "high", "medium", "low"]))


@st.composite
def incident_sources(draw):
    """Generate valid incident sources."""
    return draw(st.sampled_from(["monitoring", "user_report", "api", "chat"]))


@st.composite
def affected_systems(draw):
    """Generate lists of affected systems."""
    systems = ["database", "api", "frontend", "backend", "network", "auth", "cache", "queue"]
    return draw(st.lists(st.sampled_from(systems), min_size=1, max_size=4, unique=True))


@st.composite
def severity_indicators(draw):
    """Generate severity indicator keywords."""
    indicators = [
        "critical", "urgent", "down", "outage", "timeout", "error", "slow", 
        "degraded", "failing", "warning", "issue", "minor", "cosmetic"
    ]
    return draw(st.lists(st.sampled_from(indicators), min_size=0, max_size=3, unique=True))


@st.composite
def incident_reports(draw):
    """Generate valid incident reports for property-based testing."""
    return IncidentReport(
        id=f"INC-{draw(st.text(alphabet='ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', min_size=8, max_size=8))}",
        title=draw(incident_titles()),
        description=draw(incident_descriptions()),
        source=draw(incident_sources()),
        timestamp=draw(st.datetimes(min_value=datetime(2024, 1, 1))).replace(tzinfo=timezone.utc),
        reporter=draw(st.text(min_size=3, max_size=20)),
        affected_systems=draw(affected_systems()),
        error_logs=draw(st.one_of(st.none(), st.text(min_size=10, max_size=200))),
        metrics_data=draw(st.one_of(st.none(), st.dictionaries(st.text(), st.integers()))),
        severity_indicators=draw(severity_indicators())
    )


@st.composite
def incidents(draw):
    """Generate incident objects for property-based testing."""
    report = draw(incident_reports())
    return Incident(report)


@st.composite
def team_names(draw):
    """Generate valid team names."""
    return draw(st.sampled_from(["SRE", "Backend", "Frontend", "Infrastructure", "Security", "Database"]))


@st.composite
def incident_types(draw):
    """Generate incident types for team capability testing."""
    return draw(st.sampled_from([
        "outage", "performance", "security", "database", "api", "network", 
        "infrastructure", "deployment", "monitoring", "authentication"
    ]))


# Test data generators
def generate_test_incident_data() -> Dict[str, Any]:
    """Generate test incident data."""
    return {
        "title": "Test API Timeout Issue",
        "description": "API endpoints are responding slowly",
        "source": "monitoring",
        "reporter": "test-system",
        "affected_systems": ["api", "database"],
        "error_logs": "Timeout after 30 seconds",
        "severity_indicators": ["timeout", "slow"]
    }


def generate_security_incident_data() -> Dict[str, Any]:
    """Generate security incident test data."""
    return {
        "title": "Suspicious Login Activity",
        "description": "Multiple failed login attempts detected from unusual IP addresses",
        "source": "security_monitoring",
        "reporter": "security-system",
        "affected_systems": ["authentication", "user_accounts"],
        "error_logs": "Failed login attempts: 50+ in 5 minutes",
        "severity_indicators": ["security", "suspicious", "authentication"]
    }


def generate_critical_incident_data() -> Dict[str, Any]:
    """Generate critical incident test data."""
    return {
        "title": "Production Database Outage",
        "description": "Primary database cluster is completely down",
        "source": "monitoring",
        "reporter": "monitoring-system",
        "affected_systems": ["database", "api", "frontend", "backend"],
        "error_logs": "Connection refused to database cluster",
        "severity_indicators": ["critical", "down", "outage", "production"]
    }