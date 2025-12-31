"""Tests for incident management tools."""

import pytest
from datetime import datetime
from src.incident_agent.tools.incident_tools import (
    create_incident_tool,
    update_incident_tool,
    get_incident_status_tool,
    list_incidents_tool,
    get_incident_timeline_tool,
    clear_incidents_store
)


class TestIncidentTools:
    """Test suite for incident management tools."""
    
    def setup_method(self):
        """Clear incidents store before each test."""
        clear_incidents_store()
    
    def test_create_incident_tool(self):
        """Test incident creation tool."""
        result = create_incident_tool.invoke({
            "title": "Test incident",
            "description": "Test description",
            "severity": "high",
            "affected_systems": ["api", "database"],
            "reporter": "test-user",
            "source": "manual"
        })
        
        assert result["success"] is True
        assert "incident_id" in result
        assert result["incident"]["title"] == "Test incident"
        assert result["incident"]["severity"] == "high"
        assert result["incident"]["affected_systems"] == ["api", "database"]
        assert result["incident"]["status"] == "open"
        assert len(result["incident"]["timeline"]) == 1
    
    def test_update_incident_tool(self):
        """Test incident update tool."""
        # Create incident first
        create_result = create_incident_tool.invoke({
            "title": "Test incident",
            "description": "Test description", 
            "severity": "medium",
            "affected_systems": ["api"],
            "reporter": "test-user"
        })
        
        incident_id = create_result["incident_id"]
        
        # Update incident
        update_result = update_incident_tool.invoke({
            "incident_id": incident_id,
            "status": "in_progress",
            "severity": "high",
            "assigned_teams": ["sre", "backend"],
            "resolution_notes": "Investigation started",
            "add_timeline_event": "Team assigned and investigation begun"
        })
        
        assert update_result["success"] is True
        assert update_result["incident_id"] == incident_id
        assert "status: open → in_progress" in update_result["changes"]
        assert "severity: medium → high" in update_result["changes"]
        assert update_result["incident"]["assigned_teams"] == ["sre", "backend"]
        assert update_result["incident"]["resolution_notes"] == "Investigation started"
        
        # Check timeline was updated
        timeline = update_result["incident"]["timeline"]
        assert len(timeline) >= 4  # creation + status + severity + teams + custom event
    
    def test_update_nonexistent_incident(self):
        """Test updating non-existent incident."""
        result = update_incident_tool.invoke({
            "incident_id": "nonexistent",
            "status": "resolved"
        })
        
        assert result["success"] is False
        assert "not found" in result["error"]
    
    def test_get_incident_status_tool(self):
        """Test incident status retrieval."""
        # Create incident
        create_result = create_incident_tool.invoke({
            "title": "Status test incident",
            "description": "Testing status retrieval",
            "severity": "critical",
            "affected_systems": ["database", "api", "auth"],
            "reporter": "monitoring"
        })
        
        incident_id = create_result["incident_id"]
        
        # Get status
        status_result = get_incident_status_tool.invoke({
            "incident_id": incident_id
        })
        
        assert status_result["success"] is True
        assert status_result["incident_id"] == incident_id
        assert status_result["status"] == "open"
        assert status_result["severity"] == "critical"
        assert status_result["title"] == "Status test incident"
        assert status_result["affected_systems"] == ["database", "api", "auth"]
        assert "age_hours" in status_result
        assert status_result["timeline_count"] == 1
    
    def test_get_status_nonexistent_incident(self):
        """Test getting status of non-existent incident."""
        result = get_incident_status_tool.invoke({
            "incident_id": "nonexistent"
        })
        
        assert result["success"] is False
        assert "not found" in result["error"]
    
    def test_list_incidents_tool(self):
        """Test incident listing tool."""
        # Create multiple incidents
        incidents_data = [
            {"title": "Critical DB issue", "severity": "critical", "status": "open"},
            {"title": "API slowdown", "severity": "high", "status": "in_progress"},
            {"title": "Minor UI bug", "severity": "low", "status": "resolved"}
        ]
        
        created_ids = []
        for incident_data in incidents_data:
            create_result = create_incident_tool.invoke({
                "title": incident_data["title"],
                "description": "Test description",
                "severity": incident_data["severity"],
                "affected_systems": ["test"],
                "reporter": "test"
            })
            created_ids.append(create_result["incident_id"])
            
            # Update status if needed
            if incident_data["status"] != "open":
                update_incident_tool.invoke({
                    "incident_id": create_result["incident_id"],
                    "status": incident_data["status"]
                })
        
        # Test listing all incidents
        list_result = list_incidents_tool.invoke({
            "limit": 10
        })
        
        assert list_result["success"] is True
        assert list_result["total_found"] == 3
        assert len(list_result["incidents"]) == 3
        
        # Test filtering by severity
        critical_result = list_incidents_tool.invoke({
            "severity_filter": "critical",
            "limit": 10
        })
        
        assert critical_result["success"] is True
        assert critical_result["total_found"] == 1
        assert critical_result["incidents"][0]["severity"] == "critical"
        
        # Test filtering by status
        resolved_result = list_incidents_tool.invoke({
            "status_filter": "resolved",
            "limit": 10
        })
        
        assert resolved_result["success"] is True
        assert resolved_result["total_found"] == 1
        assert resolved_result["incidents"][0]["status"] == "resolved"
        
        # Test limit
        limited_result = list_incidents_tool.invoke({
            "limit": 2
        })
        
        assert limited_result["success"] is True
        assert len(limited_result["incidents"]) == 2
    
    def test_get_incident_timeline_tool(self):
        """Test incident timeline retrieval."""
        # Create incident
        create_result = create_incident_tool.invoke({
            "title": "Timeline test",
            "description": "Testing timeline",
            "severity": "medium",
            "affected_systems": ["api"],
            "reporter": "test"
        })
        
        incident_id = create_result["incident_id"]
        
        # Add some timeline events
        update_incident_tool.invoke({
            "incident_id": incident_id,
            "status": "in_progress",
            "add_timeline_event": "Investigation started"
        })
        
        update_incident_tool.invoke({
            "incident_id": incident_id,
            "assigned_teams": ["sre"],
            "add_timeline_event": "SRE team engaged"
        })
        
        # Get timeline
        timeline_result = get_incident_timeline_tool.invoke({
            "incident_id": incident_id
        })
        
        assert timeline_result["success"] is True
        assert timeline_result["incident_id"] == incident_id
        assert timeline_result["title"] == "Timeline test"
        assert timeline_result["timeline_count"] >= 4  # creation + status + teams + 2 custom events
        
        # Check timeline structure
        timeline = timeline_result["timeline"]
        assert all("timestamp" in event for event in timeline)
        assert all("event" in event for event in timeline)
        assert all("details" in event for event in timeline)
    
    def test_incident_age_calculation(self):
        """Test that incident age is calculated correctly."""
        # Create incident
        create_result = create_incident_tool.invoke({
            "title": "Age test",
            "description": "Testing age calculation",
            "severity": "low",
            "affected_systems": ["test"],
            "reporter": "test"
        })
        
        incident_id = create_result["incident_id"]
        
        # Get status immediately
        status_result = get_incident_status_tool.invoke({
            "incident_id": incident_id
        })
        
        assert status_result["success"] is True
        assert status_result["age_hours"] >= 0
        assert status_result["age_hours"] < 1  # Should be very recent
    
    def test_incident_data_persistence(self):
        """Test that incident data persists across operations."""
        # Create incident
        create_result = create_incident_tool.invoke({
            "title": "Persistence test",
            "description": "Testing data persistence",
            "severity": "high",
            "affected_systems": ["api", "database"],
            "reporter": "test-user",
            "source": "monitoring"
        })
        
        incident_id = create_result["incident_id"]
        
        # Update incident multiple times
        update_incident_tool.invoke({
            "incident_id": incident_id,
            "status": "in_progress",
            "assigned_teams": ["sre"]
        })
        
        update_incident_tool.invoke({
            "incident_id": incident_id,
            "severity": "critical",
            "resolution_notes": "Escalated due to impact"
        })
        
        # Verify all data is preserved
        status_result = get_incident_status_tool.invoke({
            "incident_id": incident_id
        })
        
        assert status_result["success"] is True
        assert status_result["title"] == "Persistence test"
        assert status_result["status"] == "in_progress"
        assert status_result["severity"] == "critical"
        assert status_result["assigned_teams"] == ["sre"]
        assert status_result["affected_systems"] == ["api", "database"]
        
        # Check in list view
        list_result = list_incidents_tool.invoke({"limit": 10})
        incident_in_list = next(
            (inc for inc in list_result["incidents"] if inc["incident_id"] == incident_id),
            None
        )
        
        assert incident_in_list is not None
        assert incident_in_list["severity"] == "critical"
        assert incident_in_list["status"] == "in_progress"
        assert incident_in_list["assigned_teams"] == ["sre"]