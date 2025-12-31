"""Tests for incident agent utility functions."""

import pytest
from datetime import datetime, timezone
from hypothesis import given, strategies as st

from src.incident_agent.utils import (
    generate_incident_id, current_timestamp, parse_incident_data,
    extract_severity_keywords, extract_security_indicators,
    format_incident_summary, validate_team_assignment,
    calculate_incident_priority_score
)
from .conftest import incident_reports, severity_levels, team_names


class TestUtilityFunctions:
    """Test utility functions."""
    
    def test_generate_incident_id(self):
        """Test incident ID generation."""
        id1 = generate_incident_id()
        id2 = generate_incident_id()
        
        assert id1.startswith("INC-")
        assert id2.startswith("INC-")
        assert id1 != id2  # Should be unique
        assert len(id1) == 12  # INC- + 8 characters
    
    def test_current_timestamp(self):
        """Test current timestamp generation."""
        timestamp = current_timestamp()
        
        assert isinstance(timestamp, datetime)
        assert timestamp.tzinfo == timezone.utc
    
    def test_parse_incident_data(self):
        """Test parsing raw incident data."""
        raw_data = {
            "title": "API Timeout",
            "description": "API is timing out",
            "source": "monitoring",
            "reporter": "system",
            "affected_systems": "api,database",
            "severity_indicators": "timeout,slow"
        }
        
        incident = parse_incident_data(raw_data)
        
        assert incident.title == "API Timeout"
        assert incident.source == "monitoring"
        assert len(incident.affected_systems) == 2
        assert "api" in incident.affected_systems
        assert len(incident.severity_indicators) == 2
        assert "timeout" in incident.severity_indicators
    
    def test_extract_severity_keywords(self):
        """Test severity keyword extraction."""
        text = "The production database is down and critical services are failing"
        keywords = extract_severity_keywords(text)
        
        assert len(keywords) > 0
        assert any("critical" in keyword for keyword in keywords)
        assert any("down" in keyword for keyword in keywords)
    
    def test_extract_security_indicators(self):
        """Test security indicator extraction."""
        text = "Suspicious login attempts detected, possible security breach"
        indicators = extract_security_indicators(text)
        
        assert len(indicators) > 0
        assert "suspicious" in indicators
        assert "security" in indicators
        assert "breach" in indicators
    
    def test_validate_team_assignment(self):
        """Test team assignment validation."""
        available_teams = ["SRE", "Backend", "Security"]
        
        assert validate_team_assignment("SRE", available_teams) is True
        assert validate_team_assignment("InvalidTeam", available_teams) is False
    
    def test_calculate_incident_priority_score(self):
        """Test incident priority score calculation."""
        # Critical incident with multiple systems
        score1 = calculate_incident_priority_score("critical", 3, False)
        
        # Critical security incident
        score2 = calculate_incident_priority_score("critical", 3, True)
        
        # Low priority incident
        score3 = calculate_incident_priority_score("low", 1, False)
        
        assert score1 > score3  # Critical should be higher than low
        assert score2 > score1  # Security incidents get priority boost
        assert score1 == 3000   # 1000 * 3 systems * 1 (no security)
        assert score2 == 6000   # 1000 * 3 systems * 2 (security multiplier)
    
    @given(st.text(min_size=10))
    def test_severity_keyword_extraction_property(self, text):
        """Property test: Severity keyword extraction should always return a list."""
        keywords = extract_severity_keywords(text)
        
        assert isinstance(keywords, list)
        # All keywords should contain a colon (severity:keyword format)
        assert all(":" in keyword for keyword in keywords)
    
    @given(st.text(min_size=10))
    def test_security_indicator_extraction_property(self, text):
        """Property test: Security indicator extraction should always return a list."""
        indicators = extract_security_indicators(text)
        
        assert isinstance(indicators, list)
        # All indicators should be strings
        assert all(isinstance(indicator, str) for indicator in indicators)
    
    @given(
        severity_levels(),
        st.integers(min_value=1, max_value=10),
        st.booleans()
    )
    def test_priority_score_calculation_property(self, severity, system_count, is_security):
        """Property test: Priority score calculation should be consistent."""
        score = calculate_incident_priority_score(severity, system_count, is_security)
        
        assert score > 0
        assert isinstance(score, int)
        
        # Security incidents should have higher scores
        non_security_score = calculate_incident_priority_score(severity, system_count, False)
        if is_security:
            assert score >= non_security_score
    
    @given(incident_reports())
    def test_format_incident_summary_property(self, incident_report):
        """Property test: Incident summary formatting should always produce valid output."""
        summary = format_incident_summary(incident_report)
        
        assert isinstance(summary, str)
        assert len(summary) > 0
        assert incident_report.id in summary
        assert incident_report.title in summary
        assert incident_report.reporter in summary
    
    @given(
        team_names(),
        st.lists(team_names(), min_size=1, max_size=5, unique=True)
    )
    def test_team_validation_property(self, team, available_teams):
        """Property test: Team validation should work correctly."""
        is_valid = validate_team_assignment(team, available_teams)
        
        assert isinstance(is_valid, bool)
        assert is_valid == (team in available_teams)