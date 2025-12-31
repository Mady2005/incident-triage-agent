"""Tools for incident creation, updates, and status management."""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import uuid
from langchain_core.tools import tool

from ..utils import current_timestamp
from ..schemas import IncidentStatus


# In-memory incident store (would be replaced with database in production)
_incident_store: Dict[str, Dict[str, Any]] = {}


@tool
def create_incident_tool(
    title: str,
    description: str,
    severity: str,
    affected_systems: List[str],
    reporter: str = "system",
    source: str = "agent"
) -> Dict[str, Any]:
    """
    Create a new incident record.
    
    Args:
        title: Brief title describing the incident
        description: Detailed description of the incident
        severity: Incident severity (critical, high, medium, low)
        affected_systems: List of affected systems/components
        reporter: Person or system reporting the incident
        source: Source of the incident report
        
    Returns:
        Dictionary with incident details including generated ID
    """
    incident_id = f"INC-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8]}"
    timestamp = current_timestamp().isoformat()
    
    incident = {
        "incident_id": incident_id,
        "title": title,
        "description": description,
        "severity": severity,
        "status": "open",
        "affected_systems": affected_systems,
        "reporter": reporter,
        "source": source,
        "created_at": timestamp,
        "updated_at": timestamp,
        "assigned_teams": [],
        "suggested_actions": [],
        "escalation_needed": False,
        "resolution_notes": "",
        "timeline": [
            {
                "timestamp": timestamp,
                "event": "incident_created",
                "details": f"Incident created by {reporter}",
                "severity": severity
            }
        ]
    }
    
    _incident_store[incident_id] = incident
    
    return {
        "success": True,
        "incident_id": incident_id,
        "message": f"Incident {incident_id} created successfully",
        "incident": incident
    }


@tool
def update_incident_tool(
    incident_id: str,
    status: Optional[str] = None,
    severity: Optional[str] = None,
    assigned_teams: Optional[List[str]] = None,
    resolution_notes: Optional[str] = None,
    add_timeline_event: Optional[str] = None
) -> Dict[str, Any]:
    """
    Update an existing incident.
    
    Args:
        incident_id: ID of the incident to update
        status: New status (open, in_progress, resolved, closed)
        severity: New severity level
        assigned_teams: List of teams assigned to the incident
        resolution_notes: Notes about resolution progress
        add_timeline_event: Event description to add to timeline
        
    Returns:
        Dictionary with update results
    """
    if incident_id not in _incident_store:
        return {
            "success": False,
            "error": f"Incident {incident_id} not found"
        }
    
    incident = _incident_store[incident_id]
    timestamp = current_timestamp().isoformat()
    changes = []
    
    # Update fields if provided
    if status is not None:
        old_status = incident["status"]
        incident["status"] = status
        changes.append(f"status: {old_status} → {status}")
        
        # Add timeline event for status change
        incident["timeline"].append({
            "timestamp": timestamp,
            "event": "status_changed",
            "details": f"Status changed from {old_status} to {status}",
            "old_value": old_status,
            "new_value": status
        })
    
    if severity is not None:
        old_severity = incident["severity"]
        incident["severity"] = severity
        changes.append(f"severity: {old_severity} → {severity}")
        
        # Add timeline event for severity change
        incident["timeline"].append({
            "timestamp": timestamp,
            "event": "severity_changed",
            "details": f"Severity changed from {old_severity} to {severity}",
            "old_value": old_severity,
            "new_value": severity
        })
    
    if assigned_teams is not None:
        old_teams = incident["assigned_teams"]
        incident["assigned_teams"] = assigned_teams
        changes.append(f"assigned_teams: {old_teams} → {assigned_teams}")
        
        # Add timeline event for team assignment
        incident["timeline"].append({
            "timestamp": timestamp,
            "event": "teams_assigned",
            "details": f"Teams assigned: {', '.join(assigned_teams)}",
            "teams": assigned_teams
        })
    
    if resolution_notes is not None:
        incident["resolution_notes"] = resolution_notes
        changes.append("resolution_notes updated")
        
        # Add timeline event for resolution notes
        incident["timeline"].append({
            "timestamp": timestamp,
            "event": "resolution_notes_added",
            "details": "Resolution notes updated",
            "notes": resolution_notes
        })
    
    if add_timeline_event is not None:
        incident["timeline"].append({
            "timestamp": timestamp,
            "event": "custom_event",
            "details": add_timeline_event
        })
        changes.append("timeline event added")
    
    # Update timestamp
    incident["updated_at"] = timestamp
    
    return {
        "success": True,
        "incident_id": incident_id,
        "message": f"Incident {incident_id} updated: {', '.join(changes)}",
        "changes": changes,
        "incident": incident
    }


@tool
def get_incident_status_tool(incident_id: str) -> Dict[str, Any]:
    """
    Get current status and details of an incident.
    
    Args:
        incident_id: ID of the incident to retrieve
        
    Returns:
        Dictionary with incident status and details
    """
    if incident_id not in _incident_store:
        return {
            "success": False,
            "error": f"Incident {incident_id} not found"
        }
    
    incident = _incident_store[incident_id]
    
    # Calculate incident age
    created_at = datetime.fromisoformat(incident["created_at"])
    # Ensure both datetimes have timezone info for comparison
    now = datetime.now(timezone.utc) if created_at.tzinfo else datetime.now()
    age_hours = (now - created_at).total_seconds() / 3600
    
    # Get latest timeline event
    latest_event = incident["timeline"][-1] if incident["timeline"] else None
    
    return {
        "success": True,
        "incident_id": incident_id,
        "status": incident["status"],
        "severity": incident["severity"],
        "title": incident["title"],
        "assigned_teams": incident["assigned_teams"],
        "age_hours": round(age_hours, 2),
        "escalation_needed": incident.get("escalation_needed", False),
        "affected_systems": incident["affected_systems"],
        "latest_event": latest_event,
        "timeline_count": len(incident["timeline"]),
        "created_at": incident["created_at"],
        "updated_at": incident["updated_at"]
    }


@tool
def list_incidents_tool(
    status_filter: Optional[str] = None,
    severity_filter: Optional[str] = None,
    team_filter: Optional[str] = None,
    limit: int = 10
) -> Dict[str, Any]:
    """
    List incidents with optional filtering.
    
    Args:
        status_filter: Filter by status (open, in_progress, resolved, closed)
        severity_filter: Filter by severity (critical, high, medium, low)
        team_filter: Filter by assigned team
        limit: Maximum number of incidents to return
        
    Returns:
        Dictionary with list of matching incidents
    """
    incidents = []
    
    for incident_id, incident in _incident_store.items():
        # Apply filters
        if status_filter and incident["status"] != status_filter:
            continue
        if severity_filter and incident["severity"] != severity_filter:
            continue
        if team_filter and team_filter not in incident["assigned_teams"]:
            continue
        
        # Calculate incident age
        created_at = datetime.fromisoformat(incident["created_at"])
        # Ensure both datetimes have timezone info for comparison
        now = datetime.now(timezone.utc) if created_at.tzinfo else datetime.now()
        age_hours = (now - created_at).total_seconds() / 3600
        
        incidents.append({
            "incident_id": incident_id,
            "title": incident["title"],
            "status": incident["status"],
            "severity": incident["severity"],
            "assigned_teams": incident["assigned_teams"],
            "age_hours": round(age_hours, 2),
            "affected_systems": incident["affected_systems"],
            "escalation_needed": incident.get("escalation_needed", False),
            "created_at": incident["created_at"],
            "updated_at": incident["updated_at"]
        })
    
    # Sort by creation time (newest first)
    incidents.sort(key=lambda x: x["created_at"], reverse=True)
    
    # Apply limit
    incidents = incidents[:limit]
    
    return {
        "success": True,
        "total_found": len(incidents),
        "incidents": incidents,
        "filters_applied": {
            "status": status_filter,
            "severity": severity_filter,
            "team": team_filter,
            "limit": limit
        }
    }


@tool
def get_incident_timeline_tool(incident_id: str) -> Dict[str, Any]:
    """
    Get detailed timeline for an incident.
    
    Args:
        incident_id: ID of the incident
        
    Returns:
        Dictionary with incident timeline
    """
    if incident_id not in _incident_store:
        return {
            "success": False,
            "error": f"Incident {incident_id} not found"
        }
    
    incident = _incident_store[incident_id]
    
    return {
        "success": True,
        "incident_id": incident_id,
        "title": incident["title"],
        "timeline": incident["timeline"],
        "timeline_count": len(incident["timeline"]),
        "created_at": incident["created_at"],
        "updated_at": incident["updated_at"]
    }


def get_all_incidents() -> Dict[str, Dict[str, Any]]:
    """Get all incidents (for internal use)."""
    return _incident_store.copy()


def clear_incidents_store():
    """Clear all incidents (for testing)."""
    global _incident_store
    _incident_store.clear()