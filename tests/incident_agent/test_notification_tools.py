"""Tests for notification tools."""

import pytest
from src.incident_agent.tools.notification_tools import (
    send_notification_tool,
    send_escalation_notification_tool,
    format_status_update_tool,
    send_status_broadcast_tool
)


class TestNotificationTools:
    """Test suite for notification tools."""
    
    def test_send_notification_tool(self):
        """Test basic notification sending."""
        incident_data = {
            "incident_id": "TEST-001",
            "title": "Test incident",
            "severity": "high",
            "status": "open",
            "assigned_teams": ["sre", "backend"],
            "affected_systems": ["api", "database"],
            "description": "Test incident description",
            "escalation_needed": False
        }
        
        result = send_notification_tool.invoke({
            "incident_id": "TEST-001",
            "message_type": "created",
            "incident_data": incident_data,
            "channels": ["#incidents", "#sre"],
            "urgent": False
        })
        
        assert result["success"] is True
        assert result["incident_id"] == "TEST-001"
        assert result["notification_type"] == "created"
        assert result["channels_notified"] == ["#incidents", "#sre"]
        assert result["urgent"] is False
        assert "timestamp" in result
    
    def test_send_notification_different_types(self):
        """Test different notification message types."""
        incident_data = {
            "incident_id": "TEST-002",
            "title": "Test incident",
            "severity": "critical",
            "status": "resolved",
            "assigned_teams": ["sre"],
            "affected_systems": ["api"],
            "description": "Test description",
            "resolution_notes": "Issue resolved by restarting service"
        }
        
        message_types = ["created", "updated", "escalated", "resolved"]
        
        for msg_type in message_types:
            result = send_notification_tool.invoke({
                "incident_id": "TEST-002",
                "message_type": msg_type,
                "incident_data": incident_data,
                "urgent": (msg_type == "escalated")
            })
            
            assert result["success"] is True
            assert result["notification_type"] == msg_type
            assert result["urgent"] == (msg_type == "escalated")
    
    def test_send_escalation_notification_tool(self):
        """Test escalation notification."""
        incident_data = {
            "incident_id": "TEST-003",
            "title": "Critical system failure",
            "severity": "critical",
            "status": "open",
            "assigned_teams": ["sre"],
            "affected_systems": ["database", "api"],
            "description": "Database cluster is down"
        }
        
        result = send_escalation_notification_tool.invoke({
            "incident_id": "TEST-003",
            "escalation_reason": "No response from primary team after 30 minutes",
            "target_team": "management",
            "incident_data": incident_data,
            "urgency_level": "critical"
        })
        
        assert result["success"] is True
        assert result["incident_id"] == "TEST-003"
        assert "escalation_details" in result
        
        escalation_details = result["escalation_details"]
        assert escalation_details["reason"] == "No response from primary team after 30 minutes"
        assert escalation_details["target_team"] == "management"
        assert escalation_details["urgency_level"] == "critical"
        assert "escalated_at" in escalation_details
    
    def test_format_status_update_technical(self):
        """Test technical status update formatting."""
        incident_data = {
            "incident_id": "TEST-004",
            "title": "API performance degradation",
            "severity": "high",
            "status": "in_progress",
            "assigned_teams": ["sre", "backend"],
            "affected_systems": ["api", "database"],
            "description": "API response times increased significantly",
            "suggested_actions": [
                "Check database query performance",
                "Review recent deployments",
                "Scale API instances"
            ],
            "timeline": [
                {
                    "timestamp": "2024-01-01T10:00:00Z",
                    "details": "Incident created"
                },
                {
                    "timestamp": "2024-01-01T10:05:00Z", 
                    "details": "Teams assigned"
                },
                {
                    "timestamp": "2024-01-01T10:10:00Z",
                    "details": "Investigation started"
                }
            ]
        }
        
        result = format_status_update_tool.invoke({
            "incident_id": "TEST-004",
            "incident_data": incident_data,
            "update_type": "progress",
            "audience": "technical"
        })
        
        assert result["success"] is True
        assert result["incident_id"] == "TEST-004"
        assert result["audience"] == "technical"
        assert result["update_type"] == "progress"
        
        message = result["formatted_message"]
        assert "TEST-004" in message
        assert "API performance degradation" in message
        assert "HIGH" in message
        assert "IN_PROGRESS" in message
        assert "sre, backend" in message
        assert "api, database" in message
        assert "Check database query performance" in message
        assert len(message) > 100  # Should be substantial
    
    def test_format_status_update_management(self):
        """Test management status update formatting."""
        incident_data = {
            "incident_id": "TEST-005",
            "title": "Service outage affecting customers",
            "severity": "critical",
            "status": "in_progress",
            "assigned_teams": ["sre", "management"],
            "affected_systems": ["frontend", "api", "database"],
            "description": "Complete service outage",
            "suggested_actions": [
                "Activate disaster recovery procedures",
                "Communicate with customers",
                "Engage additional resources"
            ]
        }
        
        result = format_status_update_tool.invoke({
            "incident_id": "TEST-005",
            "incident_data": incident_data,
            "update_type": "progress",
            "audience": "management"
        })
        
        assert result["success"] is True
        assert result["audience"] == "management"
        
        message = result["formatted_message"]
        assert "Executive Summary" in message
        assert "Business Impact" in message
        assert "Multiple systems affected" in message
        assert "Response Team" in message
        assert "Communication" in message
        assert "TEST-005" in message
    
    def test_format_status_update_customer(self):
        """Test customer status update formatting."""
        incident_data = {
            "incident_id": "TEST-006",
            "title": "Login service disruption",
            "severity": "high",
            "status": "in_progress",
            "assigned_teams": ["sre"],
            "affected_systems": ["auth", "api"],
            "description": "Users unable to log in"
        }
        
        result = format_status_update_tool.invoke({
            "incident_id": "TEST-006",
            "incident_data": incident_data,
            "update_type": "progress",
            "audience": "customer"
        })
        
        assert result["success"] is True
        assert result["audience"] == "customer"
        
        message = result["formatted_message"]
        assert "Service Status Update" in message
        assert "investigating" in message.lower()
        assert "engineering team" in message.lower()
        assert "apologize" in message.lower()
        assert "TEST-006" not in message  # Should not expose internal IDs
        assert "auth, api" in message  # Should show affected services
    
    def test_send_status_broadcast_tool(self):
        """Test status broadcast to multiple audiences."""
        incident_data = {
            "incident_id": "TEST-007",
            "title": "Database performance issues",
            "severity": "medium",
            "status": "in_progress",
            "assigned_teams": ["dba", "sre"],
            "affected_systems": ["database"],
            "description": "Database queries running slowly"
        }
        
        result = send_status_broadcast_tool.invoke({
            "incident_id": "TEST-007",
            "incident_data": incident_data,
            "audiences": ["technical", "management"],
            "channels": ["#incidents", "#management"]
        })
        
        assert result["success"] is True
        assert result["incident_id"] == "TEST-007"
        assert result["total_audiences"] == 2
        assert result["successful_broadcasts"] == 2
        assert len(result["results"]) == 2
        
        # Check that both audiences were processed
        audiences_processed = [r["audience"] for r in result["results"]]
        assert "technical" in audiences_processed
        assert "management" in audiences_processed
        
        # Check that all broadcasts were successful
        assert all(r["success"] for r in result["results"])
    
    def test_notification_error_handling(self):
        """Test notification error handling."""
        # Test with minimal incident data
        minimal_data = {
            "incident_id": "TEST-008"
        }
        
        result = send_notification_tool.invoke({
            "incident_id": "TEST-008",
            "message_type": "created",
            "incident_data": minimal_data
        })
        
        # Should still succeed with minimal data
        assert result["success"] is True
        assert result["incident_id"] == "TEST-008"
    
    def test_format_update_character_count(self):
        """Test that formatted messages include character count."""
        incident_data = {
            "incident_id": "TEST-009",
            "title": "Short incident",
            "severity": "low",
            "status": "open",
            "assigned_teams": ["support"],
            "affected_systems": ["frontend"],
            "description": "Minor UI issue"
        }
        
        result = format_status_update_tool.invoke({
            "incident_id": "TEST-009",
            "incident_data": incident_data,
            "audience": "technical"
        })
        
        assert result["success"] is True
        assert "character_count" in result
        assert result["character_count"] > 0
        assert result["character_count"] == len(result["formatted_message"])
    
    def test_escalation_urgency_levels(self):
        """Test different escalation urgency levels."""
        incident_data = {
            "incident_id": "TEST-010",
            "title": "Test escalation",
            "severity": "high",
            "status": "open",
            "assigned_teams": ["sre"],
            "affected_systems": ["api"]
        }
        
        urgency_levels = ["low", "medium", "high", "critical"]
        
        for urgency in urgency_levels:
            result = send_escalation_notification_tool.invoke({
                "incident_id": "TEST-010",
                "escalation_reason": f"Testing {urgency} urgency",
                "target_team": "management",
                "incident_data": incident_data,
                "urgency_level": urgency
            })
            
            assert result["success"] is True
            assert result["escalation_details"]["urgency_level"] == urgency
            
            # High and critical should be marked as urgent
            expected_urgent = urgency in ["high", "critical"]
            assert result["urgent"] == expected_urgent