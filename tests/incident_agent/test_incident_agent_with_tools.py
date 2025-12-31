"""Tests for the enhanced incident agent with tools integration."""

import pytest
from datetime import datetime
from src.incident_agent.incident_agent_with_tools import (
    process_incident_with_tools,
    get_incident_details_with_tools,
    incident_agent_with_tools
)
from src.incident_agent.tools.incident_tools import clear_incidents_store


class TestIncidentAgentWithTools:
    """Test suite for the enhanced incident agent with tools."""
    
    def setup_method(self):
        """Clear incidents store before each test."""
        clear_incidents_store()
    
    def test_process_incident_with_tools_basic(self):
        """Test basic incident processing with tools integration."""
        incident_data = {
            "id": "TOOL-TEST-001",
            "title": "Database connection failure",
            "description": "Unable to connect to primary database",
            "source": "monitoring",
            "timestamp": datetime.now().isoformat(),
            "reporter": "monitoring-system",
            "affected_systems": ["database", "api"],
            "error_logs": "Connection timeout after 30 seconds",
            "severity_indicators": ["critical", "database", "timeout"]
        }
        
        result = process_incident_with_tools(incident_data)
        
        # Check basic processing results
        assert "incident_id" in result
        assert result["severity"] in ["low", "medium", "high", "critical"]
        assert isinstance(result["assigned_teams"], list)
        assert len(result["assigned_teams"]) > 0
        assert isinstance(result["suggested_actions"], list)
        assert len(result["suggested_actions"]) > 0
        assert isinstance(result["escalation_needed"], bool)
        assert result["status"] in ["open", "in_progress", "resolved", "closed"]
        
        # Check tool-specific results
        assert "tool_created" in result
        assert result["tool_created"] is True
        assert "runbooks_found" in result
        assert "diagnostic_queries" in result
        assert "system_health" in result
        assert "tools_used" in result
        
        # Check tools usage summary
        tools_used = result["tools_used"]
        assert tools_used["incident_management"] is True
        assert tools_used["notifications"] is True
        assert isinstance(tools_used["runbook_lookup"], bool)
        assert isinstance(tools_used["diagnostics"], bool)
        assert isinstance(tools_used["health_checks"], bool)
    
    def test_process_incident_critical_severity(self):
        """Test processing of critical severity incident."""
        incident_data = {
            "id": "TOOL-TEST-002",
            "title": "Complete service outage",
            "description": "All services are down, customers cannot access the platform",
            "source": "monitoring",
            "timestamp": datetime.now().isoformat(),
            "reporter": "monitoring-system",
            "affected_systems": ["frontend", "api", "database", "auth"],
            "error_logs": "Multiple service failures detected",
            "severity_indicators": ["critical", "outage", "down", "failure"]
        }
        
        result = process_incident_with_tools(incident_data)
        
        # Critical incidents should be escalated
        assert result["severity"] == "critical"
        assert result["escalation_needed"] is True
        
        # Should have comprehensive tool results
        assert len(result["runbooks_found"]) > 0
        assert len(result["diagnostic_queries"]) > 0
        assert len(result["system_health"]) > 0
        
        # Should have enhanced actions with runbook steps
        actions_text = " ".join(result["suggested_actions"]).lower()
        assert "runbook" in actions_text or "diagnostic" in actions_text
    
    def test_process_incident_with_runbook_integration(self):
        """Test that runbooks are properly integrated into suggested actions."""
        incident_data = {
            "id": "TOOL-TEST-003",
            "title": "Database high CPU usage",
            "description": "Database server showing sustained high CPU usage",
            "source": "monitoring",
            "timestamp": datetime.now().isoformat(),
            "reporter": "monitoring-system",
            "affected_systems": ["database"],
            "error_logs": "CPU usage at 95% for 15 minutes",
            "severity_indicators": ["performance", "cpu", "database", "high"]
        }
        
        result = process_incident_with_tools(incident_data)
        
        # Should find database-related runbooks
        assert len(result["runbooks_found"]) > 0
        
        # Runbook information should be in suggested actions
        actions_text = " ".join(result["suggested_actions"])
        assert "📖" in actions_text  # Runbook emoji
        assert "⏱️" in actions_text  # Time estimate emoji
        
        # Should have runbook steps in actions
        runbook = result["runbooks_found"][0]
        first_step = runbook["steps"][0].lower()
        actions_lower = actions_text.lower()
        # At least part of the first step should be in actions
        assert any(word in actions_lower for word in first_step.split()[:3])
    
    def test_process_incident_with_diagnostic_queries(self):
        """Test that diagnostic queries are generated and included."""
        incident_data = {
            "id": "TOOL-TEST-004",
            "title": "API response time issues",
            "description": "API endpoints showing increased response times",
            "source": "performance-monitoring",
            "timestamp": datetime.now().isoformat(),
            "reporter": "ops-team",
            "affected_systems": ["api", "database"],
            "error_logs": "Average response time increased to 2.5 seconds",
            "severity_indicators": ["performance", "latency", "api", "slow"]
        }
        
        result = process_incident_with_tools(incident_data)
        
        # Should generate diagnostic queries
        assert len(result["diagnostic_queries"]) > 0
        
        # Diagnostic queries should be referenced in actions
        actions_text = " ".join(result["suggested_actions"])
        assert "🔍" in actions_text  # Diagnostic emoji
        assert "diagnostic" in actions_text.lower()
        
        # Should have performance-related queries
        queries_text = " ".join(result["diagnostic_queries"]).lower()
        assert ("response_time" in queries_text or 
                "performance" in queries_text or
                "latency" in queries_text)
    
    def test_process_incident_with_system_health_checks(self):
        """Test that system health checks are performed and integrated."""
        incident_data = {
            "id": "TOOL-TEST-005",
            "title": "Multiple system alerts",
            "description": "Receiving alerts from multiple systems",
            "source": "monitoring",
            "timestamp": datetime.now().isoformat(),
            "reporter": "monitoring-system",
            "affected_systems": ["api", "database", "auth"],
            "error_logs": "Multiple system health check failures",
            "severity_indicators": ["multiple", "systems", "health", "alerts"]
        }
        
        result = process_incident_with_tools(incident_data)
        
        # Should perform health checks
        assert len(result["system_health"]) > 0
        
        # Should check all affected systems
        checked_systems = {system["system"] for system in result["system_health"]}
        expected_systems = set(incident_data["affected_systems"])
        assert checked_systems == expected_systems
        
        # If any systems are unhealthy, should be mentioned in actions
        unhealthy_systems = [s for s in result["system_health"] if s["status"] != "healthy"]
        if unhealthy_systems:
            actions_text = " ".join(result["suggested_actions"])
            assert "⚠️" in actions_text  # Warning emoji for unhealthy systems
    
    def test_get_incident_details_with_tools(self):
        """Test comprehensive incident details retrieval."""
        # First create an incident
        incident_data = {
            "id": "TOOL-TEST-006",
            "title": "Test incident for details",
            "description": "Testing incident details retrieval",
            "source": "test",
            "timestamp": datetime.now().isoformat(),
            "reporter": "test-user",
            "affected_systems": ["api", "database"],
            "error_logs": "Test error logs",
            "severity_indicators": ["test", "medium"]
        }
        
        process_result = process_incident_with_tools(incident_data)
        incident_id = process_result["incident_id"]
        
        # Get detailed information
        details = get_incident_details_with_tools(incident_id)
        
        assert details["success"] is True
        assert "incident_status" in details
        assert "system_health" in details
        assert "status_updates" in details
        assert "timestamp" in details
        
        # Check incident status
        status = details["incident_status"]
        assert status["incident_id"] == incident_id
        assert status["title"] == "Test incident for details"
        assert "age_hours" in status
        assert "timeline_count" in status
        
        # Check status updates for different audiences
        status_updates = details["status_updates"]
        assert "technical" in status_updates
        assert "management" in status_updates
        assert len(status_updates["technical"]) > 0
        assert len(status_updates["management"]) > 0
        
        # Technical update should be more detailed
        assert len(status_updates["technical"]) > len(status_updates["management"])
    
    def test_get_incident_details_nonexistent(self):
        """Test getting details for non-existent incident."""
        details = get_incident_details_with_tools("NONEXISTENT-001")
        
        assert details["success"] is False
        assert "error" in details
        assert "not found" in details["error"].lower()
    
    def test_incident_workflow_state_management(self):
        """Test that the LangGraph workflow properly manages state with tools."""
        incident_data = {
            "id": "TOOL-TEST-007",
            "title": "Workflow state test",
            "description": "Testing workflow state management",
            "source": "test",
            "timestamp": datetime.now().isoformat(),
            "reporter": "test-user",
            "affected_systems": ["api"],
            "error_logs": "Test logs",
            "severity_indicators": ["medium", "test"]
        }
        
        # Invoke the workflow directly
        result = incident_agent_with_tools.invoke({
            "incident_input": incident_data
        })
        
        # Check that state is properly managed through the workflow
        assert "incident_id" in result
        assert "severity_classification" in result
        assert "team_assignment" in result
        assert "suggested_actions" in result
        assert "tool_created" in result
        assert result["tool_created"] is True
        
        # Check that enhanced actions from tools are present
        assert "runbooks_found" in result
        assert "diagnostic_queries" in result
        assert "system_health" in result
    
    def test_multiple_incidents_processing(self):
        """Test processing multiple incidents with tools."""
        incidents = [
            {
                "id": "MULTI-001",
                "title": "Database issue",
                "description": "Database connection problems",
                "source": "monitoring",
                "timestamp": datetime.now().isoformat(),
                "reporter": "monitoring",
                "affected_systems": ["database"],
                "severity_indicators": ["database", "connection"]
            },
            {
                "id": "MULTI-002", 
                "title": "API performance",
                "description": "API response time degradation",
                "source": "monitoring",
                "timestamp": datetime.now().isoformat(),
                "reporter": "monitoring",
                "affected_systems": ["api"],
                "severity_indicators": ["api", "performance"]
            },
            {
                "id": "MULTI-003",
                "title": "Auth failures",
                "description": "Authentication service failures",
                "source": "security",
                "timestamp": datetime.now().isoformat(),
                "reporter": "security-team",
                "affected_systems": ["auth"],
                "severity_indicators": ["auth", "failure"]
            }
        ]
        
        results = []
        for incident in incidents:
            result = process_incident_with_tools(incident)
            results.append(result)
        
        # All incidents should be processed successfully
        assert len(results) == 3
        
        # Each should have unique incident IDs
        incident_ids = [r["incident_id"] for r in results]
        assert len(set(incident_ids)) == 3
        
        # All should have tool integration
        for result in results:
            assert result["tool_created"] is True
            assert "tools_used" in result
            assert result["tools_used"]["incident_management"] is True
    
    def test_tool_error_resilience(self):
        """Test that the workflow is resilient to tool errors."""
        # Test with minimal incident data that might cause tool issues
        minimal_incident = {
            "id": "MINIMAL-001",
            "title": "Minimal incident",
            # Missing many optional fields
        }
        
        # Should still process successfully even with minimal data
        result = process_incident_with_tools(minimal_incident)
        
        assert "incident_id" in result
        assert "severity" in result
        assert "assigned_teams" in result
        assert "suggested_actions" in result
        
        # Tools should handle missing data gracefully
        assert "tools_used" in result
        assert result["tools_used"]["incident_management"] is True