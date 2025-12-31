"""Tests for the core incident agent workflow."""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch

from src.incident_agent.incident_agent import (
    incident_agent, 
    process_incident,
    triage_incident,
    route_to_team,
    coordinate_response
)
from src.incident_agent.schemas import IncidentState


class TestIncidentAgentWorkflow:
    """Test cases for the incident agent workflow."""
    
    def test_process_incident_basic_flow(self):
        """Test basic incident processing flow."""
        incident_data = {
            "id": "TEST-001",
            "title": "Database connection timeout",
            "description": "Users reporting slow page loads",
            "source": "monitoring",
            "timestamp": datetime.now().isoformat(),
            "reporter": "monitoring-system",
            "affected_systems": ["database", "api"],
            "error_logs": "Connection timeout after 30 seconds",
            "severity_indicators": ["timeout", "performance"]
        }
        
        result = process_incident(incident_data)
        
        # Verify basic structure
        assert "incident_id" in result
        assert "severity" in result
        assert "assigned_teams" in result
        assert "suggested_actions" in result
        assert "status" in result
        
        # Verify teams were assigned
        assert len(result["assigned_teams"]) > 0
        
        # Verify actions were suggested
        assert len(result["suggested_actions"]) > 0
        
        # Verify status progression
        assert result["status"] in ["open", "in_progress"]
    
    def test_process_incident_with_security_indicators(self):
        """Test incident processing with security indicators."""
        incident_data = {
            "id": "SEC-001",
            "title": "Unauthorized access detected",
            "description": "Multiple failed login attempts from suspicious IP",
            "source": "security",
            "timestamp": datetime.now().isoformat(),
            "reporter": "security-monitor",
            "affected_systems": ["auth", "api"],
            "error_logs": "Failed authentication attempts",
            "severity_indicators": ["security", "unauthorized", "breach"]
        }
        
        result = process_incident(incident_data)
        
        # Security incidents should be escalated
        assert result["escalation_needed"] == True
        
        # Should have immediate notifications for security
        if result.get("notifications"):
            assert any(notif["urgency"] == "immediate" for notif in result["notifications"])
    
    def test_process_incident_with_multiple_systems(self):
        """Test incident processing affecting multiple systems."""
        incident_data = {
            "id": "MULTI-001",
            "title": "Service degradation across platform",
            "description": "Multiple services showing performance issues",
            "source": "monitoring",
            "timestamp": datetime.now().isoformat(),
            "reporter": "monitoring-system",
            "affected_systems": ["database", "api", "frontend", "infrastructure"],
            "error_logs": "High response times across services",
            "severity_indicators": ["performance", "degradation", "widespread"]
        }
        
        result = process_incident(incident_data)
        
        # Multiple systems should result in multiple team assignments
        assert len(result["assigned_teams"]) >= 2
        
        # Should have comprehensive action suggestions
        assert len(result["suggested_actions"]) >= 4
    
    def test_workflow_state_transitions(self):
        """Test that workflow state transitions work correctly."""
        initial_state = {
            "incident_input": {
                "id": "STATE-001",
                "title": "Test state transitions",
                "description": "Testing workflow state management",
                "source": "api",
                "timestamp": datetime.now().isoformat(),
                "reporter": "test-system",
                "affected_systems": ["api"],
                "severity_indicators": ["test"]
            }
        }
        
        # Test the full workflow
        result = incident_agent.invoke(initial_state)
        
        # Verify final state has all required fields
        assert "incident_id" in result
        assert "severity_classification" in result
        assert "team_assignment" in result
        assert "suggested_actions" in result
        assert "resolution_status" in result
        assert "created_at" in result
        assert "updated_at" in result
    
    def test_empty_incident_handling(self):
        """Test handling of minimal incident data."""
        minimal_incident = {
            "id": "MIN-001",
            "title": "Minimal incident",
            "description": "Basic incident with minimal data",
            "source": "api",
            "timestamp": datetime.now().isoformat(),
            "reporter": "test",
            "affected_systems": [],
            "severity_indicators": []
        }
        
        result = process_incident(minimal_incident)
        
        # Should still process successfully with fallbacks
        assert result["incident_id"] is not None
        assert result["severity"] is not None
        assert len(result["assigned_teams"]) > 0  # Should fallback to SRE
        assert len(result["suggested_actions"]) > 0  # Should have basic actions
    
    def test_team_assignment_logic(self):
        """Test team assignment based on affected systems."""
        test_cases = [
            {
                "systems": ["database"],
                "expected_team": "Backend"
            },
            {
                "systems": ["infrastructure"],
                "expected_team": "Infrastructure"
            },
            {
                "systems": ["security", "auth"],
                "expected_team": "Security"
            },
            {
                "systems": ["unknown-system"],
                "expected_team": "SRE"  # Fallback
            }
        ]
        
        for case in test_cases:
            incident_data = {
                "id": f"TEAM-{case['systems'][0].upper()}",
                "title": f"Test {case['systems'][0]} incident",
                "description": "Testing team assignment",
                "source": "api",
                "timestamp": datetime.now().isoformat(),
                "reporter": "test",
                "affected_systems": case["systems"],
                "severity_indicators": ["test"]
            }
            
            result = process_incident(incident_data)
            
            # Check if expected team is assigned (may have additional teams)
            assert case["expected_team"] in result["assigned_teams"], \
                f"Expected {case['expected_team']} for systems {case['systems']}, got {result['assigned_teams']}"
    
    def test_suggested_actions_generation(self):
        """Test that appropriate actions are suggested based on incident type."""
        # Critical incident should have immediate actions
        critical_incident = {
            "id": "CRIT-001",
            "title": "Complete service outage",
            "description": "All services are down",
            "source": "monitoring",
            "timestamp": datetime.now().isoformat(),
            "reporter": "monitoring",
            "affected_systems": ["api", "database", "frontend"],
            "severity_indicators": ["outage", "critical", "down"]
        }
        
        result = process_incident(critical_incident)
        
        # Should have escalation-related actions for critical incidents
        actions_text = " ".join(result["suggested_actions"]).lower()
        assert any(keyword in actions_text for keyword in ["immediate", "notify", "escalate", "war room"])
        
        # Should have diagnostic actions
        assert any(keyword in actions_text for keyword in ["monitor", "dashboard", "logs", "check"])


class TestWorkflowNodes:
    """Test individual workflow nodes."""
    
    def test_triage_incident_node(self):
        """Test the triage incident node."""
        state = IncidentState(
            incident_input={
                "id": "TRIAGE-001",
                "title": "Test triage",
                "description": "Testing triage node",
                "source": "test",
                "timestamp": datetime.now().isoformat(),
                "reporter": "test",
                "affected_systems": ["api"],
                "severity_indicators": ["test"]
            },
            messages=[]
        )
        
        # Mock the triage router to avoid LLM calls
        with patch('src.incident_agent.incident_agent.triage_router') as mock_router:
            mock_classification = Mock()
            mock_classification.severity = "medium"
            mock_classification.security_incident = False
            mock_classification.affected_systems = ["api"]
            
            mock_incident = Mock()
            mock_incident.report.id = "TRIAGE-001"
            mock_incident.created_at = datetime.now()
            
            mock_router.classify_severity.return_value = mock_classification
            mock_router.create_incident_from_classification.return_value = mock_incident
            mock_router.should_escalate_immediately.return_value = False
            
            command = triage_incident(state)
            
            assert command.goto == "route_to_team"
            assert "incident_id" in command.update
            assert "severity_classification" in command.update
    
    def test_route_to_team_node(self):
        """Test the route to team node."""
        state = IncidentState(
            incident_input={
                "affected_systems": ["database"],
                "title": "Database issue"
            },
            severity_classification="high",
            messages=[]
        )
        
        command = route_to_team(state)
        
        assert command.goto == "coordinate_response"
        assert "team_assignment" in command.update
        assert len(command.update["team_assignment"]) > 0
    
    def test_coordinate_response_node(self):
        """Test the coordinate response node."""
        state = IncidentState(
            incident_input={
                "title": "Test coordination",
                "affected_systems": ["api"]
            },
            severity_classification="medium",
            team_assignment=["Backend"],
            messages=[]
        )
        
        command = coordinate_response(state)
        
        assert command.goto == "__end__"
        assert "suggested_actions" in command.update
        assert "resolution_status" in command.update
        assert len(command.update["suggested_actions"]) > 0
        assert command.update["resolution_status"] == "in_progress"


if __name__ == "__main__":
    # Run a quick test
    test_workflow = TestIncidentAgentWorkflow()
    test_workflow.test_process_incident_basic_flow()
    print("✅ Basic workflow test passed!")