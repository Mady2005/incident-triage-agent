"""Configuration management for the incident triage agent."""

import os
from dataclasses import dataclass, fields
from typing import Any, Optional

from langchain_core.runnables import RunnableConfig


@dataclass(kw_only=True)
class Configuration:
    """Configuration for the incident triage agent."""
    
    # LLM Configuration
    model_name: str = "gpt-4o-mini"
    temperature: float = 0.1
    
    # Incident Processing Configuration
    severity_classification_timeout: int = 30  # seconds
    team_routing_timeout: int = 15  # seconds
    critical_incident_notification_delay: int = 0  # seconds
    
    # Team Configuration
    available_teams: str = "SRE,Backend,Frontend,Infrastructure,Security,Database"
    default_escalation_path: str = "SRE,Infrastructure,Backend"
    
    # Notification Configuration
    notification_channels: str = "email,slack,webhook"
    critical_notification_channels: str = "email,slack,webhook,sms"
    
    # Memory and Learning Configuration
    enable_memory: bool = True
    memory_store_namespace: str = "incident_agent"
    learning_feedback_weight: float = 0.1
    
    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_title: str = "Incident Triage Agent API"
    api_version: str = "1.0.0"
    
    # External Integrations
    pagerduty_api_key: Optional[str] = None
    slack_bot_token: Optional[str] = None
    webhook_urls: Optional[str] = None
    
    # Security Configuration
    security_escalation_teams: str = "Security,SRE,Infrastructure"
    security_notification_delay: int = 0  # immediate
    compliance_reporting_enabled: bool = True

    @classmethod
    def from_runnable_config(
        cls, config: Optional[RunnableConfig] = None
    ) -> "Configuration":
        """Create a Configuration instance from a RunnableConfig."""
        configurable = (
            config["configurable"] if config and "configurable" in config else {}
        )
        values: dict[str, Any] = {
            f.name: os.environ.get(f.name.upper(), configurable.get(f.name))
            for f in fields(cls)
            if f.init
        }

        return cls(**{k: v for k, v in values.items() if v is not None})
    
    def get_available_teams(self) -> list[str]:
        """Get list of available response teams."""
        return [team.strip() for team in self.available_teams.split(",")]
    
    def get_default_escalation_path(self) -> list[str]:
        """Get default escalation path as a list."""
        return [team.strip() for team in self.default_escalation_path.split(",")]
    
    def get_notification_channels(self) -> list[str]:
        """Get list of notification channels."""
        return [channel.strip() for channel in self.notification_channels.split(",")]
    
    def get_critical_notification_channels(self) -> list[str]:
        """Get list of critical notification channels."""
        return [channel.strip() for channel in self.critical_notification_channels.split(",")]
    
    def get_security_escalation_teams(self) -> list[str]:
        """Get list of security escalation teams."""
        return [team.strip() for team in self.security_escalation_teams.split(",")]
    
    def get_webhook_urls(self) -> list[str]:
        """Get list of webhook URLs."""
        if not self.webhook_urls:
            return []
        return [url.strip() for url in self.webhook_urls.split(",")]