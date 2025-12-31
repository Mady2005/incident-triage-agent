"""Tests for the notification system."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from src.incident_agent.notifications.base_notifier import (
    BaseNotifier, 
    NotificationMessage, 
    NotificationChannel, 
    NotificationPriority
)
from src.incident_agent.notifications.slack_notifier import SlackNotifier


class TestBaseNotifier:
    """Test cases for the base notifier."""
    
    def test_notification_message_creation(self):
        """Test creating notification messages."""
        message = NotificationMessage(
            title="Test Incident",
            message="This is a test",
            incident_id="TEST-001",
            severity="high",
            priority=NotificationPriority.HIGH,
            recipients=["team1"],
            metadata={"test": True},
            timestamp=datetime.now(),
            channel=NotificationChannel.SLACK
        )
        
        assert message.title == "Test Incident"
        assert message.incident_id == "TEST-001"
        assert message.severity == "high"
        assert message.priority == NotificationPriority.HIGH


class TestSlackNotifier:
    """Test cases for Slack notifications."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = {
            "webhook_url": "https://hooks.slack.com/services/TEST/WEBHOOK/URL",
            "default_channel": "#test-incidents",
            "team_channels": {
                "sre": "#test-sre",
                "backend": "#test-backend",
                "security": "#test-security"
            },
            "enabled": True
        }
        self.notifier = SlackNotifier(self.config)
    
    def test_slack_notifier_initialization(self):
        """Test Slack notifier initialization."""
        assert self.notifier.webhook_url == self.config["webhook_url"]
        assert self.notifier.default_channel == "#test-incidents"
        assert self.notifier.team_channels["sre"] == "#test-sre"
        assert self.notifier.is_enabled() == True
    
    def test_config_validation(self):
        """Test configuration validation."""
        # Valid config
        assert self.notifier.validate_config() == True
        
        # Invalid webhook URL
        invalid_notifier = SlackNotifier({
            "webhook_url": "https://invalid-url.com",
            "enabled": True
        })
        assert invalid_notifier.validate_config() == False
        
        # Missing webhook URL
        missing_notifier = SlackNotifier({
            "enabled": True
        })
        assert missing_notifier.validate_config() == False
    
    def test_channel_mapping(self):
        """Test channel mapping for recipients."""
        recipients = ["sre", "backend", "oncall"]
        channels = self.notifier._get_target_channels(recipients)
        
        assert "#test-incidents" in channels  # Default channel
        assert "#test-sre" in channels
        assert "#test-backend" in channels
        assert "#oncall" in channels  # Default oncall channel
    
    def test_incident_message_formatting(self):
        """Test formatting incident data into notification message."""
        incident_data = {
            "incident_id": "TEST-001",
            "title": "Test Database Issue",
            "description": "Database connection timeout",
            "severity": "critical",
            "assigned_teams": ["sre", "backend"],
            "affected_systems": ["database", "api"],
            "suggested_actions": ["Check database connections", "Review logs"],
            "escalation_needed": True
        }
        
        message = self.notifier.format_incident_message(incident_data, "created")
        
        assert "🚨 New CRITICAL Incident" in message.title
        assert message.incident_id == "TEST-001"
        assert message.severity == "critical"
        assert message.priority == NotificationPriority.CRITICAL
        assert "sre" in message.recipients
        assert "backend" in message.recipients
    
    def test_should_notify_logic(self):
        """Test notification decision logic."""
        # Critical incidents should always notify
        critical_incident = {"severity": "critical"}
        assert self.notifier.should_notify(critical_incident, "created") == True
        
        # Security incidents should always notify
        security_incident = {"severity": "medium", "is_security_incident": True}
        assert self.notifier.should_notify(security_incident, "created") == True
        
        # Escalations should always notify
        normal_incident = {"severity": "low"}
        assert self.notifier.should_notify(normal_incident, "escalated") == True
        
        # High severity should notify
        high_incident = {"severity": "high"}
        assert self.notifier.should_notify(high_incident, "created") == True
        
        # Medium severity should notify on creation
        medium_incident = {"severity": "medium"}
        assert self.notifier.should_notify(medium_incident, "created") == True
        
        # Disabled notifier should not notify
        disabled_notifier = SlackNotifier({**self.config, "enabled": False})
        assert disabled_notifier.should_notify(critical_incident, "created") == False
    
    def test_slack_payload_building(self):
        """Test building Slack webhook payload."""
        message = NotificationMessage(
            title="🚨 Critical Incident",
            message="Database is down",
            incident_id="TEST-001",
            severity="critical",
            priority=NotificationPriority.CRITICAL,
            recipients=["sre"],
            metadata={},
            timestamp=datetime.now(),
            channel=NotificationChannel.SLACK
        )
        
        payload = self.notifier._build_slack_payload(message, "#test-incidents")
        
        assert payload["channel"] == "#test-incidents"
        assert payload["username"] == "Incident Agent"
        assert len(payload["attachments"]) == 1
        
        attachment = payload["attachments"][0]
        assert attachment["color"] == "#FF0000"  # Red for critical
        assert "🚨 Critical Incident" in attachment["title"]
        assert attachment["text"] == "Database is down"
        
        # Check fields
        fields = attachment["fields"]
        field_titles = [field["title"] for field in fields]
        assert "Incident ID" in field_titles
        assert "Severity" in field_titles
        assert "Priority" in field_titles
        assert "Timestamp" in field_titles
        
        # Critical incidents should have action buttons
        assert "actions" in attachment
        assert len(attachment["actions"]) == 2
    
    @pytest.mark.asyncio
    async def test_send_notification_success(self):
        """Test successful notification sending."""
        message = NotificationMessage(
            title="Test Notification",
            message="Test message",
            incident_id="TEST-001",
            severity="medium",
            priority=NotificationPriority.MEDIUM,
            recipients=["sre"],
            metadata={},
            timestamp=datetime.now(),
            channel=NotificationChannel.SLACK
        )
        
        # Mock successful HTTP response
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            
            result = await self.notifier.send_notification(message)
            assert result == True
    
    @pytest.mark.asyncio
    async def test_send_notification_failure(self):
        """Test notification sending failure."""
        message = NotificationMessage(
            title="Test Notification",
            message="Test message",
            incident_id="TEST-001",
            severity="medium",
            priority=NotificationPriority.MEDIUM,
            recipients=["sre"],
            metadata={},
            timestamp=datetime.now(),
            channel=NotificationChannel.SLACK
        )
        
        # Mock failed HTTP response
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 400
            
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            
            result = await self.notifier.send_notification(message)
            assert result == False
    
    def test_severity_color_mapping(self):
        """Test color mapping for different severities."""
        severities_and_colors = [
            ("critical", "#FF0000"),  # Red
            ("high", "#FF8C00"),      # Orange
            ("medium", "#FFD700"),    # Yellow
            ("low", "#00FF00")        # Green
        ]
        
        for severity, expected_color in severities_and_colors:
            message = NotificationMessage(
                title="Test",
                message="Test",
                incident_id="TEST-001",
                severity=severity,
                priority=NotificationPriority.MEDIUM,
                recipients=[],
                metadata={},
                timestamp=datetime.now(),
                channel=NotificationChannel.SLACK
            )
            
            payload = self.notifier._build_slack_payload(message, "#test")
            attachment = payload["attachments"][0]
            assert attachment["color"] == expected_color
    
    def test_get_channel_type(self):
        """Test getting channel type."""
        assert self.notifier.get_channel() == NotificationChannel.SLACK


class TestNotificationIntegration:
    """Integration tests for notification system."""
    
    def test_incident_processing_with_notifications(self):
        """Test that incident processing can work with notifications."""
        # This would test the integration with the main incident agent
        # For now, we'll test that the notification system doesn't break the flow
        
        incident_data = {
            "incident_id": "INT-001",
            "title": "Integration Test Incident",
            "severity": "high",
            "assigned_teams": ["sre"],
            "affected_systems": ["api"],
            "escalation_needed": False
        }
        
        config = {
            "webhook_url": "https://hooks.slack.com/services/TEST/WEBHOOK/URL",
            "enabled": False  # Disabled for testing
        }
        
        notifier = SlackNotifier(config)
        
        # Should not notify when disabled
        assert notifier.should_notify(incident_data, "created") == False
        
        # Should format message correctly even when disabled
        message = notifier.format_incident_message(incident_data, "created")
        assert message.incident_id == "INT-001"
        assert message.severity == "high"


if __name__ == "__main__":
    # Run a quick test
    test_slack = TestSlackNotifier()
    test_slack.setup_method()
    test_slack.test_slack_notifier_initialization()
    print("✅ Basic notification tests passed!")