"""FastAPI application for the Incident Triage Agent."""

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from ..incident_agent import process_incident
from ..schemas import (
    IncidentReport, 
    IncidentResponse, 
    IncidentStatus, 
    SeverityUpdate, 
    EscalationRequest,
    IncidentSummary
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Incident Triage Agent API",
    description="Intelligent incident triage and response coordination system",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for MVP (replace with database in production)
incidents_store: Dict[str, Dict[str, Any]] = {}


# Request/Response Models
class CreateIncidentRequest(BaseModel):
    """Request model for creating incidents."""
    title: str = Field(..., description="Brief title describing the incident")
    description: str = Field(..., description="Detailed description of the incident")
    source: str = Field(..., description="Source of the incident report")
    reporter: str = Field(..., description="Person or system reporting the incident")
    affected_systems: List[str] = Field(default_factory=list, description="List of affected systems")
    error_logs: Optional[str] = Field(None, description="Relevant error logs")
    metrics_data: Optional[Dict[str, Any]] = Field(None, description="Relevant metrics data")
    severity_indicators: List[str] = Field(default_factory=list, description="Keywords indicating severity")


class IncidentResponseModel(BaseModel):
    """Response model for incident operations."""
    incident_id: str
    status: str
    message: str
    severity: str
    assigned_teams: List[str]
    suggested_actions: List[str]
    escalation_needed: bool
    created_at: datetime
    updated_at: datetime


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    timestamp: datetime
    version: str


# API Endpoints

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(),
        version="1.0.0"
    )


@app.post("/incidents/", response_model=IncidentResponseModel, status_code=status.HTTP_201_CREATED)
async def create_incident(request: CreateIncidentRequest):
    """
    Create and process a new incident.
    
    This endpoint:
    1. Accepts incident data
    2. Processes it through the triage workflow
    3. Returns the processing results
    """
    try:
        logger.info(f"Creating incident: {request.title}")
        
        # Convert request to incident data format
        incident_data = {
            "id": f"API-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            "title": request.title,
            "description": request.description,
            "source": request.source,
            "timestamp": datetime.now().isoformat(),
            "reporter": request.reporter,
            "affected_systems": request.affected_systems,
            "error_logs": request.error_logs,
            "metrics_data": request.metrics_data,
            "severity_indicators": request.severity_indicators
        }
        
        # Process through incident agent
        result = process_incident(incident_data)
        
        # Store in memory for retrieval
        incidents_store[result["incident_id"]] = {
            **incident_data,
            **result,
            "original_request": request.model_dump()
        }
        
        logger.info(f"Incident {result['incident_id']} created successfully")
        
        return IncidentResponseModel(
            incident_id=result["incident_id"],
            status="created",
            message="Incident created and processed successfully",
            severity=result["severity"],
            assigned_teams=result["assigned_teams"],
            suggested_actions=result["suggested_actions"],
            escalation_needed=result["escalation_needed"],
            created_at=result["created_at"],
            updated_at=result["updated_at"]
        )
        
    except Exception as e:
        logger.error(f"Error creating incident: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create incident: {str(e)}"
        )


@app.get("/incidents/{incident_id}", response_model=Dict[str, Any])
async def get_incident(incident_id: str):
    """
    Get incident details by ID.
    
    Returns complete incident information including processing results.
    """
    if incident_id not in incidents_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident {incident_id} not found"
        )
    
    incident = incidents_store[incident_id]
    logger.info(f"Retrieved incident: {incident_id}")
    
    return {
        "incident_id": incident_id,
        "title": incident.get("title"),
        "description": incident.get("description"),
        "severity": incident.get("severity"),
        "status": incident.get("status", "open"),
        "assigned_teams": incident.get("assigned_teams", []),
        "suggested_actions": incident.get("suggested_actions", []),
        "escalation_needed": incident.get("escalation_needed", False),
        "affected_systems": incident.get("affected_systems", []),
        "created_at": incident.get("created_at"),
        "updated_at": incident.get("updated_at"),
        "reporter": incident.get("reporter"),
        "source": incident.get("source")
    }


@app.get("/incidents/", response_model=List[Dict[str, Any]])
async def list_incidents(
    status_filter: Optional[str] = None,
    team_filter: Optional[str] = None,
    severity_filter: Optional[str] = None,
    limit: int = 50
):
    """
    List incidents with optional filtering.
    
    Query parameters:
    - status: Filter by incident status
    - team: Filter by assigned team
    - severity: Filter by severity level
    - limit: Maximum number of incidents to return
    """
    incidents = []
    
    for incident_id, incident_data in incidents_store.items():
        # Apply filters
        if status_filter and incident_data.get("status") != status_filter:
            continue
        if team_filter and team_filter not in incident_data.get("assigned_teams", []):
            continue
        if severity_filter and incident_data.get("severity") != severity_filter:
            continue
        
        incidents.append({
            "incident_id": incident_id,
            "title": incident_data.get("title"),
            "severity": incident_data.get("severity"),
            "status": incident_data.get("status", "open"),
            "assigned_teams": incident_data.get("assigned_teams", []),
            "created_at": incident_data.get("created_at"),
            "updated_at": incident_data.get("updated_at"),
            "escalation_needed": incident_data.get("escalation_needed", False)
        })
    
    # Sort by creation time (newest first) and limit
    incidents.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    logger.info(f"Listed {len(incidents[:limit])} incidents")
    return incidents[:limit]


@app.put("/incidents/{incident_id}/severity", response_model=Dict[str, Any])
async def update_incident_severity(incident_id: str, update: SeverityUpdate):
    """
    Update incident severity.
    
    This endpoint allows manual severity adjustments by operators.
    """
    if incident_id not in incidents_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident {incident_id} not found"
        )
    
    incident = incidents_store[incident_id]
    old_severity = incident.get("severity")
    
    # Update severity
    incident["severity"] = update.new_severity
    incident["updated_at"] = datetime.now()
    incident["severity_update_reason"] = update.reason
    incident["severity_updated_by"] = update.updated_by
    
    logger.info(f"Updated incident {incident_id} severity from {old_severity} to {update.new_severity}")
    
    return {
        "incident_id": incident_id,
        "message": f"Severity updated from {old_severity} to {update.new_severity}",
        "old_severity": old_severity,
        "new_severity": update.new_severity,
        "reason": update.reason,
        "updated_by": update.updated_by,
        "updated_at": incident["updated_at"]
    }


@app.post("/incidents/{incident_id}/escalate", response_model=Dict[str, Any])
async def escalate_incident(incident_id: str, escalation: EscalationRequest):
    """
    Escalate an incident.
    
    This endpoint triggers escalation procedures for an incident.
    """
    if incident_id not in incidents_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident {incident_id} not found"
        )
    
    incident = incidents_store[incident_id]
    
    # Update escalation status
    incident["escalation_needed"] = True
    incident["escalation_reason"] = escalation.escalation_reason
    incident["escalation_urgency"] = escalation.urgency_level
    incident["escalation_target_team"] = escalation.target_team
    incident["escalation_context"] = escalation.additional_context
    incident["escalated_at"] = datetime.now()
    incident["updated_at"] = datetime.now()
    
    logger.info(f"Escalated incident {incident_id}: {escalation.escalation_reason}")
    
    return {
        "incident_id": incident_id,
        "message": "Incident escalated successfully",
        "escalation_reason": escalation.escalation_reason,
        "urgency_level": escalation.urgency_level,
        "target_team": escalation.target_team,
        "escalated_at": incident["escalated_at"]
    }


@app.get("/incidents/{incident_id}/status", response_model=Dict[str, Any])
async def get_incident_status(incident_id: str):
    """
    Get current incident status.
    
    Returns a focused view of incident status for monitoring systems.
    """
    if incident_id not in incidents_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident {incident_id} not found"
        )
    
    incident = incidents_store[incident_id]
    
    return {
        "incident_id": incident_id,
        "current_status": incident.get("status", "open"),
        "severity": incident.get("severity"),
        "assigned_teams": incident.get("assigned_teams", []),
        "escalation_needed": incident.get("escalation_needed", False),
        "progress_summary": f"Incident assigned to {', '.join(incident.get('assigned_teams', []))}",
        "created_at": incident.get("created_at"),
        "updated_at": incident.get("updated_at"),
        "suggested_actions_count": len(incident.get("suggested_actions", []))
    }


@app.get("/stats", response_model=Dict[str, Any])
async def get_system_stats():
    """
    Get system statistics.
    
    Returns overview statistics about incident processing.
    """
    total_incidents = len(incidents_store)
    
    if total_incidents == 0:
        return {
            "total_incidents": 0,
            "severity_distribution": {},
            "team_workload": {},
            "escalation_rate": 0.0
        }
    
    # Calculate statistics
    severity_counts = {}
    team_assignments = {}
    escalated_count = 0
    
    for incident in incidents_store.values():
        # Severity distribution
        severity = incident.get("severity", "unknown")
        severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        # Team workload
        for team in incident.get("assigned_teams", []):
            team_assignments[team] = team_assignments.get(team, 0) + 1
        
        # Escalation rate
        if incident.get("escalation_needed", False):
            escalated_count += 1
    
    return {
        "total_incidents": total_incidents,
        "severity_distribution": severity_counts,
        "team_workload": team_assignments,
        "escalation_rate": round(escalated_count / total_incidents * 100, 2),
        "last_updated": datetime.now()
    }


# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions."""
    logger.error(f"HTTP error: {exc.status_code} - {exc.detail}")
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "status_code": exc.status_code}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions."""
    logger.error(f"Unexpected error: {str(exc)}")
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "status_code": 500}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)