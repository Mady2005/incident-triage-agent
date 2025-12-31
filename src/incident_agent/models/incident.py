"""Core incident model with validation and state management."""

from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from enum import Enum

from ..schemas import IncidentReport, TeamAssignment, ResolutionAction
from ..utils import generate_incident_id, current_timestamp, calculate_incident_priority_score


class IncidentSeverity(Enum):
    """Incident severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class IncidentStatus(Enum):
    """Incident resolution status."""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class Incident:
    """Core incident model with validation and state management."""
    
    def __init__(self, incident_report: IncidentReport):
        """Initialize incident from incident report."""
        self.report = incident_report
        self.severity: Optional[IncidentSeverity] = None
        self.status = IncidentStatus.OPEN
        self.team_assignments: List[TeamAssignment] = []
        self.resolution_actions: List[ResolutionAction] = []
        self.is_security_incident = False
        self.escalation_needed = False
        self.priority_score = 0
        self.created_at = incident_report.timestamp
        self.updated_at = current_timestamp()
        self.resolution_time: Optional[datetime] = None
        self.escalation_history: List[Dict[str, Any]] = []
        self.status_updates: List[Dict[str, Any]] = []
    
    def set_severity(self, severity: str, reasoning: str = "") -> None:
        """Set incident severity with validation."""
        try:
            self.severity = IncidentSeverity(severity)
            self.priority_score = calculate_incident_priority_score(
                severity, 
                len(self.report.affected_systems),
                self.is_security_incident
            )
            self.updated_at = current_timestamp()
            
            # Add status update
            self.status_updates.append({
                "timestamp": self.updated_at,
                "action": "severity_set",
                "details": {"severity": severity, "reasoning": reasoning}
            })
        except ValueError:
            raise ValueError(f"Invalid severity level: {severity}")
    
    def assign_team(self, team_assignment: TeamAssignment) -> None:
        """Assign a response team to the incident."""
        self.team_assignments.append(team_assignment)
        self.updated_at = current_timestamp()
        
        # Add status update
        self.status_updates.append({
            "timestamp": self.updated_at,
            "action": "team_assigned",
            "details": {
                "team": team_assignment.team_name,
                "reason": team_assignment.assignment_reason
            }
        })
    
    def add_resolution_action(self, action: ResolutionAction) -> None:
        """Add a suggested resolution action."""
        self.resolution_actions.append(action)
        self.updated_at = current_timestamp()
        
        # Add status update
        self.status_updates.append({
            "timestamp": self.updated_at,
            "action": "resolution_action_added",
            "details": {
                "action_type": action.action_type,
                "description": action.description
            }
        })
    
    def update_status(self, new_status: str, reason: str = "") -> None:
        """Update incident status."""
        try:
            old_status = self.status
            self.status = IncidentStatus(new_status)
            self.updated_at = current_timestamp()
            
            # Set resolution time if resolved
            if self.status == IncidentStatus.RESOLVED and old_status != IncidentStatus.RESOLVED:
                self.resolution_time = self.updated_at
            
            # Add status update
            self.status_updates.append({
                "timestamp": self.updated_at,
                "action": "status_updated",
                "details": {
                    "old_status": old_status.value,
                    "new_status": new_status,
                    "reason": reason
                }
            })
        except ValueError:
            raise ValueError(f"Invalid status: {new_status}")
    
    def escalate(self, escalation_reason: str, target_team: Optional[str] = None) -> None:
        """Escalate the incident."""
        self.escalation_needed = True
        self.updated_at = current_timestamp()
        
        escalation_record = {
            "timestamp": self.updated_at,
            "reason": escalation_reason,
            "target_team": target_team,
            "escalated_from": [ta.team_name for ta in self.team_assignments]
        }
        
        self.escalation_history.append(escalation_record)
        
        # Add status update
        self.status_updates.append({
            "timestamp": self.updated_at,
            "action": "escalated",
            "details": escalation_record
        })
    
    def mark_as_security_incident(self) -> None:
        """Mark incident as security-related."""
        self.is_security_incident = True
        self.updated_at = current_timestamp()
        
        # Recalculate priority score with security multiplier
        if self.severity:
            self.priority_score = calculate_incident_priority_score(
                self.severity.value,
                len(self.report.affected_systems),
                True
            )
        
        # Add status update
        self.status_updates.append({
            "timestamp": self.updated_at,
            "action": "marked_security_incident",
            "details": {"security_incident": True}
        })
    
    def get_assigned_teams(self) -> List[str]:
        """Get list of assigned team names."""
        return [ta.team_name for ta in self.team_assignments]
    
    def get_primary_team(self) -> Optional[str]:
        """Get the primary assigned team (highest priority)."""
        if not self.team_assignments:
            return None
        
        primary = min(self.team_assignments, key=lambda ta: ta.priority)
        return primary.team_name
    
    def get_resolution_time_minutes(self) -> Optional[int]:
        """Get resolution time in minutes."""
        if not self.resolution_time:
            return None
        
        delta = self.resolution_time - self.created_at
        return int(delta.total_seconds() / 60)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert incident to dictionary representation."""
        return {
            "id": self.report.id,
            "title": self.report.title,
            "description": self.report.description,
            "severity": self.severity.value if self.severity else None,
            "status": self.status.value,
            "assigned_teams": self.get_assigned_teams(),
            "is_security_incident": self.is_security_incident,
            "escalation_needed": self.escalation_needed,
            "priority_score": self.priority_score,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "resolution_time": self.resolution_time.isoformat() if self.resolution_time else None,
            "affected_systems": self.report.affected_systems,
            "reporter": self.report.reporter,
            "source": self.report.source
        }