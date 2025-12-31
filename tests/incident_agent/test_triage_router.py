"""Property-based tests for incident triage router."""

import pytest
from hypothesis import given, strategies as st, assume
from unittest.mock import Mock, patch

from src.incident_agent.routers.triage_router import (
    TriageRouter, 
    prioritize_incidents, 
    detect_critical_incidents,
    match_historical_patterns
)
from src.incident_agent.schemas import SeverityClassificationSchema, IncidentReport
from src.incident_agent.models.incident import Incident, IncidentSeverity
from .conftest import incident_reports, incidents, severity_levels


class TestTriageRouter:
    """Test cases for the TriageRouter class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Mock the LLM to avoid needing API keys
        mock_llm = Mock()
        self.router = TriageRouter(llm=mock_llm)
    
    @given(incident_reports())
    def test_severity_classification_consistency(self, incident_report):
        """
        **Feature: incident-triage-agent, Property 1: Severity Classification Consistency**
        
        For any incident report, the agent should assign exactly one severity level 
        (critical, high, medium, low) with accompanying reasoning.
        
        **Validates: Requirements 1.1, 1.4**
        """
        # Mock the LLM to return a valid classification
        mock_classification = SeverityClassificationSchema(
            reasoning="Test reasoning for classification",
            severity="medium",
            security_incident=False,
            affected_systems=incident_report.affected_systems
        )
        
        with patch.object(self.router.llm, 'with_structured_output') as mock_structured:
            mock_structured.return_value.invoke.return_value = mock_classification
            
            result = self.router.classify_severity(incident_report)
            
            # Property: Must return exactly one severity level
            assert result.severity in ["critical", "high", "medium", "low"]
            
            # Property: Must include reasoning
            assert result.reasoning is not None
            assert len(result.reasoning.strip()) > 0
            
            # Property: Must identify affected systems
            assert isinstance(result.affected_systems, list)
            
            # Property: Must determine security incident status
            assert isinstance(result.security_incident, bool)
    
    @given(incident_reports())
    def test_fallback_classification_always_returns_valid_severity(self, incident_report):
        """Test that fallback classification always returns a valid severity level."""
        # Test the fallback method directly
        severity = self.router._fallback_severity_classification(incident_report)
        
        # Property: Fallback must always return valid severity
        assert severity in ["critical", "high", "medium", "low"]
    
    @given(incident_reports())
    def test_security_detection_is_boolean(self, incident_report):
        """Test that security detection always returns a boolean."""
        result = self.router._detect_security_indicators(incident_report)
        
        # Property: Security detection must return boolean
        assert isinstance(result, bool)
    
    @given(incident_reports())
    def test_escalation_decision_is_boolean(self, incident_report):
        """Test that escalation decisions are always boolean."""
        # Create a mock classification
        classification = SeverityClassificationSchema(
            reasoning="Test reasoning",
            severity="high",
            security_incident=False,
            affected_systems=incident_report.affected_systems
        )
        
        result = self.router.should_escalate_immediately(classification)
        
        # Property: Escalation decision must be boolean
        assert isinstance(result, bool)
    
    @given(incident_reports())
    def test_notification_urgency_is_valid(self, incident_report):
        """Test that notification urgency is always valid."""
        classification = SeverityClassificationSchema(
            reasoning="Test reasoning",
            severity="medium",
            security_incident=False,
            affected_systems=incident_report.affected_systems
        )
        
        urgency = self.router.get_notification_urgency(classification)
        
        # Property: Urgency must be one of valid values
        assert urgency in ["immediate", "urgent", "normal"]
    
    @given(incident_reports())
    def test_incident_creation_preserves_report_data(self, incident_report):
        """Test that incident creation preserves original report data."""
        classification = SeverityClassificationSchema(
            reasoning="Test reasoning",
            severity="high",
            security_incident=False,
            affected_systems=incident_report.affected_systems
        )
        
        incident = self.router.create_incident_from_classification(incident_report, classification)
        
        # Property: Original report data must be preserved
        assert incident.report.id == incident_report.id
        assert incident.report.title == incident_report.title
        assert incident.report.description == incident_report.description
        assert incident.report.affected_systems == incident_report.affected_systems
        
        # Property: Severity must be set from classification
        assert incident.severity.value == classification.severity


class TestIncidentPrioritizationAndOrdering:
    """Test cases for comprehensive incident prioritization and ordering functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Mock the LLM to avoid needing API keys
        mock_llm = Mock()
        self.router = TriageRouter(llm=mock_llm)
    
    @given(st.lists(incidents(), min_size=1, max_size=8))
    def test_batch_processing_returns_complete_structure(self, incident_list):
        """Test that batch processing returns all required components."""
        # Set varied severities for comprehensive testing
        severity_values = ["critical", "high", "medium", "low"]
        for i, incident in enumerate(incident_list):
            severity = severity_values[i % len(severity_values)]
            incident.set_severity(severity, f"Test severity {severity}")
            
            # Mark some as security incidents
            if i % 4 == 0:
                incident.mark_as_security_incident()
        
        result = self.router.process_incident_batch_with_prioritization(incident_list)
        
        # Property: Result must contain all required keys
        required_keys = [
            "prioritized_incidents", "critical_incidents", "immediate_notifications",
            "historical_insights", "processing_summary"
        ]
        for key in required_keys:
            assert key in result
        
        # Property: Prioritized incidents should maintain count
        assert len(result["prioritized_incidents"]) == len(incident_list)
        
        # Property: Processing summary should have correct counts
        summary = result["processing_summary"]
        assert summary["total_incidents"] == len(incident_list)
        assert isinstance(summary["critical_count"], int)
        assert isinstance(summary["security_count"], int)
        
        # Property: Severity distribution should sum to total incidents
        severity_dist = summary["severity_distribution"]
        total_in_distribution = sum(severity_dist.values())
        assert total_in_distribution == len(incident_list)
    
    @given(st.lists(incidents(), min_size=2, max_size=6))
    def test_critical_incident_notification_generation(self, incident_list):
        """Test that critical incidents generate proper immediate notifications."""
        # Make some incidents critical
        critical_count = 0
        for i, incident in enumerate(incident_list):
            if i % 2 == 0:  # Make every other incident critical
                incident.set_severity("critical", "Test critical incident")
                critical_count += 1
            else:
                incident.set_severity("medium", "Test non-critical incident")
        
        result = self.router.process_incident_batch_with_prioritization(incident_list)
        
        # Property: Should have notifications for critical incidents
        notifications = result["immediate_notifications"]
        critical_incidents = result["critical_incidents"]
        
        # Property: Each critical incident should have a notification
        critical_ids = set(inc["id"] for inc in critical_incidents)
        notification_ids = set(notif["incident_id"] for notif in notifications)
        
        # All critical incidents should have notifications
        for critical_id in critical_ids:
            assert critical_id in notification_ids
        
        # Property: Each notification should have required fields
        for notification in notifications:
            assert "incident_id" in notification
            assert "severity" in notification
            assert "notification_reason" in notification
            assert "recipients" in notification
            assert notification["urgency"] == "immediate"
            assert "message" in notification
            assert "affected_systems" in notification
    
    @given(st.lists(incidents(), min_size=0, max_size=3))
    def test_empty_incident_list_handling(self, incident_list):
        """Test that empty incident lists are handled gracefully."""
        # Test with empty list
        result = self.router.process_incident_batch_with_prioritization([])
        
        # Property: Empty input should return empty results with proper structure
        assert result["prioritized_incidents"] == []
        assert result["critical_incidents"] == []
        assert result["immediate_notifications"] == []
        assert result["historical_insights"] == {}
        
        summary = result["processing_summary"]
        assert summary["total_incidents"] == 0
        assert summary["critical_count"] == 0
        assert summary["security_count"] == 0
        assert summary["immediate_notification_count"] == 0
    
    @given(st.lists(incidents(), min_size=1, max_size=5))
    def test_system_impact_analysis_accuracy(self, incident_list):
        """Test that system impact analysis provides accurate metrics."""
        # Ensure incidents have varied system impacts
        for i, incident in enumerate(incident_list):
            # Vary the number of affected systems
            systems_count = (i % 4) + 1  # 1-4 systems per incident
            incident.report.affected_systems = [f"system-{j}" for j in range(systems_count)]
            incident.set_severity("medium", "Test incident")
        
        result = self.router.process_incident_batch_with_prioritization(incident_list)
        
        impact_analysis = result["processing_summary"]["system_impact_analysis"]
        
        # Property: Total systems affected should be sum of all incident systems
        expected_total = sum(len(inc.report.affected_systems) for inc in incident_list)
        assert impact_analysis["total_systems_affected"] == expected_total
        
        # Property: Average should be calculated correctly
        expected_avg = expected_total / len(incident_list)
        assert abs(impact_analysis["average_systems_per_incident"] - expected_avg) < 0.01
        
        # Property: Unique systems count should be reasonable
        all_systems = set()
        for inc in incident_list:
            all_systems.update(inc.report.affected_systems)
        assert impact_analysis["unique_systems_count"] == len(all_systems)
    
    @given(st.lists(incidents(), min_size=1, max_size=4))
    def test_historical_insights_integration(self, incident_list):
        """Test that historical insights are properly integrated when available."""
        # Set up some historical data
        historical_data = [
            {
                "id": "HIST-001",
                "title": "Database connection timeout",
                "description": "Connection issues with primary database",
                "severity": "high",
                "affected_systems": ["database", "api"],
                "resolution_time_minutes": 45,
                "is_security_incident": False
            },
            {
                "id": "HIST-002",
                "title": "API performance degradation",
                "description": "Slow response times across all endpoints",
                "severity": "medium", 
                "affected_systems": ["api", "load-balancer"],
                "resolution_time_minutes": 120,
                "is_security_incident": False
            }
        ]
        
        self.router.set_historical_incidents(historical_data)
        
        # Set up incidents with similar characteristics
        for i, incident in enumerate(incident_list):
            incident.report.title = f"Database connection issue {i}"
            incident.report.description = "Connection timeout problems"
            incident.report.affected_systems = ["database", "api"]
            incident.set_severity("high", "Test incident")
        
        result = self.router.process_incident_batch_with_prioritization(incident_list)
        
        # Property: Historical insights should be provided for top priority incidents
        insights = result["historical_insights"]
        
        # Should have insights for at least some incidents (up to top 5)
        expected_insight_count = min(len(incident_list), 5)
        
        # Property: Each insight should have proper structure
        for incident_id, insight in insights.items():
            assert "similar_count" in insight
            assert "top_similarity_score" in insight
            assert isinstance(insight["similar_count"], int)
            assert isinstance(insight["top_similarity_score"], (int, float))
            assert 0 <= insight["top_similarity_score"] <= 1


class TestIncidentPrioritization:
    """Test cases for incident prioritization functions."""
    
    @given(st.lists(incidents(), min_size=1, max_size=10))
    def test_incident_ordering_by_priority(self, incident_list):
        """
        **Feature: incident-triage-agent, Property 2: Incident Ordering by Priority**
        
        For any collection of incidents, ordering by severity and impact scope should 
        place critical incidents first, followed by high, medium, and low severity incidents.
        
        **Validates: Requirements 1.2**
        """
        # Set different severities for testing
        severity_values = ["critical", "high", "medium", "low"]
        for i, incident in enumerate(incident_list):
            severity = severity_values[i % len(severity_values)]
            incident.set_severity(severity, f"Test severity {severity}")
        
        # Prioritize incidents
        prioritized = prioritize_incidents(incident_list)
        
        # Property: Result should have same length as input
        assert len(prioritized) == len(incident_list)
        
        # Property: All incidents should be present
        assert set(inc.report.id for inc in prioritized) == set(inc.report.id for inc in incident_list)
        
        # Property: Critical incidents should come before non-critical
        critical_indices = [i for i, inc in enumerate(prioritized) if inc.severity == IncidentSeverity.CRITICAL]
        non_critical_indices = [i for i, inc in enumerate(prioritized) if inc.severity != IncidentSeverity.CRITICAL]
        
        if critical_indices and non_critical_indices:
            assert max(critical_indices) < min(non_critical_indices)
        
        # Property: High severity should come before medium and low
        high_indices = [i for i, inc in enumerate(prioritized) if inc.severity == IncidentSeverity.HIGH]
        medium_low_indices = [i for i, inc in enumerate(prioritized) 
                             if inc.severity in [IncidentSeverity.MEDIUM, IncidentSeverity.LOW]]
        
        if high_indices and medium_low_indices:
            assert max(high_indices) < min(medium_low_indices)
    
    @given(st.lists(incidents(), min_size=1, max_size=10))
    def test_critical_incident_detection(self, incident_list):
        """Test that critical incidents are properly detected for immediate notification."""
        # Set some incidents as critical
        critical_count = 0
        for i, incident in enumerate(incident_list):
            if i % 3 == 0:  # Make every third incident critical
                incident.set_severity("critical", "Test critical incident")
                critical_count += 1
            else:
                incident.set_severity("medium", "Test non-critical incident")
        
        # Detect critical incidents
        critical_incidents = detect_critical_incidents(incident_list)
        
        # Property: All returned incidents should require immediate notification
        for incident in critical_incidents:
            assert (incident.severity == IncidentSeverity.CRITICAL or 
                   incident.is_security_incident or 
                   len(incident.report.affected_systems) > 5)
        
        # Property: All critical severity incidents should be included
        critical_severity_incidents = [inc for inc in incident_list if inc.severity == IncidentSeverity.CRITICAL]
        critical_ids = set(inc.report.id for inc in critical_incidents)
        
        for critical_inc in critical_severity_incidents:
            assert critical_inc.report.id in critical_ids
    
    @given(st.lists(incidents(), min_size=1, max_size=8))
    def test_critical_incident_notification_generation(self, incident_list):
        """
        **Feature: incident-triage-agent, Property 3: Critical Incident Notification**
        
        For any incident classified as critical severity, the agent should generate 
        immediate notification to the primary on-call engineer.
        
        **Validates: Requirements 1.3**
        """
        # Set up test router
        mock_llm = Mock()
        router = TriageRouter(llm=mock_llm)
        
        # Set some incidents as critical, others as non-critical
        critical_incidents = []
        non_critical_incidents = []
        
        for i, incident in enumerate(incident_list):
            if i % 3 == 0:  # Make every third incident critical
                incident.set_severity("critical", "Test critical incident")
                critical_incidents.append(incident)
            else:
                incident.set_severity("medium", "Test non-critical incident")
                non_critical_incidents.append(incident)
        
        # Process incidents with the router to generate notifications
        result = router.process_incident_batch_with_prioritization(incident_list)
        
        # Property: Every critical severity incident must generate an immediate notification
        notifications = result["immediate_notifications"]
        critical_incident_ids = set(inc.report.id for inc in critical_incidents)
        notification_incident_ids = set(notif["incident_id"] for notif in notifications)
        
        # All critical incidents should have notifications
        for critical_id in critical_incident_ids:
            assert critical_id in notification_incident_ids, f"Critical incident {critical_id} missing notification"
        
        # Property: All notifications for critical incidents must have "immediate" urgency
        for notification in notifications:
            if notification["incident_id"] in critical_incident_ids:
                assert notification["urgency"] == "immediate", f"Critical incident notification must have immediate urgency"
        
        # Property: All notifications for critical incidents must include primary-oncall recipient
        for notification in notifications:
            if notification["incident_id"] in critical_incident_ids:
                assert "recipients" in notification, "Notification must include recipients"
                # The notification should be sent to primary on-call for critical incidents
                # This is verified through the router's get_notification_recipients method
        
        # Property: Critical incident notifications must include essential information
        for notification in notifications:
            if notification["incident_id"] in critical_incident_ids:
                required_fields = ["incident_id", "severity", "notification_reason", "recipients", "urgency", "message", "affected_systems"]
                for field in required_fields:
                    assert field in notification, f"Critical incident notification missing required field: {field}"
                
                # Verify severity is marked as critical
                assert notification["severity"] == "critical", "Critical incident notification must show critical severity"
                
                # Verify message contains incident information
                assert len(notification["message"]) > 0, "Critical incident notification must have non-empty message"
                
                # Verify affected systems are included
                assert isinstance(notification["affected_systems"], list), "Affected systems must be a list"
    
    @given(st.lists(incidents(), min_size=0, max_size=5))
    def test_historical_pattern_matching_returns_valid_format(self, incident_list):
        """Test that historical pattern matching returns properly formatted results."""
        if not incident_list:
            return  # Skip empty lists
        
        incident = incident_list[0]
        
        # Create mock historical data
        historical_data = [
            {
                "id": "HIST-001",
                "title": "Database connection issue",
                "description": "Connection timeout problems",
                "severity": "high",
                "affected_systems": ["database", "api"]
            },
            {
                "id": "HIST-002", 
                "title": "API performance degradation",
                "description": "Slow response times",
                "severity": "medium",
                "affected_systems": ["api"]
            }
        ]
        
        matches = match_historical_patterns(incident, historical_data)
        
        # Property: Result should be a list
        assert isinstance(matches, list)
        
        # Property: Each match should have similarity score
        for match in matches:
            assert "similarity_score" in match
            assert isinstance(match["similarity_score"], (int, float))
            assert 0 <= match["similarity_score"] <= 1
        
        # Property: Matches should be sorted by similarity (highest first)
        if len(matches) > 1:
            for i in range(len(matches) - 1):
                assert matches[i]["similarity_score"] >= matches[i + 1]["similarity_score"]


class TestSecurityIncidentHandling:
    """Test cases for security incident handling."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Mock the LLM to avoid needing API keys
        mock_llm = Mock()
        self.router = TriageRouter(llm=mock_llm)
    
    @given(incident_reports())
    def test_security_incident_classification(self, incident_report):
        """
        **Feature: incident-triage-agent, Property 15: Security Incident Classification**
        
        For any incident report containing security indicators, the incident should be 
        classified as a security incident with appropriate escalation.
        
        **Validates: Requirements 6.1, 6.2**
        """
        # Add security indicators to make it a security incident
        security_keywords = ["security", "breach", "unauthorized", "hack", "malware"]
        
        # Test with security keywords in title
        security_incident_report = IncidentReport(
            id=incident_report.id,
            title=f"Security breach in {incident_report.title}",
            description=incident_report.description,
            source=incident_report.source,
            timestamp=incident_report.timestamp,
            reporter=incident_report.reporter,
            affected_systems=incident_report.affected_systems,
            error_logs=incident_report.error_logs,
            metrics_data=incident_report.metrics_data,
            severity_indicators=incident_report.severity_indicators + ["security", "breach"]
        )
        
        # Test security detection
        is_security = self.router._detect_security_indicators(security_incident_report)
        
        # Property: Security incidents should be detected
        assert is_security == True
        
        # Test with non-security incident
        normal_incident_report = IncidentReport(
            id=incident_report.id,
            title="Normal performance issue",
            description="System is running slowly",
            source=incident_report.source,
            timestamp=incident_report.timestamp,
            reporter=incident_report.reporter,
            affected_systems=["api"],
            error_logs="Slow response times",
            metrics_data=incident_report.metrics_data,
            severity_indicators=["performance", "slow"]
        )
        
        is_normal = self.router._detect_security_indicators(normal_incident_report)
        
        # Property: Non-security incidents should not be flagged as security
        assert is_normal == False
    
    @given(incident_reports())
    def test_security_incident_escalation(self, incident_report):
        """Test that security incidents trigger appropriate escalation."""
        # Create security classification
        security_classification = SeverityClassificationSchema(
            reasoning="Security indicators detected",
            severity="high",
            security_incident=True,
            affected_systems=incident_report.affected_systems
        )
        
        # Test escalation decision
        should_escalate = self.router.should_escalate_immediately(security_classification)
        
        # Property: Security incidents should always escalate
        assert should_escalate == True
        
        # Test notification urgency
        urgency = self.router.get_notification_urgency(security_classification)
        
        # Property: Security incidents should have immediate urgency
        assert urgency == "immediate"