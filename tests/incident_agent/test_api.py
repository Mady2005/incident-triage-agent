"""Tests for the FastAPI incident agent API."""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime

from src.incident_agent.api.main import app


class TestIncidentAPI:
    """Test cases for the incident API endpoints."""
    
    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)
    
    def test_health_check(self):
        """Test health check endpoint."""
        response = self.client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert data["version"] == "1.0.0"
    
    def test_create_incident_basic(self):
        """Test basic incident creation."""
        incident_data = {
            "title": "Test incident",
            "description": "This is a test incident",
            "source": "api",
            "reporter": "test-user",
            "affected_systems": ["api"],
            "severity_indicators": ["test"]
        }
        
        response = self.client.post("/incidents/", json=incident_data)
        
        assert response.status_code == 201
        data = response.json()
        
        # Verify response structure
        assert "incident_id" in data
        assert data["status"] == "created"
        assert data["message"] == "Incident created and processed successfully"
        assert data["severity"] in ["critical", "high", "medium", "low"]
        assert isinstance(data["assigned_teams"], list)
        assert len(data["assigned_teams"]) > 0
        assert isinstance(data["suggested_actions"], list)
        assert len(data["suggested_actions"]) > 0
        assert isinstance(data["escalation_needed"], bool)
    
    def test_create_critical_incident(self):
        """Test creation of critical incident."""
        incident_data = {
            "title": "Critical database outage",
            "description": "Complete database failure affecting all services",
            "source": "monitoring",
            "reporter": "monitoring-system",
            "affected_systems": ["database", "api"],
            "error_logs": "Connection timeout",
            "severity_indicators": ["critical", "outage", "down"]
        }
        
        response = self.client.post("/incidents/", json=incident_data)
        
        assert response.status_code == 201
        data = response.json()
        
        # Critical incidents should be escalated
        assert data["escalation_needed"] == True
        
        # Should have immediate response actions
        actions_text = " ".join(data["suggested_actions"]).lower()
        assert any(keyword in actions_text for keyword in ["immediate", "notify", "war room"])
    
    def test_create_security_incident(self):
        """Test creation of security incident."""
        incident_data = {
            "title": "Unauthorized access detected",
            "description": "Suspicious login attempts",
            "source": "monitoring",
            "reporter": "security-monitor",
            "affected_systems": ["auth"],
            "severity_indicators": ["security", "unauthorized"]
        }
        
        response = self.client.post("/incidents/", json=incident_data)
        
        assert response.status_code == 201
        data = response.json()
        
        # Security incidents should include Security team
        assert "Security" in data["assigned_teams"]
        assert data["escalation_needed"] == True
    
    def test_get_incident(self):
        """Test retrieving incident by ID."""
        # First create an incident
        incident_data = {
            "title": "Test retrieval",
            "description": "Testing incident retrieval",
            "source": "api",
            "reporter": "test-user",
            "affected_systems": ["api"],
            "severity_indicators": ["test"]
        }
        
        create_response = self.client.post("/incidents/", json=incident_data)
        incident_id = create_response.json()["incident_id"]
        
        # Now retrieve it
        response = self.client.get(f"/incidents/{incident_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["incident_id"] == incident_id
        assert data["title"] == incident_data["title"]
        assert data["description"] == incident_data["description"]
        assert "severity" in data
        assert "assigned_teams" in data
        assert "suggested_actions" in data
    
    def test_get_nonexistent_incident(self):
        """Test retrieving non-existent incident."""
        response = self.client.get("/incidents/NONEXISTENT-001")
        
        assert response.status_code == 404
        assert "not found" in response.json()["error"].lower()
    
    def test_list_incidents(self):
        """Test listing incidents."""
        # Create a few incidents first
        incidents_data = [
            {
                "title": "Incident 1",
                "description": "First test incident",
                "source": "api",
                "reporter": "test-user",
                "affected_systems": ["api"],
                "severity_indicators": ["test"]
            },
            {
                "title": "Incident 2", 
                "description": "Second test incident",
                "source": "monitoring",
                "reporter": "monitoring",
                "affected_systems": ["database"],
                "severity_indicators": ["performance"]
            }
        ]
        
        created_ids = []
        for incident_data in incidents_data:
            response = self.client.post("/incidents/", json=incident_data)
            created_ids.append(response.json()["incident_id"])
        
        # List all incidents
        response = self.client.get("/incidents/")
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        assert len(data) >= 2  # At least the ones we created
        
        # Verify structure of listed incidents
        for incident in data:
            assert "incident_id" in incident
            assert "title" in incident
            assert "severity" in incident
            assert "assigned_teams" in incident
    
    def test_list_incidents_with_filters(self):
        """Test listing incidents with filters."""
        # Create incident with known characteristics
        incident_data = {
            "title": "Backend API issue",
            "description": "API performance problem",
            "source": "monitoring",
            "reporter": "monitoring",
            "affected_systems": ["api"],
            "severity_indicators": ["performance"]
        }
        
        create_response = self.client.post("/incidents/", json=incident_data)
        created_incident = create_response.json()
        
        # Test team filter
        response = self.client.get("/incidents/?team_filter=Backend")
        assert response.status_code == 200
        
        # Should include our incident if Backend team was assigned
        if "Backend" in created_incident["assigned_teams"]:
            incident_ids = [inc["incident_id"] for inc in response.json()]
            assert created_incident["incident_id"] in incident_ids
    
    def test_update_incident_severity(self):
        """Test updating incident severity."""
        # Create incident
        incident_data = {
            "title": "Test severity update",
            "description": "Testing severity updates",
            "source": "api",
            "reporter": "test-user",
            "affected_systems": ["api"],
            "severity_indicators": ["test"]
        }
        
        create_response = self.client.post("/incidents/", json=incident_data)
        incident_id = create_response.json()["incident_id"]
        original_severity = create_response.json()["severity"]
        
        # Update severity
        update_data = {
            "new_severity": "critical",
            "reason": "Impact assessment revealed critical business impact",
            "updated_by": "incident-commander"
        }
        
        response = self.client.put(f"/incidents/{incident_id}/severity", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["incident_id"] == incident_id
        assert data["old_severity"] == original_severity
        assert data["new_severity"] == "critical"
        assert data["reason"] == update_data["reason"]
        assert data["updated_by"] == update_data["updated_by"]
    
    def test_escalate_incident(self):
        """Test incident escalation."""
        # Create incident
        incident_data = {
            "title": "Test escalation",
            "description": "Testing escalation functionality",
            "source": "api",
            "reporter": "test-user",
            "affected_systems": ["api"],
            "severity_indicators": ["test"]
        }
        
        create_response = self.client.post("/incidents/", json=incident_data)
        incident_id = create_response.json()["incident_id"]
        
        # Escalate incident
        escalation_data = {
            "escalation_reason": "Initial response team unable to resolve",
            "target_team": "SRE",
            "urgency_level": "urgent",
            "additional_context": "Customer impact increasing"
        }
        
        response = self.client.post(f"/incidents/{incident_id}/escalate", json=escalation_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["incident_id"] == incident_id
        assert data["message"] == "Incident escalated successfully"
        assert data["escalation_reason"] == escalation_data["escalation_reason"]
        assert data["urgency_level"] == escalation_data["urgency_level"]
        assert data["target_team"] == escalation_data["target_team"]
    
    def test_get_incident_status(self):
        """Test getting incident status."""
        # Create incident
        incident_data = {
            "title": "Test status check",
            "description": "Testing status endpoint",
            "source": "api",
            "reporter": "test-user",
            "affected_systems": ["api"],
            "severity_indicators": ["test"]
        }
        
        create_response = self.client.post("/incidents/", json=incident_data)
        incident_id = create_response.json()["incident_id"]
        
        # Get status
        response = self.client.get(f"/incidents/{incident_id}/status")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["incident_id"] == incident_id
        assert "current_status" in data
        assert "severity" in data
        assert "assigned_teams" in data
        assert "progress_summary" in data
        assert "suggested_actions_count" in data
    
    def test_get_system_stats(self):
        """Test getting system statistics."""
        # Create a few incidents to generate stats
        incidents_data = [
            {
                "title": "Stats test 1",
                "description": "First stats test",
                "source": "api",
                "reporter": "test",
                "affected_systems": ["api"],
                "severity_indicators": ["test"]
            },
            {
                "title": "Critical stats test",
                "description": "Critical incident for stats",
                "source": "monitoring",
                "reporter": "monitoring",
                "affected_systems": ["database"],
                "severity_indicators": ["critical", "outage"]
            }
        ]
        
        for incident_data in incidents_data:
            self.client.post("/incidents/", json=incident_data)
        
        # Get stats
        response = self.client.get("/stats")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "total_incidents" in data
        assert "severity_distribution" in data
        assert "team_workload" in data
        assert "escalation_rate" in data
        assert data["total_incidents"] >= 2  # At least the ones we created
    
    def test_invalid_incident_data(self):
        """Test creating incident with invalid data."""
        # Missing required fields
        invalid_data = {
            "title": "Test incident"
            # Missing required fields like description, source, reporter
        }
        
        response = self.client.post("/incidents/", json=invalid_data)
        
        assert response.status_code == 422  # Validation error


if __name__ == "__main__":
    # Run a quick test
    test_api = TestIncidentAPI()
    test_api.setup_method()
    test_api.test_health_check()
    print("✅ Basic API test passed!")