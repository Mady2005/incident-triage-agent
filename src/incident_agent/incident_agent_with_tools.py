"""Enhanced incident agent with integrated tools and utilities."""

from typing import Literal, List, Dict, Any
from datetime import datetime
import os

from langchain.chat_models import init_chat_model
from langgraph.graph import StateGraph, START, END
from langgraph.types import Command
from dotenv import load_dotenv

from .schemas import IncidentState, StateInput
from .incident_agent import (
    triage_incident, 
    route_to_team, 
    coordinate_response
)
from .tools.incident_tools import (
    create_incident_tool,
    update_incident_tool,
    get_incident_status_tool
)
from .tools.notification_tools import (
    send_notification_tool,
    send_escalation_notification_tool,
    format_status_update_tool
)
from .tools.diagnostic_tools import (
    lookup_runbook_tool,
    query_metrics_tool,
    check_system_health_tool,
    generate_diagnostic_queries_tool
)
from .utils import current_timestamp

load_dotenv(".env")

# Initialize LLM with fallback for testing
try:
    llm = init_chat_model("gpt-4o-mini", temperature=0.1)
except Exception as e:
    print(f"⚠️  LLM initialization failed: {str(e)}")
    print("⚠️  Using mock LLM for testing - set OPENAI_API_KEY for full functionality")
    llm = None


def triage_incident_with_tools(state: IncidentState) -> Command[Literal["route_to_team", "__end__"]]:
    """Enhanced triage with tool integration."""
    # Run original triage logic
    command = triage_incident(state)
    
    if command.goto == "route_to_team":
        # Create incident record using tools
        incident_data = state["incident_input"]
        
        create_result = create_incident_tool.invoke({
            "title": incident_data.get("title", "Unknown Incident"),
            "description": incident_data.get("description", ""),
            "severity": command.update.get("severity_classification", "medium"),
            "affected_systems": incident_data.get("affected_systems", []),
            "reporter": incident_data.get("reporter", "system"),
            "source": incident_data.get("source", "agent")
        })
        
        if create_result["success"]:
            # Update command with tool-generated incident ID
            command.update["incident_id"] = create_result["incident_id"]
            command.update["tool_created"] = True
            
            # Send creation notification
            notification_data = {
                "incident_id": create_result["incident_id"],
                "title": incident_data.get("title", "Unknown Incident"),
                "severity": command.update.get("severity_classification", "medium"),
                "description": incident_data.get("description", ""),
                "affected_systems": incident_data.get("affected_systems", []),
                "assigned_teams": [],
                "escalation_needed": command.update.get("escalation_needed", False)
            }
            
            send_notification_tool.invoke({
                "incident_id": create_result["incident_id"],
                "message_type": "created",
                "incident_data": notification_data,
                "urgent": (command.update.get("severity_classification") == "critical")
            })
            
            print(f"✅ Incident {create_result['incident_id']} created and notification sent")
        else:
            print(f"❌ Failed to create incident record: {create_result.get('error')}")
    
    return command


def route_to_team_with_tools(state: IncidentState) -> Command[Literal["coordinate_response", "__end__"]]:
    """Enhanced team routing with tool integration."""
    # Run original routing logic
    command = route_to_team(state)
    
    if command.goto == "coordinate_response":
        incident_id = state.get("incident_id")
        
        if incident_id:
            # Update incident with team assignment
            update_result = update_incident_tool.invoke({
                "incident_id": incident_id,
                "assigned_teams": command.update.get("team_assignment", []),
                "add_timeline_event": f"Teams assigned: {', '.join(command.update.get('team_assignment', []))}"
            })
            
            if update_result["success"]:
                # Send team assignment notification
                notification_data = {
                    "incident_id": incident_id,
                    "title": state["incident_input"].get("title", "Unknown Incident"),
                    "severity": state.get("severity_classification", "medium"),
                    "description": state["incident_input"].get("description", ""),
                    "affected_systems": state["incident_input"].get("affected_systems", []),
                    "assigned_teams": command.update.get("team_assignment", []),
                    "escalation_needed": state.get("escalation_needed", False)
                }
                
                send_notification_tool.invoke({
                    "incident_id": incident_id,
                    "message_type": "updated",
                    "incident_data": notification_data,
                    "urgent": False
                })
                
                print(f"✅ Incident {incident_id} updated with team assignments")
            else:
                print(f"❌ Failed to update incident: {update_result.get('error')}")
    
    return command


def coordinate_response_with_tools(state: IncidentState) -> Command[Literal["__end__"]]:
    """Enhanced response coordination with tool integration."""
    # Run original coordination logic
    command = coordinate_response(state)
    
    incident_id = state.get("incident_id")
    incident_data = state["incident_input"]
    
    if incident_id:
        # Look up relevant runbooks
        runbook_result = lookup_runbook_tool.invoke({
            "affected_systems": incident_data.get("affected_systems", []),
            "symptoms": incident_data.get("severity_indicators", []),
            "severity": state.get("severity_classification", "medium")
        })
        
        # Generate diagnostic queries
        diagnostic_result = generate_diagnostic_queries_tool.invoke({
            "incident_type": "performance",  # Could be determined from incident analysis
            "affected_systems": incident_data.get("affected_systems", []),
            "symptoms": incident_data.get("severity_indicators", [])
        })
        
        # Check system health
        health_result = check_system_health_tool.invoke({
            "systems": incident_data.get("affected_systems", []),
            "include_dependencies": True
        })
        
        # Enhance suggested actions with tool results
        enhanced_actions = command.update.get("suggested_actions", [])
        
        if runbook_result["success"] and runbook_result["runbooks"]:
            runbook = runbook_result["runbooks"][0]  # Use top match
            enhanced_actions.extend([
                f"📖 Follow runbook: {runbook['title']}",
                f"⏱️ Estimated resolution time: {runbook['estimated_time']}"
            ])
            enhanced_actions.extend([f"• {step}" for step in runbook["steps"][:3]])  # Add first 3 steps
        
        if diagnostic_result["success"]:
            enhanced_actions.append("🔍 Execute diagnostic queries:")
            enhanced_actions.extend([f"• {query[:80]}..." for query in diagnostic_result["diagnostic_queries"][:2]])
        
        if health_result["success"]:
            unhealthy_systems = [s for s in health_result["system_details"] if s["status"] != "healthy"]
            if unhealthy_systems:
                enhanced_actions.append(f"⚠️ Focus on unhealthy systems: {', '.join([s['system'] for s in unhealthy_systems])}")
        
        # Update incident with enhanced actions and tool results
        update_result = update_incident_tool.invoke({
            "incident_id": incident_id,
            "status": "in_progress",
            "resolution_notes": f"Runbooks found: {len(runbook_result.get('runbooks', []))}, Diagnostic queries generated: {len(diagnostic_result.get('diagnostic_queries', []))}",
            "add_timeline_event": "Response coordination completed with tool assistance"
        })
        
        # Update command with enhanced actions
        command.update["suggested_actions"] = enhanced_actions
        command.update["runbooks_found"] = runbook_result.get("runbooks", [])
        command.update["diagnostic_queries"] = diagnostic_result.get("diagnostic_queries", [])
        command.update["system_health"] = health_result.get("system_details", [])
        
        # Send escalation notification if needed
        if state.get("escalation_needed", False):
            escalation_data = {
                "incident_id": incident_id,
                "title": incident_data.get("title", "Unknown Incident"),
                "severity": state.get("severity_classification", "medium"),
                "description": incident_data.get("description", ""),
                "affected_systems": incident_data.get("affected_systems", []),
                "assigned_teams": state.get("team_assignment", []),
                "suggested_actions": enhanced_actions,
                "escalation_needed": True
            }
            
            send_escalation_notification_tool.invoke({
                "incident_id": incident_id,
                "escalation_reason": "Critical incident requiring immediate attention",
                "target_team": "management",
                "incident_data": escalation_data,
                "urgency_level": "high" if state.get("severity_classification") == "critical" else "medium"
            })
        
        print(f"✅ Response coordination completed for incident {incident_id}")
        print(f"   📖 Runbooks found: {len(runbook_result.get('runbooks', []))}")
        print(f"   🔍 Diagnostic queries: {len(diagnostic_result.get('diagnostic_queries', []))}")
        print(f"   🏥 System health checks: {len(health_result.get('system_details', []))}")
    
    return command


def build_incident_agent_with_tools():
    """Build incident agent with integrated tools."""
    
    workflow = StateGraph(IncidentState, input_schema=StateInput)
    
    # Add enhanced nodes with tool integration
    workflow.add_node("triage_incident", triage_incident_with_tools)
    workflow.add_node("route_to_team", route_to_team_with_tools)
    workflow.add_node("coordinate_response", coordinate_response_with_tools)
    
    # Add edges
    workflow.add_edge(START, "triage_incident")
    
    return workflow.compile()


# Create the enhanced agent
incident_agent_with_tools = build_incident_agent_with_tools()


def process_incident_with_tools(incident_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process an incident with full tool integration.
    
    Args:
        incident_data: Raw incident data dictionary
        
    Returns:
        Final state with processing results and tool outputs
    """
    print(f"🚨 Processing incident with tools: {incident_data.get('title', 'Unknown')}")
    
    # Run the enhanced workflow
    result = incident_agent_with_tools.invoke({
        "incident_input": incident_data
    })
    
    # Extract comprehensive results
    response = {
        "incident_id": result.get("incident_id"),
        "severity": result.get("severity_classification"),
        "assigned_teams": result.get("team_assignment", []),
        "suggested_actions": result.get("suggested_actions", []),
        "escalation_needed": result.get("escalation_needed", False),
        "status": result.get("resolution_status", "in_progress"),
        "created_at": result.get("created_at"),
        "updated_at": result.get("updated_at"),
        
        # Tool-specific results
        "tool_created": result.get("tool_created", False),
        "runbooks_found": result.get("runbooks_found", []),
        "diagnostic_queries": result.get("diagnostic_queries", []),
        "system_health": result.get("system_health", []),
        
        # Summary statistics
        "tools_used": {
            "incident_management": True,
            "notifications": True,
            "runbook_lookup": len(result.get("runbooks_found", [])) > 0,
            "diagnostics": len(result.get("diagnostic_queries", [])) > 0,
            "health_checks": len(result.get("system_health", [])) > 0
        }
    }
    
    print(f"✅ Incident {response['incident_id']} processed with comprehensive tool support")
    return response


def get_incident_details_with_tools(incident_id: str) -> Dict[str, Any]:
    """Get comprehensive incident details using tools."""
    
    # Get incident status
    status_result = get_incident_status_tool.invoke({"incident_id": incident_id})
    
    if not status_result["success"]:
        return {
            "success": False,
            "error": status_result["error"]
        }
    
    # Get system health for affected systems
    affected_systems = status_result.get("affected_systems", [])
    health_result = check_system_health_tool.invoke({
        "systems": affected_systems,
        "include_dependencies": True
    }) if affected_systems else {"success": False}
    
    # Format status update for different audiences
    incident_data = {
        "incident_id": incident_id,
        "title": status_result.get("title", "Unknown"),
        "severity": status_result.get("severity", "unknown"),
        "status": status_result.get("status", "unknown"),
        "assigned_teams": status_result.get("assigned_teams", []),
        "affected_systems": affected_systems,
        "escalation_needed": status_result.get("escalation_needed", False)
    }
    
    technical_update = format_status_update_tool.invoke({
        "incident_id": incident_id,
        "incident_data": incident_data,
        "update_type": "progress",
        "audience": "technical"
    })
    
    management_update = format_status_update_tool.invoke({
        "incident_id": incident_id,
        "incident_data": incident_data,
        "update_type": "progress",
        "audience": "management"
    })
    
    return {
        "success": True,
        "incident_status": status_result,
        "system_health": health_result if health_result["success"] else None,
        "status_updates": {
            "technical": technical_update.get("formatted_message", ""),
            "management": management_update.get("formatted_message", "")
        },
        "timestamp": current_timestamp().isoformat()
    }


if __name__ == "__main__":
    # Test the enhanced agent with tools
    sample_incident = {
        "id": "TOOLS-001",
        "title": "Database connection pool exhaustion",
        "description": "All database connections are exhausted, causing API timeouts and user authentication failures",
        "source": "monitoring",
        "timestamp": datetime.now().isoformat(),
        "reporter": "monitoring-system",
        "affected_systems": ["database", "api", "auth"],
        "error_logs": "Connection pool exhausted: max_connections=100, active=100, idle=0",
        "severity_indicators": ["critical", "timeout", "database", "connection", "pool"]
    }
    
    # Process incident with full tool integration
    result = process_incident_with_tools(sample_incident)
    
    print("\n📊 Processing Result with Tools:")
    for key, value in result.items():
        if key == "suggested_actions":
            print(f"  {key}:")
            for action in value:
                print(f"    - {action}")
        elif key == "runbooks_found":
            print(f"  {key}: {len(value)} runbooks")
            for runbook in value[:2]:  # Show first 2
                print(f"    - {runbook.get('title', 'Unknown')}")
        elif key == "diagnostic_queries":
            print(f"  {key}: {len(value)} queries")
        elif key == "system_health":
            print(f"  {key}: {len(value)} systems checked")
        else:
            print(f"  {key}: {value}")
    
    # Test incident details retrieval
    if result.get("incident_id"):
        print(f"\n🔍 Testing incident details retrieval...")
        details = get_incident_details_with_tools(result["incident_id"])
        if details["success"]:
            print(f"✅ Retrieved comprehensive incident details")
            print(f"   Status: {details['incident_status']['status']}")
            print(f"   Age: {details['incident_status']['age_hours']} hours")
            if details["system_health"]:
                print(f"   System Health: {details['system_health']['overall_status']}")
        else:
            print(f"❌ Failed to retrieve details: {details['error']}")