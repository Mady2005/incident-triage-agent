"""Tests for diagnostic tools."""

import pytest
from src.incident_agent.tools.diagnostic_tools import (
    lookup_runbook_tool,
    query_metrics_tool,
    check_system_health_tool,
    generate_diagnostic_queries_tool
)


class TestDiagnosticTools:
    """Test suite for diagnostic tools."""
    
    def test_lookup_runbook_tool_exact_match(self):
        """Test runbook lookup with exact symptom matches."""
        result = lookup_runbook_tool.invoke({
            "affected_systems": ["database"],
            "symptoms": ["timeout", "connection"],
            "severity": "critical"
        })
        
        assert result["success"] is True
        assert result["total_runbooks_found"] > 0
        assert len(result["runbooks"]) > 0
        
        # Should find database connection timeout runbook
        runbook = result["runbooks"][0]
        assert runbook["system"] == "database"
        assert "timeout" in runbook["title"].lower() or "connection" in runbook["title"].lower()
        assert "steps" in runbook
        assert "estimated_time" in runbook
        assert "escalation_criteria" in runbook
        assert runbook["relevance_score"] > 0
    
    def test_lookup_runbook_tool_multiple_systems(self):
        """Test runbook lookup with multiple affected systems."""
        result = lookup_runbook_tool.invoke({
            "affected_systems": ["api", "database"],
            "symptoms": ["high_latency", "slow"],
            "severity": "high"
        })
        
        assert result["success"] is True
        assert result["total_runbooks_found"] > 0
        
        # Should find runbooks for both systems
        systems_found = {runbook["system"] for runbook in result["runbooks"]}
        assert "api" in systems_found or "database" in systems_found
        
        # Check search criteria is preserved
        assert result["search_criteria"]["affected_systems"] == ["api", "database"]
        assert result["search_criteria"]["symptoms"] == ["high_latency", "slow"]
        assert result["search_criteria"]["severity"] == "high"
    
    def test_lookup_runbook_tool_no_matches(self):
        """Test runbook lookup with no symptom matches."""
        result = lookup_runbook_tool.invoke({
            "affected_systems": ["unknown_system"],
            "symptoms": ["unknown_symptom"],
            "severity": "low"
        })
        
        assert result["success"] is True
        # Should still return success even with no matches
        assert result["total_runbooks_found"] == 0
        assert len(result["runbooks"]) == 0
    
    def test_lookup_runbook_tool_fallback(self):
        """Test runbook lookup fallback to general runbooks."""
        result = lookup_runbook_tool.invoke({
            "affected_systems": ["database"],
            "symptoms": ["unknown_symptom"],  # No specific match
            "severity": "medium"
        })
        
        assert result["success"] is True
        # Should find fallback runbooks for the system
        if result["total_runbooks_found"] > 0:
            runbook = result["runbooks"][0]
            assert runbook["system"] == "database"
            assert runbook["relevance_score"] <= 0.5  # Lower score for fallback
    
    def test_query_metrics_tool_cpu(self):
        """Test CPU metrics querying."""
        result = query_metrics_tool.invoke({
            "system": "api",
            "metric_type": "cpu",
            "time_range": "1h",
            "aggregation": "avg"
        })
        
        assert result["success"] is True
        assert result["system"] == "api"
        assert result["metric_type"] == "cpu"
        assert result["unit"] == "percent"
        assert result["current_value"] >= 0
        assert result["status"] in ["normal", "warning", "critical"]
        assert result["trend"] in ["increasing", "decreasing", "stable"]
        assert "thresholds" in result
        assert result["thresholds"]["warning"] == 70
        assert result["thresholds"]["critical"] == 90
        assert "recommendations" in result
        assert isinstance(result["recommendations"], list)
    
    def test_query_metrics_tool_memory(self):
        """Test memory metrics querying."""
        result = query_metrics_tool.invoke({
            "system": "database",
            "metric_type": "memory",
            "time_range": "6h",
            "aggregation": "max"
        })
        
        assert result["success"] is True
        assert result["metric_type"] == "memory"
        assert result["unit"] == "percent"
        assert result["time_range"] == "6h"
        assert result["aggregation"] == "max"
        assert result["thresholds"]["warning"] == 80
        assert result["thresholds"]["critical"] == 95
    
    def test_query_metrics_tool_response_time(self):
        """Test response time metrics querying."""
        result = query_metrics_tool.invoke({
            "system": "api",
            "metric_type": "response_time",
            "time_range": "15m",
            "aggregation": "avg"
        })
        
        assert result["success"] is True
        assert result["metric_type"] == "response_time"
        assert result["unit"] == "milliseconds"
        assert result["thresholds"]["warning"] == 500
        assert result["thresholds"]["critical"] == 1000
    
    def test_query_metrics_tool_error_rate(self):
        """Test error rate metrics querying."""
        result = query_metrics_tool.invoke({
            "system": "auth",
            "metric_type": "error_rate",
            "time_range": "5m",
            "aggregation": "avg"
        })
        
        assert result["success"] is True
        assert result["metric_type"] == "error_rate"
        assert result["unit"] == "percent"
        assert result["current_value"] >= 0
        assert result["thresholds"]["warning"] == 2
        assert result["thresholds"]["critical"] == 5
    
    def test_check_system_health_tool_single_system(self):
        """Test system health check for single system."""
        result = check_system_health_tool.invoke({
            "systems": ["api"],
            "include_dependencies": False
        })
        
        assert result["success"] is True
        assert result["systems_checked"] == 1
        assert result["overall_status"] in ["healthy", "degraded", "unhealthy"]
        assert 0 <= result["overall_health_score"] <= 1
        assert len(result["system_details"]) == 1
        
        system_detail = result["system_details"][0]
        assert system_detail["system"] == "api"
        assert system_detail["status"] in ["healthy", "degraded", "unhealthy"]
        assert 0 <= system_detail["health_score"] <= 1
        assert "issues" in system_detail
        assert "metrics" in system_detail
        assert "last_checked" in system_detail
    
    def test_check_system_health_tool_multiple_systems(self):
        """Test system health check for multiple systems."""
        systems = ["api", "database", "auth"]
        result = check_system_health_tool.invoke({
            "systems": systems,
            "include_dependencies": True
        })
        
        assert result["success"] is True
        assert result["systems_checked"] == 3
        assert len(result["system_details"]) == 3
        
        # Check that all systems are included
        system_names = {detail["system"] for detail in result["system_details"]}
        assert system_names == set(systems)
        
        # Check health counts add up
        total_systems = (result["healthy_systems"] + 
                        result["degraded_systems"] + 
                        result["unhealthy_systems"])
        assert total_systems == 3
    
    def test_check_system_health_tool_with_dependencies(self):
        """Test system health check with dependency checking."""
        result = check_system_health_tool.invoke({
            "systems": ["api"],
            "include_dependencies": True
        })
        
        assert result["success"] is True
        
        # API should have dependencies
        api_detail = result["system_details"][0]
        assert api_detail["system"] == "api"
        # Dependencies might be empty list or contain actual dependencies
        assert "dependencies" in api_detail
        assert isinstance(api_detail["dependencies"], list)
    
    def test_generate_diagnostic_queries_performance(self):
        """Test diagnostic query generation for performance incidents."""
        result = generate_diagnostic_queries_tool.invoke({
            "incident_type": "performance",
            "affected_systems": ["api", "database"],
            "symptoms": ["slow", "timeout"]
        })
        
        assert result["success"] is True
        assert result["incident_type"] == "performance"
        assert result["affected_systems"] == ["api", "database"]
        assert result["symptoms"] == ["slow", "timeout"]
        assert result["total_queries"] > 0
        assert result["total_steps"] > 0
        assert len(result["diagnostic_queries"]) > 0
        assert len(result["investigation_steps"]) > 0
        assert "next_actions" in result
        
        # Should contain performance-related queries
        queries_text = " ".join(result["diagnostic_queries"]).lower()
        assert "response_time" in queries_text or "performance" in queries_text
    
    def test_generate_diagnostic_queries_outage(self):
        """Test diagnostic query generation for outage incidents."""
        result = generate_diagnostic_queries_tool.invoke({
            "incident_type": "outage",
            "affected_systems": ["frontend", "api"],
            "symptoms": ["down", "unavailable"]
        })
        
        assert result["success"] is True
        assert result["incident_type"] == "outage"
        assert len(result["diagnostic_queries"]) > 0
        
        # Should contain outage-related queries
        queries_text = " ".join(result["diagnostic_queries"]).lower()
        assert "health_check" in queries_text or "uptime" in queries_text
    
    def test_generate_diagnostic_queries_security(self):
        """Test diagnostic query generation for security incidents."""
        result = generate_diagnostic_queries_tool.invoke({
            "incident_type": "security",
            "affected_systems": ["auth", "api"],
            "symptoms": ["brute_force", "suspicious"]
        })
        
        assert result["success"] is True
        assert result["incident_type"] == "security"
        
        # Should contain security-related queries
        queries_text = " ".join(result["diagnostic_queries"]).lower()
        assert ("security" in queries_text or 
                "auth" in queries_text or 
                "access_log" in queries_text)
    
    def test_generate_diagnostic_queries_error(self):
        """Test diagnostic query generation for error incidents."""
        result = generate_diagnostic_queries_tool.invoke({
            "incident_type": "error",
            "affected_systems": ["api"],
            "symptoms": ["exception", "failure"]
        })
        
        assert result["success"] is True
        assert result["incident_type"] == "error"
        
        # Should contain error-related queries
        queries_text = " ".join(result["diagnostic_queries"]).lower()
        assert "error" in queries_text or "deployment" in queries_text
    
    def test_generate_diagnostic_queries_symptom_specific(self):
        """Test diagnostic query generation with specific symptoms."""
        result = generate_diagnostic_queries_tool.invoke({
            "incident_type": "performance",
            "affected_systems": ["database"],
            "symptoms": ["timeout", "memory", "cpu"]
        })
        
        assert result["success"] is True
        
        # Should include symptom-specific queries
        queries_text = " ".join(result["diagnostic_queries"]).lower()
        steps_text = " ".join(result["investigation_steps"]).lower()
        
        # Check for symptom-specific content
        assert ("timeout" in queries_text or "timeout" in steps_text)
        assert ("memory" in queries_text or "memory" in steps_text)
        assert ("cpu" in queries_text or "cpu" in steps_text)
    
    def test_metrics_recommendations_generation(self):
        """Test that metrics generate appropriate recommendations."""
        # Test critical CPU
        result = query_metrics_tool.invoke({
            "system": "database",
            "metric_type": "cpu",
            "time_range": "1h",
            "aggregation": "max"
        })
        
        assert result["success"] is True
        
        if result["status"] == "critical":
            recommendations = result["recommendations"]
            assert len(recommendations) > 0
            rec_text = " ".join(recommendations).lower()
            assert ("cpu" in rec_text or 
                    "process" in rec_text or 
                    "scaling" in rec_text)
    
    def test_system_health_metrics_integration(self):
        """Test that system health checks include metrics."""
        result = check_system_health_tool.invoke({
            "systems": ["api"],
            "include_dependencies": False
        })
        
        assert result["success"] is True
        
        system_detail = result["system_details"][0]
        metrics = system_detail["metrics"]
        
        # Should have key metrics
        expected_metrics = ["cpu", "memory", "response_time"]
        for metric in expected_metrics:
            if metric in metrics:
                metric_data = metrics[metric]
                assert "value" in metric_data
                assert "status" in metric_data
                assert "unit" in metric_data
                assert metric_data["status"] in ["normal", "warning", "critical"]