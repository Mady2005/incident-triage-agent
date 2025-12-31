"""Tests for incident agent models."""

import pytest
from datetime import datetime, timezone
from hypothesis import given, strategies as st, settings, HealthCheck

from src.incident_agent.models.incident import Incident, IncidentSeverity, IncidentStatus
from src.incident_agent.models.team import ResponseTeam, TeamRegistry, TeamCapability, TeamType
from src.incident_agent.schemas import TeamAssignment, ResolutionAction
from .conftest import incidents, incident_reports, severity_levels, team_names, incident_types


class TestIncident:
    """Test incident model functionality."""
    
    def test_incident_creation(self, sample_incident):
        """Test basic incident creation."""
        assert sample_incident.report.id == "INC-TEST001"
        assert sample_incident.status == IncidentStatus.OPEN
        assert sample_incident.severity is None
        assert len(sample_incident.team_assignments) == 0
        assert sample_incident.priority_score == 0
    
    def test_set_severity(self, sample_incident):
        """Test setting incident severity."""
        sample_incident.set_severity("high", "Database timeouts indicate high severity")
        
        assert sample_incident.severity == IncidentSeverity.HIGH
        assert sample_incident.priority_score > 0
        assert len(sample_incident.status_updates) == 1
        assert sample_incident.status_updates[0]["action"] == "severity_set"
    
    def test_assign_team(self, sample_incident):
        """Test team assignment."""
        assignment = TeamAssignment(
            team_name="SRE",
            assignment_reason="Database expertise",
            priority=1,
            escalation_path=["Infrastructure"],
            estimated_response_time=15
        )
        
        sample_incident.assign_team(assignment)
        
        assert len(sample_incident.team_assignments) == 1
        assert sample_incident.get_primary_team() == "SRE"
        assert "SRE" in sample_incident.get_assigned_teams()
    
    def test_escalation(self, sample_incident):
        """Test incident escalation."""
        sample_incident.escalate("No response from primary team", "Infrastructure")
        
        assert sample_incident.escalation_needed is True
        assert len(sample_incident.escalation_history) == 1
        assert sample_incident.escalation_history[0]["reason"] == "No response from primary team"
    
    def test_security_incident_marking(self, sample_incident):
        """Test marking incident as security-related."""
        sample_incident.set_severity("high")
        original_score = sample_incident.priority_score
        
        sample_incident.mark_as_security_incident()
        
        assert sample_incident.is_security_incident is True
        assert sample_incident.priority_score > original_score  # Security multiplier applied
    
    @given(incidents(), severity_levels())
    @settings(suppress_health_check=[HealthCheck.too_slow])
    def test_severity_setting_property(self, incident, severity):
        """Property test: Setting severity should always update priority score."""
        incident.set_severity(severity)
        
        assert incident.severity.value == severity
        assert incident.priority_score > 0
        assert len(incident.status_updates) >= 1
    
    @given(incidents())
    def test_status_updates_tracking(self, incident):
        """Property test: All incident changes should be tracked in status updates."""
        initial_updates = len(incident.status_updates)
        
        incident.set_severity("medium")
        incident.update_status("in_progress")
        
        assert len(incident.status_updates) == initial_updates + 2
        assert any(update["action"] == "severity_set" for update in incident.status_updates)
        assert any(update["action"] == "status_updated" for update in incident.status_updates)


class TestResponseTeam:
    """Test response team model."""
    
    def test_team_creation(self):
        """Test basic team creation."""
        capabilities = [
            TeamCapability("database", 4, 15),
            TeamCapability("api", 3, 20)
        ]
        
        team = ResponseTeam(
            name="Backend",
            team_type=TeamType.BACKEND,
            capabilities=capabilities,
            escalation_path=["SRE", "Infrastructure"]
        )
        
        assert team.name == "Backend"
        assert team.team_type == TeamType.BACKEND
        assert len(team.capabilities) == 2
        assert team.can_handle_incident_type("database")
        assert team.get_expertise_level("database") == 4
    
    def test_incident_assignment(self):
        """Test incident assignment to team."""
        team = ResponseTeam(
            name="SRE",
            team_type=TeamType.SRE,
            capabilities=[],
            escalation_path=[]
        )
        
        team.assign_incident("INC-001")
        team.assign_incident("INC-002")
        
        assert len(team.current_incidents) == 2
        assert team.workload_score == 2
        assert "INC-001" in team.current_incidents
    
    def test_incident_resolution(self):
        """Test incident resolution."""
        team = ResponseTeam(
            name="SRE",
            team_type=TeamType.SRE,
            capabilities=[],
            escalation_path=[]
        )
        
        team.assign_incident("INC-001")
        team.resolve_incident("INC-001")
        
        assert len(team.current_incidents) == 0
        assert team.workload_score == 0
    
    @given(
        team_names(),
        incident_types(),
        st.integers(min_value=1, max_value=5),
        st.integers(min_value=5, max_value=60)
    )
    def test_capability_handling(self, team_name, incident_type, expertise, response_time):
        """Property test: Teams should correctly report their capabilities."""
        capability = TeamCapability(incident_type, expertise, response_time)
        team = ResponseTeam(
            name=team_name,
            team_type=TeamType.SRE,
            capabilities=[capability],
            escalation_path=[]
        )
        
        assert team.can_handle_incident_type(incident_type)
        assert team.get_expertise_level(incident_type) == expertise
        assert team.get_estimated_response_time(incident_type) == response_time
        assert not team.can_handle_incident_type("unknown_type")


class TestTeamRegistry:
    """Test team registry functionality."""
    
    def test_registry_initialization(self, team_registry):
        """Test team registry initialization with default teams."""
        assert len(team_registry.teams) >= 4  # At least SRE, Backend, Security, Infrastructure
        assert team_registry.get_team("SRE") is not None
        assert team_registry.get_team("Security") is not None
    
    def test_team_registration(self, team_registry):
        """Test registering new teams."""
        new_team = ResponseTeam(
            name="TestTeam",
            team_type=TeamType.BACKEND,
            capabilities=[],
            escalation_path=[]
        )
        
        team_registry.register_team(new_team)
        
        assert team_registry.get_team("TestTeam") is not None
        assert "TestTeam" in team_registry.list_all_teams()
    
    def test_best_team_finding(self, team_registry):
        """Test finding best team for incident type."""
        best_team = team_registry.find_best_team_for_incident("security")
        
        assert best_team is not None
        assert best_team.can_handle_incident_type("security") or best_team.name == "SRE"
    
    @given(incident_types())
    def test_team_finding_property(self, incident_type):
        """Property test: Registry should always find a team for any incident type."""
        # Create registry inside test to avoid fixture issues with Hypothesis
        from src.incident_agent.models.team import TeamRegistry
        team_registry = TeamRegistry()
        
        team = team_registry.find_best_team_for_incident(incident_type)
        
        assert team is not None
        # Either the team can handle the incident type, or it's the SRE fallback
        assert team.can_handle_incident_type(incident_type) or team.name == "SRE"