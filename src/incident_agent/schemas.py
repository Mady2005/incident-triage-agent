"""Core data models and schemas for the incident triage agent."""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from typing_extensions import TypedDict, Literal
from langgraph.graph import MessagesState


class IncidentReport(BaseModel):
    """Structured incident report data."""
    
    id: str
    title: str
    description: str
    source: Literal["monitoring", "user_report", "api", "chat"]
    timestamp: datetime
    reporter: str
    affected_systems: List[str]
    error_logs: Optional[str] = None
    metrics_data: Optional[Dict[str, Any]] = None
    severity_indicators: List[str] = Field(default_factory=list)


class TeamAssignment(BaseModel):
    """Team assignment information for incident response."""
    
    team_name: str
    assignment_reason: str
    priority: int
    escalation_path: List[str]
    estimated_response_time: int  # minutes


class ResolutionAction(BaseModel):
    """Suggested resolution action for incident response."""
    
    action_type: Literal["diagnostic", "fix", "communication", "escalation"]
    description: str
    priority: int
    estimated_duration: int  # minutes
    required_permissions: List[str] = Field(default_factory=list)
    runbook_reference: Optional[str] = None


class IncidentState(MessagesState):
    """State schema for incident processing workflow."""
    
    incident_input: dict  # Raw incident data
    severity_classification: Optional[Literal["critical", "high", "medium", "low"]] = None
    team_assignment: List[str] = Field(default_factory=list)  # Assigned response teams
    suggested_actions: List[str] = Field(default_factory=list)  # Recommended next steps
    escalation_needed: bool = False
    resolution_status: Literal["open", "in_progress", "resolved", "closed"] = "open"
    incident_id: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class SeverityClassificationSchema(BaseModel):
    """Schema for LLM-based severity classification."""
    
    reasoning: str = Field(
        description="Step-by-step reasoning behind the severity classification."
    )
    severity: Literal["critical", "high", "medium", "low"] = Field(
        description="The severity level of the incident based on impact and urgency."
    )
    security_incident: bool = Field(
        description="Whether this incident has security implications."
    )
    affected_systems: List[str] = Field(
        description="List of systems or components affected by this incident."
    )


class TeamRoutingSchema(BaseModel):
    """Schema for team routing decisions."""
    
    reasoning: str = Field(
        description="Step-by-step reasoning behind the team assignment."
    )
    primary_team: str = Field(
        description="Primary response team for this incident."
    )
    secondary_teams: List[str] = Field(
        description="Additional teams that should be involved.",
        default_factory=list
    )
    escalation_needed: bool = Field(
        description="Whether immediate escalation is required."
    )


# API Response Models
class IncidentResponse(BaseModel):
    """Response model for incident creation and updates."""
    
    incident_id: str
    status: str
    message: str
    assigned_teams: List[str]
    suggested_actions: List[ResolutionAction]
    created_at: datetime
    updated_at: datetime


class IncidentStatus(BaseModel):
    """Response model for incident status queries."""
    
    incident_id: str
    current_status: Literal["open", "in_progress", "resolved", "closed"]
    severity: Literal["critical", "high", "medium", "low"]
    assigned_teams: List[str]
    progress_summary: str
    estimated_resolution: Optional[datetime] = None


class SeverityUpdate(BaseModel):
    """Request model for severity updates."""
    
    new_severity: Literal["critical", "high", "medium", "low"]
    reason: str
    updated_by: str


class EscalationRequest(BaseModel):
    """Request model for incident escalation."""
    
    escalation_reason: str
    target_team: Optional[str] = None
    urgency_level: Literal["immediate", "urgent", "normal"]
    additional_context: Optional[str] = None


class IncidentSummary(BaseModel):
    """Summary model for incident listings."""
    
    incident_id: str
    title: str
    severity: Literal["critical", "high", "medium", "low"]
    status: Literal["open", "in_progress", "resolved", "closed"]
    assigned_teams: List[str]
    created_at: datetime
    updated_at: datetime


# Input Types
class StateInput(TypedDict):
    """Input to the incident processing state."""
    incident_input: dict


class IncidentData(TypedDict):
    """Raw incident data structure."""
    id: str
    title: str
    description: str
    source: str
    timestamp: str
    reporter: str
    affected_systems: List[str]
    error_logs: Optional[str]
    metrics_data: Optional[Dict[str, Any]]