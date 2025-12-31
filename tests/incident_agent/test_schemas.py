"""Tests for incident agent schemas and data models."""

import pytest
from datetime import datetime, timezone
from hypothesis import given, strategies as st

from src.incident_agent.schemas import (
    IncidentReport, TeamAssignment, ResolutionAction, IncidentState,
    SeverityClassificationSchema, TeamRoutingSchema, IncidentResponse
)
from .conftest import incident_reports, severity_levels, team_names


class TestIncidentReport:
    """Test incident report schema validation."""
    
    def test_incident_report_creation(self, sample_incident_report):
        """Test basic incident report creation."""
        assert sample_incident_report.id == "INC-TEST001"
        assert sample_incident_report.title == "Test Database Connection Issue"
        assert sample_incident_report.source == "monitoring"
        assert isinstance(sample_incident_report.timestamp, datetime)
        assert len(sample_incident_report.affected_systems) == 2
    
    @given(incident_reports())
    def test_incident_report_validation(self, incident_report):
        """Property test: All generated incident reports should be valid."""
        assert incident_report.id.startswith("INC-")
        assert len(incident_report.title) > 0
        assert incident_report.source in ["monitoring", "user_report", "api", "chat"]
        assert isinstance(incident_report.timestamp, datetime)
        assert len(incident_report.affected_systems) >= 1
        assert isinstance(incident_report.severity_indicators, list)


class TestTeamAssignment:
    """Test team assignment schema."""
    
    def test_team_assignment_creation(self):
        """Test team assignment creation."""
        assignment = TeamAssignment(
            team_name="SRE",
            assignment_reason="Database expertise required",
            priority=1,
            escalation_path=["Infrastructure", "Backend"],
            estimated_response_time=15
        )
        
        assert assignment.team_name == "SRE"
        assert assignment.priority == 1
        assert len(assignment.escalation_path) == 2
        assert assignment.estimated_response_time == 15
    
    @given(team_names(), st.text(min_size=5), st.integers(min_value=1, max_value=5))
    def test_team_assignment_validation(self, team_name, reason, priority):
        """Property test: Team assignments should validate correctly."""
        assignment = TeamAssignment(
            team_name=team_name,
            assignment_reason=reason,
            priority=priority,
            escalation_path=[],
            estimated_response_time=30
        )
        
        assert assignment.team_name in ["SRE", "Backend", "Frontend", "Infrastructure", "Security", "Database"]
        assert len(assignment.assignment_reason) >= 5
        assert 1 <= assignment.priority <= 5


class TestResolutionAction:
    """Test resolution action schema."""
    
    def test_resolution_action_creation(self):
        """Test resolution action creation."""
        action = ResolutionAction(
            action_type="diagnostic",
            description="Check database connection pool status",
            priority=1,
            estimated_duration=10,
            required_permissions=["database_read"],
            runbook_reference="DB-CONN-001"
        )
        
        assert action.action_type == "diagnostic"
        assert action.priority == 1
        assert len(action.required_permissions) == 1
        assert action.runbook_reference == "DB-CONN-001"
    
    @given(
        st.sampled_from(["diagnostic", "fix", "communication", "escalation"]),
        st.text(min_size=10),
        st.integers(min_value=1, max_value=5),
        st.integers(min_value=5, max_value=120)
    )
    def test_resolution_action_validation(self, action_type, description, priority, duration):
        """Property test: Resolution actions should validate correctly."""
        action = ResolutionAction(
            action_type=action_type,
            description=description,
            priority=priority,
            estimated_duration=duration
        )
        
        assert action.action_type in ["diagnostic", "fix", "communication", "escalation"]
        assert len(action.description) >= 10
        assert 1 <= action.priority <= 5
        assert 5 <= action.estimated_duration <= 120


class TestSeverityClassificationSchema:
    """Test severity classification schema."""
    
    @given(
        st.text(min_size=20),
        severity_levels(),
        st.booleans(),
        st.lists(st.text(min_size=3), min_size=1, max_size=5)
    )
    def test_severity_classification_validation(self, reasoning, severity, is_security, systems):
        """Property test: Severity classifications should validate correctly."""
        classification = SeverityClassificationSchema(
            reasoning=reasoning,
            severity=severity,
            security_incident=is_security,
            affected_systems=systems
        )
        
        assert len(classification.reasoning) >= 20
        assert classification.severity in ["critical", "high", "medium", "low"]
        assert isinstance(classification.security_incident, bool)
        assert len(classification.affected_systems) >= 1


class TestTeamRoutingSchema:
    """Test team routing schema."""
    
    @given(
        st.text(min_size=15),
        team_names(),
        st.lists(team_names(), max_size=3),
        st.booleans()
    )
    def test_team_routing_validation(self, reasoning, primary_team, secondary_teams, escalation):
        """Property test: Team routing should validate correctly."""
        routing = TeamRoutingSchema(
            reasoning=reasoning,
            primary_team=primary_team,
            secondary_teams=secondary_teams,
            escalation_needed=escalation
        )
        
        assert len(routing.reasoning) >= 15
        assert routing.primary_team in ["SRE", "Backend", "Frontend", "Infrastructure", "Security", "Database"]
        assert isinstance(routing.escalation_needed, bool)
        assert len(routing.secondary_teams) <= 3