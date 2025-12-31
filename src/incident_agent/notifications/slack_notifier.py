"""Slack notification implementation for incident agent."""

import json
import asyncio
from typing import Dict, Any, List, Optional
import httpx
from datetime import datetime

from .base_notifier import BaseNotifier, NotificationMessage, NotificationChannel, NotificationPriority


class SlackNotifier(BaseNotifier):
    """Slack notification implementation."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Slack notifier.
        
        Config should contain:
        - webhook_url: Slack webhook URL
        - default_channel: Default channel to post to
        - team_channels: Mapping of team names to Slack channels
        - enabled: Whether notifications are enabled
        """
        super().__init__(config)
        self.webhook_url = config.get("webhook_url")
        self.default_channel = config.get("default_channel", "#incidents")
        self.team_channels = config.get("team_channels", {})
        self.username = config.get("username", "Incident Agent")
        self.icon_emoji = config.get("icon_emoji", ":rotating_light:")
    
    def validate_config(self) -> bool:
        """Validate Slack configuration."""
        if not self.webhook_url:
            return False
        
        if not self.webhook_url.startswith("https://hooks.slack.com/"):
            return False
        
        return True
    
    def get_channel(self) -> NotificationChannel:
        """Get the notification channel type."""
        return NotificationChannel.SLACK
    
    async def send_notification(self, message: NotificationMessage) -> bool:
        """
        Send notification to Slack.
        
        Args:
            message: The notification message to send
            
        Returns:
            True if notification was sent successfully
        """
        if not self.validate_config():
            print(f"❌ Slack configuration invalid")
            return False
        
        try:
            # Determine target channels
            channels = self._get_target_channels(message.recipients)
            
            # Send to each channel
            success_count = 0
            for channel in channels:
                slack_payload = self._build_slack_payload(message, channel)
                
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        self.webhook_url,
                        json=slack_payload,
                        timeout=10.0
                    )
                    
                    if response.status_code == 200:
                        success_count += 1
                        print(f"✅ Slack notification sent to {channel}")
                    else:
                        print(f"❌ Failed to send Slack notification to {channel}: {response.status_code}")
            
            return success_count > 0
            
        except Exception as e:
            print(f"❌ Error sending Slack notification: {str(e)}")
            return False
    
    def _get_target_channels(self, recipients: List[str]) -> List[str]:
        """Get Slack channels for recipients."""
        channels = set()
        
        # Add default channel for all notifications
        channels.add(self.default_channel)
        
        # Map teams to their specific channels
        for recipient in recipients:
            if recipient.lower() in self.team_channels:
                channels.add(self.team_channels[recipient.lower()])
            elif recipient.lower() == "oncall":
                channels.add(self.team_channels.get("oncall", "#oncall"))
            elif recipient.lower() == "security":
                channels.add(self.team_channels.get("security", "#security"))
            elif recipient.lower() == "management":
                channels.add(self.team_channels.get("management", "#management"))
        
        return list(channels)
    
    def _build_slack_payload(self, message: NotificationMessage, channel: str) -> Dict[str, Any]:
        """Build Slack webhook payload."""
        # Choose color based on severity
        color_map = {
            "critical": "#FF0000",  # Red
            "high": "#FF8C00",      # Orange
            "medium": "#FFD700",    # Yellow
            "low": "#00FF00"        # Green
        }
        color = color_map.get(message.severity, "#808080")
        
        # Choose emoji based on severity
        emoji_map = {
            "critical": ":fire:",
            "high": ":warning:",
            "medium": ":information_source:",
            "low": ":white_check_mark:"
        }
        severity_emoji = emoji_map.get(message.severity, ":question:")
        
        # Build attachment with incident details
        attachment = {
            "color": color,
            "title": f"{severity_emoji} {message.title}",
            "text": message.message,
            "fields": [
                {
                    "title": "Incident ID",
                    "value": message.incident_id,
                    "short": True
                },
                {
                    "title": "Severity",
                    "value": message.severity.upper(),
                    "short": True
                },
                {
                    "title": "Priority",
                    "value": message.priority.value.upper(),
                    "short": True
                },
                {
                    "title": "Timestamp",
                    "value": message.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC"),
                    "short": True
                }
            ],
            "footer": "Incident Triage Agent",
            "ts": int(message.timestamp.timestamp())
        }
        
        # Add action buttons for critical incidents
        if message.severity == "critical":
            attachment["actions"] = [
                {
                    "type": "button",
                    "text": "View Details",
                    "url": f"http://localhost:8000/incidents/{message.incident_id}",
                    "style": "primary"
                },
                {
                    "type": "button", 
                    "text": "Escalate",
                    "url": f"http://localhost:8000/incidents/{message.incident_id}/escalate",
                    "style": "danger"
                }
            ]
        
        payload = {
            "channel": channel,
            "username": self.username,
            "icon_emoji": self.icon_emoji,
            "attachments": [attachment]
        }
        
        return payload
    
    def send_test_notification(self) -> bool:
        """Send a test notification to verify configuration."""
        test_message = NotificationMessage(
            title="🧪 Test Notification",
            message="This is a test notification from the Incident Triage Agent.",
            incident_id="TEST-001",
            severity="medium",
            priority=NotificationPriority.MEDIUM,
            recipients=["test"],
            metadata={"test": True},
            timestamp=datetime.now(),
            channel=NotificationChannel.SLACK
        )
        
        try:
            # Use asyncio to run the async method
            return asyncio.run(self.send_notification(test_message))
        except Exception as e:
            print(f"❌ Test notification failed: {str(e)}")
            return False


# Convenience function for quick Slack notifications
async def send_slack_incident_notification(
    incident_data: Dict[str, Any],
    webhook_url: str,
    message_type: str = "created",
    team_channels: Optional[Dict[str, str]] = None
) -> bool:
    """
    Quick function to send Slack notification for an incident.
    
    Args:
        incident_data: Incident information
        webhook_url: Slack webhook URL
        message_type: Type of notification (created, updated, escalated, resolved)
        team_channels: Optional mapping of team names to Slack channels
        
    Returns:
        True if notification was sent successfully
    """
    config = {
        "webhook_url": webhook_url,
        "team_channels": team_channels or {},
        "enabled": True
    }
    
    notifier = SlackNotifier(config)
    
    if not notifier.should_notify(incident_data, message_type):
        return True  # Not an error, just not needed
    
    message = notifier.format_incident_message(incident_data, message_type)
    return await notifier.send_notification(message)