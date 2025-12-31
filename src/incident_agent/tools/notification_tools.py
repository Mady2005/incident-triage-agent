"""Tools for sending notifications and formatting communications."""

from typing import Dict, Any, List, Optional
from datetime import datetime
from langchain_core.tools import tool

from ..notifications.slack_notifier import SlackNotifier
from ..utils import current_timestamp


@tool
def send_notification_tool(
    incident_id: str,
    message_type: str,
    incident_data: Dict[str, Any],
    channels: Optional[List[str]] = None,
    urgent: bool = False
) -> Dict[str, Any]:
    """
    Send notification about an incident.
    
    Args:
        incident_id: ID of the incident
        message_type: Type of notification (created, updated, escalated, resolved)
        incident_data: Incident data dictionary
        channels: Specific channels to notify (optional)
        urgent: Whether this is an urgent notification
        
    Returns:
        Dictionary with notification results
    """
    try:
        # Format notification message
        if message_type == "created":
            title = f"🚨 New Incident: {incident_data.get('title', 'Unknown')}"
            color = "danger" if incident_data.get('severity') == 'critical' else "warning"
        elif message_type == "updated":
            title = f"📝 Incident Updated: {incident_data.get('title', 'Unknown')}"
            color = "good"
        elif message_type == "escalated":
            title = f"⚠️ Incident Escalated: {incident_data.get('title', 'Unknown')}"
            color = "danger"
        elif message_type == "resolved":
            title = f"✅ Incident Resolved: {incident_data.get('title', 'Unknown')}"
            color = "good"
        else:
            title = f"📢 Incident Notification: {incident_data.get('title', 'Unknown')}"
            color = "warning"
        
        # Build notification payload
        notification = {
            "title": title,
            "incident_id": incident_id,
            "severity": incident_data.get("severity", "unknown"),
            "status": incident_data.get("status", "open"),
            "assigned_teams": incident_data.get("assigned_teams", []),
            "affected_systems": incident_data.get("affected_systems", []),
            "description": incident_data.get("description", ""),
            "timestamp": current_timestamp().isoformat(),
            "urgent": urgent,
            "color": color,
            "message_type": message_type
        }
        
        # Add specific fields based on message type
        if message_type == "escalated":
            notification["escalation_reason"] = incident_data.get("escalation_reason", "")
            notification["escalation_target"] = incident_data.get("escalation_target_team", "")
        
        if message_type == "resolved":
            notification["resolution_notes"] = incident_data.get("resolution_notes", "")
            notification["resolution_time"] = incident_data.get("resolved_at", "")
        
        # Simulate notification sending (in real implementation, would use actual notification service)
        print(f"📢 Sending {message_type} notification for incident {incident_id}")
        print(f"   Title: {title}")
        print(f"   Severity: {incident_data.get('severity')}")
        print(f"   Teams: {', '.join(incident_data.get('assigned_teams', []))}")
        if channels:
            print(f"   Channels: {', '.join(channels)}")
        
        return {
            "success": True,
            "incident_id": incident_id,
            "message": f"Notification sent for incident {incident_id}",
            "notification_type": message_type,
            "channels_notified": channels or ["default"],
            "timestamp": notification["timestamp"],
            "urgent": urgent
        }
        
    except Exception as e:
        return {
            "success": False,
            "incident_id": incident_id,
            "error": f"Failed to send notification: {str(e)}",
            "message_type": message_type
        }


@tool
def send_escalation_notification_tool(
    incident_id: str,
    escalation_reason: str,
    target_team: str,
    incident_data: Dict[str, Any],
    urgency_level: str = "high"
) -> Dict[str, Any]:
    """
    Send escalation notification for an incident.
    
    Args:
        incident_id: ID of the incident being escalated
        escalation_reason: Reason for escalation
        target_team: Team to escalate to
        incident_data: Current incident data
        urgency_level: Urgency of the escalation (low, medium, high, critical)
        
    Returns:
        Dictionary with escalation notification results
    """
    try:
        # Build escalation notification
        escalation_data = {
            **incident_data,
            "escalation_reason": escalation_reason,
            "escalation_target_team": target_team,
            "escalation_urgency": urgency_level,
            "escalated_at": current_timestamp().isoformat()
        }
        
        # Send escalation notification
        result = send_notification_tool(
            incident_id=incident_id,
            message_type="escalated",
            incident_data=escalation_data,
            channels=[f"#{target_team}", "#management"],
            urgent=(urgency_level in ["high", "critical"])
        )
        
        # Add escalation-specific information
        if result["success"]:
            result["incident_id"] = incident_id
            result["escalation_details"] = {
                "reason": escalation_reason,
                "target_team": target_team,
                "urgency_level": urgency_level,
                "escalated_at": escalation_data["escalated_at"]
            }
        
        return result
        
    except Exception as e:
        return {
            "success": False,
            "incident_id": incident_id,
            "error": f"Failed to send escalation notification: {str(e)}",
            "escalation_reason": escalation_reason
        }


@tool
def format_status_update_tool(
    incident_id: str,
    incident_data: Dict[str, Any],
    update_type: str = "progress",
    audience: str = "technical"
) -> Dict[str, Any]:
    """
    Format a status update message for different audiences.
    
    Args:
        incident_id: ID of the incident
        incident_data: Current incident data
        update_type: Type of update (progress, resolution, escalation)
        audience: Target audience (technical, management, customer)
        
    Returns:
        Dictionary with formatted status update
    """
    try:
        timestamp = current_timestamp().isoformat()
        
        # Base information
        title = incident_data.get("title", "Unknown Incident")
        severity = incident_data.get("severity", "unknown")
        status = incident_data.get("status", "open")
        teams = incident_data.get("assigned_teams", [])
        affected_systems = incident_data.get("affected_systems", [])
        
        # Format based on audience
        if audience == "technical":
            message = f"""
**Incident Update: {incident_id}**

**Title:** {title}
**Severity:** {severity.upper()}
**Status:** {status.upper()}
**Assigned Teams:** {', '.join(teams) if teams else 'None'}
**Affected Systems:** {', '.join(affected_systems) if affected_systems else 'None'}

**Current Actions:**
{chr(10).join(f"• {action}" for action in incident_data.get('suggested_actions', ['No actions specified']))}

**Timeline:**
{chr(10).join(f"• {event.get('timestamp', '')}: {event.get('details', '')}" for event in incident_data.get('timeline', [])[-3:])}

**Next Steps:**
• Continue monitoring system metrics
• Implement suggested resolution actions
• Update status as progress is made

*Last Updated: {timestamp}*
            """.strip()
            
        elif audience == "management":
            impact_description = "Multiple systems affected" if len(affected_systems) > 1 else "Single system affected"
            eta_message = "ETA for resolution: Under investigation" if status == "open" else f"Status: {status}"
            
            message = f"""
**Executive Summary - Incident {incident_id}**

**Issue:** {title}
**Impact Level:** {severity.upper()}
**Business Impact:** {impact_description}
**Response Status:** {status.upper()}

**Response Team:** {', '.join(teams) if teams else 'Being assigned'}
**{eta_message}**

**Key Actions Taken:**
{chr(10).join(f"• {action}" for action in incident_data.get('suggested_actions', ['Response team mobilized'])[:3])}

**Communication:** Technical teams are actively working on resolution. Updates will be provided every 30 minutes for critical incidents.

*Report Generated: {timestamp}*
            """.strip()
            
        elif audience == "customer":
            customer_impact = "service disruption" if severity in ["critical", "high"] else "potential service impact"
            
            message = f"""
**Service Status Update**

We are currently investigating {customer_impact} that may affect your experience with our services.

**What we know:**
• Issue identified at {incident_data.get('created_at', timestamp)}
• Our engineering team is actively working on a resolution
• Affected services: {', '.join(affected_systems) if affected_systems else 'Under investigation'}

**What we're doing:**
• Implementing immediate mitigation measures
• Monitoring system performance closely
• Preparing additional resources if needed

We will provide updates every hour until this issue is resolved. We apologize for any inconvenience.

*Last Updated: {timestamp}*
            """.strip()
            
        else:
            # Default format
            message = f"""
Incident {incident_id}: {title}
Severity: {severity} | Status: {status}
Teams: {', '.join(teams) if teams else 'None'}
Updated: {timestamp}
            """.strip()
        
        return {
            "success": True,
            "incident_id": incident_id,
            "formatted_message": message,
            "audience": audience,
            "update_type": update_type,
            "timestamp": timestamp,
            "character_count": len(message)
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to format status update: {str(e)}",
            "incident_id": incident_id,
            "audience": audience
        }


@tool
def send_status_broadcast_tool(
    incident_id: str,
    incident_data: Dict[str, Any],
    audiences: List[str] = ["technical"],
    channels: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Send status update to multiple audiences and channels.
    
    Args:
        incident_id: ID of the incident
        incident_data: Current incident data
        audiences: List of audiences to notify (technical, management, customer)
        channels: Specific channels to broadcast to
        
    Returns:
        Dictionary with broadcast results
    """
    try:
        results = []
        
        for audience in audiences:
            # Format message for this audience
            format_result = format_status_update_tool(
                incident_id=incident_id,
                incident_data=incident_data,
                update_type="progress",
                audience=audience
            )
            
            if format_result["success"]:
                # Send notification with formatted message
                notification_result = send_notification_tool(
                    incident_id=incident_id,
                    message_type="updated",
                    incident_data={
                        **incident_data,
                        "formatted_message": format_result["formatted_message"],
                        "audience": audience
                    },
                    channels=channels,
                    urgent=(incident_data.get("severity") == "critical")
                )
                
                results.append({
                    "audience": audience,
                    "success": notification_result["success"],
                    "message": format_result["formatted_message"][:100] + "..." if len(format_result["formatted_message"]) > 100 else format_result["formatted_message"]
                })
            else:
                results.append({
                    "audience": audience,
                    "success": False,
                    "error": format_result.get("error", "Unknown error")
                })
        
        successful_broadcasts = sum(1 for r in results if r["success"])
        
        return {
            "success": successful_broadcasts > 0,
            "incident_id": incident_id,
            "total_audiences": len(audiences),
            "successful_broadcasts": successful_broadcasts,
            "results": results,
            "timestamp": current_timestamp().isoformat()
        }
        
    except Exception as e:
        return {
            "success": False,
            "incident_id": incident_id,
            "error": f"Failed to send status broadcast: {str(e)}",
            "audiences": audiences
        }