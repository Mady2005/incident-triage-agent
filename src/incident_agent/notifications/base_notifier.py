"""Base notification interface for incident agent."""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime


class NotificationChannel(Enum):
    """Available notification channels."""
    SLACK = "slack"
    EMAIL = "email"
    PAGERDUTY = "pagerduty"
    SMS = "sms"
    WEBHOOK = "webhook"


class NotificationPriority(Enum):
    """Notification priority levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class NotificationMessage:
    """Structured notification message."""
    title: str
    message: str
    incident_id: str
    severity: str
    priority: NotificationPriority
    recipients: List[str]
    metadata: Dict[str, Any]
    timestamp: datetime
    channel: NotificationChannel


class BaseNotifier(ABC):
    """Base class for all notification implementations."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize notifier with configuration."""
        self.config = config
        self.enabled = config.get("enabled", True)
    
    @abstractmethod
    async def send_notification(self, message: NotificationMessage) -> bool:
        """
        Send a notification message.
        
        Args:
            message: The notification message to send
            
        Returns:
            True if notification was sent successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def validate_config(self) -> bool:
        """
        Validate the notifier configuration.
        
        Returns:
            True if configuration is valid, False otherwise
        """
        pass
    
    def format_incident_message(
        self, 
        incident_data: Dict[str, Any], 
        message_type: str = "created"
    ) -> NotificationMessage:
        """
        Format incident data into a notification message.
        
        Args:
            incident_data: Incident information
            message_type: Type of notification (created, updated, escalated, resolved)
            
        Returns:
            Formatted notification message
        """
        severity = incident_data.get("severity", "unknown")
        incident_id = incident_data.get("incident_id", "unknown")
        title = incident_data.get("title", "Incident")
        
        # Determine priority based on severity
        priority_map = {
            "critical": NotificationPriority.CRITICAL,
            "high": NotificationPriority.HIGH,
            "medium": NotificationPriority.MEDIUM,
            "low": NotificationPriority.LOW
        }
        priority = priority_map.get(severity, NotificationPriority.MEDIUM)
        
        # Format message based on type
        if message_type == "created":
            message_title = f"🚨 New {severity.upper()} Incident: {title}"
            message_body = self._format_incident_details(incident_data, "created")
        elif message_type == "escalated":
            message_title = f"⚡ Incident Escalated: {title}"
            message_body = self._format_incident_details(incident_data, "escalated")
        elif message_type == "resolved":
            message_title = f"✅ Incident Resolved: {title}"
            message_body = self._format_incident_details(incident_data, "resolved")
        else:
            message_title = f"📋 Incident Updated: {title}"
            message_body = self._format_incident_details(incident_data, "updated")
        
        return NotificationMessage(
            title=message_title,
            message=message_body,
            incident_id=incident_id,
            severity=severity,
            priority=priority,
            recipients=self._get_recipients(incident_data),
            metadata=incident_data,
            timestamp=datetime.now(),
            channel=self.get_channel()
        )
    
    def _format_incident_details(self, incident_data: Dict[str, Any], message_type: str) -> str:
        """Format incident details for notification message."""
        incident_id = incident_data.get("incident_id", "unknown")
        severity = incident_data.get("severity", "unknown")
        assigned_teams = incident_data.get("assigned_teams", [])
        affected_systems = incident_data.get("affected_systems", [])
        description = incident_data.get("description", "No description provided")
        
        message_parts = [
            f"**Incident ID:** {incident_id}",
            f"**Severity:** {severity.upper()}",
            f"**Assigned Teams:** {', '.join(assigned_teams) if assigned_teams else 'None'}",
            f"**Affected Systems:** {', '.join(affected_systems) if affected_systems else 'None'}",
            f"**Description:** {description[:200]}{'...' if len(description) > 200 else ''}"
        ]
        
        if message_type == "created":
            suggested_actions = incident_data.get("suggested_actions", [])
            if suggested_actions:
                message_parts.append(f"**Immediate Actions:** {len(suggested_actions)} suggested")
                for i, action in enumerate(suggested_actions[:3], 1):
                    message_parts.append(f"  {i}. {action}")
                if len(suggested_actions) > 3:
                    message_parts.append(f"  ... and {len(suggested_actions) - 3} more")
        
        elif message_type == "escalated":
            escalation_reason = incident_data.get("escalation_reason", "Automatic escalation")
            message_parts.append(f"**Escalation Reason:** {escalation_reason}")
        
        return "\n".join(message_parts)
    
    def _get_recipients(self, incident_data: Dict[str, Any]) -> List[str]:
        """Get notification recipients based on incident data."""
        recipients = []
        
        # Add assigned teams
        assigned_teams = incident_data.get("assigned_teams", [])
        recipients.extend(assigned_teams)
        
        # Add escalation recipients for critical incidents
        if incident_data.get("severity") == "critical":
            recipients.extend(["oncall", "management"])
        
        # Add security team for security incidents
        if incident_data.get("is_security_incident", False):
            recipients.append("security")
        
        return list(set(recipients))  # Remove duplicates
    
    @abstractmethod
    def get_channel(self) -> NotificationChannel:
        """Get the notification channel type."""
        pass
    
    def is_enabled(self) -> bool:
        """Check if notifier is enabled."""
        return self.enabled
    
    def should_notify(self, incident_data: Dict[str, Any], message_type: str) -> bool:
        """
        Determine if notification should be sent based on incident data and type.
        
        Args:
            incident_data: Incident information
            message_type: Type of notification
            
        Returns:
            True if notification should be sent
        """
        if not self.is_enabled():
            return False
        
        severity = incident_data.get("severity", "low")
        
        # Always notify for critical incidents
        if severity == "critical":
            return True
        
        # Always notify for security incidents
        if incident_data.get("is_security_incident", False):
            return True
        
        # Always notify for escalations
        if message_type == "escalated":
            return True
        
        # Notify for high severity incidents
        if severity == "high":
            return True
        
        # For medium/low severity, only notify on creation
        if message_type == "created" and severity in ["medium", "low"]:
            return True
        
        return False