"""Core incident triage and resolution agent using LangGraph."""

from typing import Literal, List, Dict, Any
from datetime import datetime

from langchain.chat_models import init_chat_model
from langgraph.graph import StateGraph, START, END
from langgraph.types import Command
from dotenv import load_dotenv
import os

from .schemas import IncidentState, StateInput, IncidentReport, SeverityClassificationSchema, TeamRoutingSchema
from .routers.triage_router import TriageRouter
from .models.incident import Incident
from .models.team import ResponseTeam, TeamRegistry
from .utils import generate_incident_id, current_timestamp, parse_incident_data
from .prompts import TEAM_ROUTING_PROMPT, RESPONSE_COORDINATION_PROMPT

load_dotenv(".env")

# Initialize LLM (with fallback for testing)
try:
    if os.getenv("OPENAI_API_KEY"):
        llm = init_chat_model("openai:gpt-4o-mini", temperature=0.1)
    else:
        # Mock LLM for testing/development
        from unittest.mock import Mock
        llm = Mock()
        print("⚠️  Using mock LLM - set OPENAI_API_KEY for full functionality")
except Exception as e:
    from unittest.mock import Mock
    llm = Mock()
    print(f"⚠️  LLM initialization failed: {e}. Using mock LLM.")

# Initialize components
triage_router = TriageRouter(llm=llm)
team_registry = TeamRegistry()

# The team registry already initializes default teams, so we don't need to register them again


def triage_incident(state: IncidentState) -> Command[Literal["route_to_team", "__end__"]]:
    """
    Triage incoming incident to determine severity and initial classification.
    
    This node:
    1. Parses the incident input
    2. Classifies severity using the triage router
    3. Creates an incident object
    4. Determines if routing is needed
    """
    print("🔍 Starting incident triage...")
    
    try:
        # Parse incident data
        incident_data = parse_incident_data(state["incident_input"])
        incident_report = IncidentReport(**incident_data)
        
        # Classify severity
        classification = triage_router.classify_severity(incident_report)
        
        # Create incident object
        incident = triage_router.create_incident_from_classification(incident_report, classification)
        
        # Update state
        update = {
            "incident_id": incident.report.id,
            "severity_classification": classification.severity,
            "created_at": incident.created_at,
            "updated_at": current_timestamp(),
            "escalation_needed": triage_router.should_escalate_immediately(classification)
        }
        
        print(f"📊 Incident {incident.report.id} classified as {classification.severity}")
        print(f"🔒 Security incident: {classification.security_incident}")
        
        # Store incident for routing
        state["_incident"] = incident
        state["_classification"] = classification
        
        return Command(goto="route_to_team", update=update)
        
    except Exception as e:
        print(f"❌ Triage failed: {str(e)}")
        update = {
            "incident_id": generate_incident_id(),
            "severity_classification": "medium",  # Fallback
            "created_at": current_timestamp(),
            "updated_at": current_timestamp(),
            "escalation_needed": True  # Escalate on error
        }
        return Command(goto="route_to_team", update=update)


def route_to_team(state: IncidentState) -> Command[Literal["coordinate_response", "__end__"]]:
    """
    Route incident to appropriate response teams based on characteristics.
    
    This node:
    1. Analyzes incident characteristics
    2. Determines best response teams
    3. Sets up team assignments
    4. Handles escalation if needed
    """
    print("🎯 Routing incident to response teams...")
    
    try:
        incident = state.get("_incident")
        classification = state.get("_classification")
        
        if not incident or not classification:
            # Fallback routing based on state
            affected_systems = state["incident_input"].get("affected_systems", [])
            severity = state["severity_classification"]
        else:
            affected_systems = incident.report.affected_systems
            severity = classification.severity
        
        # Find best teams using team registry
        assigned_teams = []
        
        # Security incidents always go to security team
        if classification and classification.security_incident:
            assigned_teams.append("Security")
        
        # Route based on affected systems
        for system in affected_systems:
            # Map system names to incident types that teams can handle
            incident_type = system.lower()
            team_found = False
            
            if "database" in incident_type or "db" in incident_type:
                incident_type = "database"
                team_found = True
            elif "api" in incident_type:
                incident_type = "api"
                team_found = True
            elif "infrastructure" in incident_type or "infra" in incident_type:
                incident_type = "infrastructure"
                team_found = True
            elif "security" in incident_type or "auth" in incident_type:
                incident_type = "security"
                team_found = True
            elif "network" in incident_type:
                incident_type = "network"
                team_found = True
            elif "performance" in incident_type or "slow" in incident_type:
                incident_type = "performance"
                team_found = True
            
            if team_found:
                best_team = team_registry.find_best_team_for_incident(incident_type, severity)
                if best_team and best_team.name not in assigned_teams:
                    assigned_teams.append(best_team.name)
            else:
                # Unknown system - fallback to SRE
                if "SRE" not in assigned_teams:
                    assigned_teams.append("SRE")
        
        # Fallback to SRE if no teams assigned
        if not assigned_teams:
            assigned_teams.append("SRE")
        
        # Critical incidents get additional team coverage
        if severity == "critical":
            if "SRE" not in assigned_teams:
                assigned_teams.append("SRE")
        
        print(f"👥 Assigned teams: {', '.join(assigned_teams)}")
        
        update = {
            "team_assignment": assigned_teams,
            "updated_at": current_timestamp()
        }
        
        return Command(goto="coordinate_response", update=update)
        
    except Exception as e:
        print(f"❌ Team routing failed: {str(e)}")
        # Fallback to SRE team
        update = {
            "team_assignment": ["SRE"],
            "updated_at": current_timestamp()
        }
        return Command(goto="coordinate_response", update=update)


def coordinate_response(state: IncidentState) -> Command[Literal["__end__"]]:
    """
    Coordinate initial response actions and generate recommendations.
    
    This node:
    1. Generates suggested response actions
    2. Creates notifications for assigned teams
    3. Sets up monitoring and tracking
    4. Provides runbook recommendations
    """
    print("🚀 Coordinating incident response...")
    
    try:
        incident = state.get("_incident")
        classification = state.get("_classification")
        assigned_teams = state["team_assignment"]
        severity = state["severity_classification"]
        
        # Generate response actions based on severity and type
        suggested_actions = []
        
        # Generate response actions based on severity and type
        suggested_actions = []
        
        # Check for critical indicators in incident input as fallback
        incident_input = state.get("incident_input", {})
        severity_indicators = incident_input.get("severity_indicators", [])
        title = incident_input.get("title", "").lower()
        description = incident_input.get("description", "").lower()
        
        # Critical incidents get immediate actions
        is_critical = (
            severity == "critical" or 
            any(indicator.lower() in ["outage", "critical", "down", "breach"] for indicator in severity_indicators) or
            any(keyword in title for keyword in ["outage", "critical", "down", "complete", "total"]) or
            any(keyword in description for keyword in ["outage", "critical", "down", "complete", "total"])
        )
        
        if is_critical:
            suggested_actions.extend([
                "Notify primary on-call engineer immediately",
                "Set up incident war room/bridge", 
                "Begin impact assessment and customer communication",
                "Activate incident commander role"
            ])
        
        # Security incidents get security-specific actions
        if classification and classification.security_incident:
            suggested_actions.extend([
                "Isolate affected systems if possible",
                "Preserve logs and evidence",
                "Notify security team and compliance",
                "Begin security incident response protocol"
            ])
        
        # System-specific actions
        if incident:
            for system in incident.report.affected_systems:
                if "database" in system.lower():
                    suggested_actions.append(f"Check {system} connection pools and query performance")
                elif "api" in system.lower():
                    suggested_actions.append(f"Monitor {system} response times and error rates")
                elif "frontend" in system.lower():
                    suggested_actions.append(f"Check {system} deployment status and CDN health")
        
        # General diagnostic actions
        suggested_actions.extend([
            "Review recent deployments and changes",
            "Check monitoring dashboards for anomalies",
            "Gather additional logs and metrics",
            "Document timeline and initial findings"
        ])
        
        print(f"📋 Generated {len(suggested_actions)} response actions")
        
        # Generate notifications for critical incidents
        notifications = []
        if severity == "critical" or (classification and classification.security_incident):
            notifications.append({
                "type": "immediate",
                "recipients": assigned_teams,
                "message": f"CRITICAL: {state['incident_input'].get('title', 'Incident')} requires immediate attention",
                "urgency": "immediate"
            })
        
        update = {
            "suggested_actions": suggested_actions,
            "resolution_status": "in_progress",
            "updated_at": current_timestamp()
        }
        
        # Store notifications in state for external systems
        if notifications:
            update["_notifications"] = notifications
        
        print("✅ Response coordination complete")
        return Command(goto=END, update=update)
        
    except Exception as e:
        print(f"❌ Response coordination failed: {str(e)}")
        # Minimal fallback actions
        update = {
            "suggested_actions": [
                "Review incident details and assess impact",
                "Contact assigned response teams",
                "Begin diagnostic investigation"
            ],
            "resolution_status": "in_progress",
            "updated_at": current_timestamp()
        }
        return Command(goto=END, update=update)


# Build the incident agent workflow
def build_incident_agent():
    """Build and compile the incident agent workflow."""
    
    workflow = StateGraph(IncidentState, input_schema=StateInput)
    
    # Add nodes
    workflow.add_node("triage_incident", triage_incident)
    workflow.add_node("route_to_team", route_to_team)
    workflow.add_node("coordinate_response", coordinate_response)
    
    # Add edges
    workflow.add_edge(START, "triage_incident")
    
    # Compile and return
    return workflow.compile()


# Create the compiled agent
incident_agent = build_incident_agent()


def process_incident(incident_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process an incident through the complete workflow.
    
    Args:
        incident_data: Raw incident data dictionary
        
    Returns:
        Final state with processing results
    """
    print(f"🚨 Processing incident: {incident_data.get('title', 'Unknown')}")
    
    # Run the workflow
    result = incident_agent.invoke({
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
        "notifications": result.get("_notifications", [])
    }
    
    print(f"✅ Incident {response['incident_id']} processed successfully")
    return response


if __name__ == "__main__":
    # Example usage
    sample_incident = {
        "id": "INC-001",
        "title": "Database connection timeout",
        "description": "Users reporting slow page loads and timeout errors when accessing the application",
        "source": "monitoring",
        "timestamp": datetime.now().isoformat(),
        "reporter": "monitoring-system",
        "affected_systems": ["database", "api"],
        "error_logs": "Connection timeout after 30 seconds",
        "severity_indicators": ["timeout", "performance", "database"]
    }
    
    result = process_incident(sample_incident)
    print("\n📊 Processing Result:")
    for key, value in result.items():
        print(f"  {key}: {value}")