"""Enhanced incident agent with Slack notification support."""

from typing import Literal, List, Dict, Any
from datetime import datetime
import os
import asyncio

from langchain.chat_models import init_chat_model
from langgraph.graph import StateGraph, START, END
from langgraph.types import Command
from dotenv import load_dotenv

from .schemas import IncidentState, StateInput
from .incident_agent import (
    triage_incident, 
    route_to_team, 
    coordinate_response,
    triage_router,
    team_registry
)
from .notifications.slack_notifier import SlackNotifier
from .utils import current_timestamp

load_dotenv(".env")

# Initialize Slack notifier if configured
slack_config = {
    "webhook_url": os.getenv("SLACK_WEBHOOK_URL"),
    "default_channel": os.getenv("SLACK_DEFAULT_CHANNEL", "#incidents"),
    "team_channels": {
        "sre": os.getenv("SLACK_SRE_CHANNEL", "#sre"),
        "backend": os.getenv("SLACK_BACKEND_CHANNEL", "#backend"),
        "frontend": os.getenv("SLACK_FRONTEND_CHANNEL", "#frontend"),
        "security": os.getenv("SLACK_SECURITY_CHANNEL", "#security"),
        "infrastructure": os.getenv("SLACK_INFRA_CHANNEL", "#infrastructure"),
        "oncall": os.getenv("SLACK_ONCALL_CHANNEL", "#oncall"),
        "management": os.getenv("SLACK_MGMT_CHANNEL", "#management")
    },
    "enabled": bool(os.getenv("SLACK_WEBHOOK_URL"))
}

slack_notifier = SlackNotifier(slack_config) if slack_config["enabled"] else None


async def send_notification_async(incident_data: Dict[str, Any], message_type: str = "created"):
    """Send Slack notification asynchronously."""
    if not slack_notifier or not slack_notifier.is_enabled():
        return
    
    try:
        if slack_notifier.should_notify(incident_data, message_type):
            message = slack_notifier.format_incident_message(incident_data, message_type)
            await slack_notifier.send_notification(message)
    except Exception as e:
        print(f"⚠️  Notification failed: {str(e)}")


def send_notification(incident_data: Dict[str, Any], message_type: str = "created"):
    """Send Slack notification synchronously."""
    try:
        asyncio.run(send_notification_async(incident_data, message_type))
    except Exception as e:
        print(f"⚠️  Notification failed: {str(e)}")


def triage_incident_with_notifications(state: IncidentState) -> Command[Literal["route_to_team", "__end__"]]:
    """Enhanced triage with notification support."""
    # Run original triage logic
    command = triage_incident(state)
    
    # Send notification for new incident
    if command.goto == "route_to_team":
        incident_data = {
            "incident_id": command.update.get("incident_id"),
            "severity": command.update.get("severity_classification"),
            "title": state["incident_input"].get("title", "Unknown Incident"),
            "description": state["incident_input"].get("description", ""),
            "affected_systems": state["incident_input"].get("affected_systems", []),
            "escalation_needed": command.update.get("escalation_needed", False),
            "assigned_teams": [],  # Will be set in routing
            "created_at": command.update.get("created_at"),
            "is_security_incident": False  # Will be determined in triage
        }
        
        # Send notification in background
        try:
            send_notification(incident_data, "created")
        except Exception as e:
            print(f"⚠️  Failed to send creation notification: {str(e)}")
    
    return command


def route_to_team_with_notifications(state: IncidentState) -> Command[Literal["coordinate_response", "__end__"]]:
    """Enhanced team routing with notification support."""
    # Run original routing logic
    command = route_to_team(state)
    
    # Send notification with team assignment
    if command.goto == "coordinate_response":
        incident_data = {
            "incident_id": state.get("incident_id"),
            "severity": state.get("severity_classification"),
            "title": state["incident_input"].get("title", "Unknown Incident"),
            "description": state["incident_input"].get("description", ""),
            "affected_systems": state["incident_input"].get("affected_systems", []),
            "assigned_teams": command.update.get("team_assignment", []),
            "escalation_needed": state.get("escalation_needed", False),
            "updated_at": command.update.get("updated_at"),
            "is_security_incident": False  # Could be enhanced to detect this
        }
        
        # Send team assignment notification
        try:
            send_notification(incident_data, "updated")
        except Exception as e:
            print(f"⚠️  Failed to send team assignment notification: {str(e)}")
    
    return command


def coordinate_response_with_notifications(state: IncidentState) -> Command[Literal["__end__"]]:
    """Enhanced response coordination with notification support."""
    # Run original coordination logic
    command = coordinate_response(state)
    
    # Send final notification with actions
    incident_data = {
        "incident_id": state.get("incident_id"),
        "severity": state.get("severity_classification"),
        "title": state["incident_input"].get("title", "Unknown Incident"),
        "description": state["incident_input"].get("description", ""),
        "affected_systems": state["incident_input"].get("affected_systems", []),
        "assigned_teams": state.get("team_assignment", []),
        "suggested_actions": command.update.get("suggested_actions", []),
        "escalation_needed": state.get("escalation_needed", False),
        "status": command.update.get("resolution_status", "in_progress"),
        "updated_at": command.update.get("updated_at"),
        "is_security_incident": False
    }
    
    # Send escalation notification if needed
    if state.get("escalation_needed", False):
        try:
            send_notification(incident_data, "escalated")
        except Exception as e:
            print(f"⚠️  Failed to send escalation notification: {str(e)}")
    
    return command


def build_incident_agent_with_notifications():
    """Build incident agent with Slack notification support."""
    
    workflow = StateGraph(IncidentState, input_schema=StateInput)
    
    # Add enhanced nodes with notifications
    workflow.add_node("triage_incident", triage_incident_with_notifications)
    workflow.add_node("route_to_team", route_to_team_with_notifications)
    workflow.add_node("coordinate_response", coordinate_response_with_notifications)
    
    # Add edges
    workflow.add_edge(START, "triage_incident")
    
    return workflow.compile()


# Create the enhanced agent
incident_agent_with_notifications = build_incident_agent_with_notifications()


def process_incident_with_notifications(incident_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process an incident with Slack notifications.
    
    Args:
        incident_data: Raw incident data dictionary
        
    Returns:
        Final state with processing results
    """
    print(f"🚨 Processing incident with notifications: {incident_data.get('title', 'Unknown')}")
    
    if slack_notifier and slack_notifier.is_enabled():
        print(f"📢 Slack notifications enabled")
    else:
        print(f"📢 Slack notifications disabled (set SLACK_WEBHOOK_URL to enable)")
    
    # Run the enhanced workflow
    result = incident_agent_with_notifications.invoke({
        "incident_input": incident_data
    })
    
    # Extract key results
    response = {
        "incident_id": result.get("incident_id"),
        "severity": result.get("severity_classification"),
        "assigned_teams": result.get("team_assignment", []),
        "suggested_actions": result.get("suggested_actions", []),
        "escalation_needed": result.get("escalation_needed", False),
        "status": result.get("resolution_status", "open"),
        "created_at": result.get("created_at"),
        "updated_at": result.get("updated_at"),
        "notifications_sent": slack_notifier.is_enabled() if slack_notifier else False
    }
    
    print(f"✅ Incident {response['incident_id']} processed with notifications")
    return response


def send_test_slack_notification() -> bool:
    """Send a test Slack notification."""
    if not slack_notifier:
        print("❌ Slack notifier not configured. Set SLACK_WEBHOOK_URL environment variable.")
        return False
    
    print("🧪 Sending test Slack notification...")
    return slack_notifier.send_test_notification()


def escalate_incident_with_notification(
    incident_id: str, 
    escalation_reason: str,
    incident_data: Dict[str, Any]
) -> bool:
    """
    Escalate an incident and send notification.
    
    Args:
        incident_id: ID of the incident to escalate
        escalation_reason: Reason for escalation
        incident_data: Current incident data
        
    Returns:
        True if escalation notification was sent
    """
    # Update incident data with escalation info
    escalated_data = {
        **incident_data,
        "escalation_needed": True,
        "escalation_reason": escalation_reason,
        "escalated_at": current_timestamp(),
        "updated_at": current_timestamp()
    }
    
    # Send escalation notification
    try:
        send_notification(escalated_data, "escalated")
        print(f"📢 Escalation notification sent for incident {incident_id}")
        return True
    except Exception as e:
        print(f"❌ Failed to send escalation notification: {str(e)}")
        return False


if __name__ == "__main__":
    # Test the enhanced agent
    sample_incident = {
        "id": "NOTIF-001",
        "title": "Critical database connection failure",
        "description": "All database connections are failing, affecting user authentication and data access",
        "source": "monitoring",
        "timestamp": datetime.now().isoformat(),
        "reporter": "monitoring-system",
        "affected_systems": ["database", "auth", "api"],
        "error_logs": "Connection timeout after 30 seconds",
        "severity_indicators": ["critical", "outage", "database", "timeout"]
    }
    
    # Test Slack configuration
    if slack_notifier:
        print("🧪 Testing Slack configuration...")
        if slack_notifier.validate_config():
            print("✅ Slack configuration valid")
            # Uncomment to send test notification
            # send_test_slack_notification()
        else:
            print("❌ Slack configuration invalid")
    
    # Process incident with notifications
    result = process_incident_with_notifications(sample_incident)
    print("\n📊 Processing Result:")
    for key, value in result.items():
        print(f"  {key}: {value}")