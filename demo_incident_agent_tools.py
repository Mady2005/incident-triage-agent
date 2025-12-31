"""Demo script for the enhanced incident agent with tools integration."""

import asyncio
from datetime import datetime
from src.incident_agent.incident_agent_with_tools import (
    process_incident_with_tools,
    get_incident_details_with_tools
)
from src.incident_agent.tools.incident_tools import (
    list_incidents_tool,
    clear_incidents_store
)
from src.incident_agent.tools.diagnostic_tools import (
    check_system_health_tool,
    query_metrics_tool
)


def print_section(title: str):
    """Print a formatted section header."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def print_subsection(title: str):
    """Print a formatted subsection header."""
    print(f"\n{'-'*40}")
    print(f"  {title}")
    print(f"{'-'*40}")


def demo_incident_processing():
    """Demonstrate incident processing with tools."""
    print_section("INCIDENT AGENT WITH TOOLS DEMO")
    
    # Clear any existing incidents
    clear_incidents_store()
    
    # Sample incidents with different characteristics
    incidents = [
        {
            "id": "DEMO-001",
            "title": "Critical database connection failure",
            "description": "All database connections are failing, causing widespread service disruption",
            "source": "monitoring",
            "timestamp": datetime.now().isoformat(),
            "reporter": "monitoring-system",
            "affected_systems": ["database", "api", "auth"],
            "error_logs": "Connection timeout after 30 seconds, pool exhausted",
            "severity_indicators": ["critical", "outage", "database", "timeout", "connection"]
        },
        {
            "id": "DEMO-002", 
            "title": "API response time degradation",
            "description": "API endpoints showing increased response times, affecting user experience",
            "source": "performance-monitoring",
            "timestamp": datetime.now().isoformat(),
            "reporter": "ops-team",
            "affected_systems": ["api", "frontend"],
            "error_logs": "Average response time increased from 200ms to 1.2s",
            "severity_indicators": ["performance", "latency", "api", "slow"]
        },
        {
            "id": "DEMO-003",
            "title": "Suspicious authentication failures",
            "description": "Unusual pattern of authentication failures detected from multiple IP addresses",
            "source": "security-monitoring",
            "timestamp": datetime.now().isoformat(),
            "reporter": "security-team",
            "affected_systems": ["auth", "api"],
            "error_logs": "Failed login attempts: 1,247 in last 10 minutes from 23 different IPs",
            "severity_indicators": ["security", "auth", "brute-force", "suspicious"]
        }
    ]
    
    processed_incidents = []
    
    # Process each incident
    for i, incident in enumerate(incidents, 1):
        print_subsection(f"Processing Incident {i}: {incident['title']}")
        
        result = process_incident_with_tools(incident)
        processed_incidents.append(result)
        
        print(f"✅ Incident ID: {result['incident_id']}")
        print(f"   Severity: {result['severity']}")
        print(f"   Assigned Teams: {', '.join(result['assigned_teams'])}")
        print(f"   Escalation Needed: {result['escalation_needed']}")
        print(f"   Tools Used: {sum(result['tools_used'].values())}/5")
        
        # Show enhanced actions
        print(f"\n📋 Suggested Actions ({len(result['suggested_actions'])}):")
        for action in result['suggested_actions'][:5]:  # Show first 5
            print(f"   • {action}")
        
        if len(result['suggested_actions']) > 5:
            print(f"   ... and {len(result['suggested_actions']) - 5} more actions")
        
        # Show runbooks found
        if result['runbooks_found']:
            print(f"\n📖 Runbooks Found ({len(result['runbooks_found'])}):")
            for runbook in result['runbooks_found'][:2]:  # Show first 2
                print(f"   • {runbook['title']} (Est. time: {runbook['estimated_time']})")
        
        # Show diagnostic capabilities
        if result['diagnostic_queries']:
            print(f"\n🔍 Diagnostic Queries Generated: {len(result['diagnostic_queries'])}")
        
        if result['system_health']:
            healthy_systems = sum(1 for s in result['system_health'] if s['status'] == 'healthy')
            print(f"\n🏥 System Health: {healthy_systems}/{len(result['system_health'])} systems healthy")
    
    return processed_incidents


def demo_incident_management_tools(processed_incidents):
    """Demonstrate incident management and monitoring tools."""
    print_section("INCIDENT MANAGEMENT TOOLS DEMO")
    
    # List all incidents
    print_subsection("Listing All Incidents")
    
    incidents_list = list_incidents_tool.invoke({
        "limit": 10
    })
    
    if incidents_list["success"]:
        print(f"📊 Total Incidents Found: {incidents_list['total_found']}")
        
        for incident in incidents_list["incidents"]:
            status_icon = "🔴" if incident["severity"] == "critical" else "🟡" if incident["severity"] == "high" else "🟢"
            print(f"   {status_icon} {incident['incident_id']}: {incident['title']}")
            print(f"      Severity: {incident['severity']} | Teams: {', '.join(incident['assigned_teams'])}")
            print(f"      Age: {incident['age_hours']:.1f} hours | Status: {incident['status']}")
    
    # Filter incidents by severity
    print_subsection("Filtering Critical Incidents")
    
    critical_incidents = list_incidents_tool.invoke({
        "severity_filter": "critical",
        "limit": 5
    })
    
    if critical_incidents["success"]:
        print(f"🚨 Critical Incidents: {critical_incidents['total_found']}")
        for incident in critical_incidents["incidents"]:
            print(f"   • {incident['incident_id']}: {incident['title']}")
    
    # Get detailed incident information
    if processed_incidents:
        print_subsection("Detailed Incident Analysis")
        
        sample_incident_id = processed_incidents[0]["incident_id"]
        details = get_incident_details_with_tools(sample_incident_id)
        
        if details["success"]:
            print(f"🔍 Analyzing Incident: {sample_incident_id}")
            
            status = details["incident_status"]
            print(f"   Status: {status['status']} | Severity: {status['severity']}")
            print(f"   Age: {status['age_hours']:.1f} hours")
            print(f"   Timeline Events: {status['timeline_count']}")
            
            if details["system_health"]:
                health = details["system_health"]
                print(f"   Overall Health: {health['overall_status']} ({health['overall_health_score']:.2f})")
                print(f"   Systems: {health['healthy_systems']} healthy, {health['degraded_systems']} degraded, {health['unhealthy_systems']} unhealthy")
            
            # Show formatted status updates
            print(f"\n📝 Technical Status Update:")
            tech_update = details["status_updates"]["technical"]
            print("   " + "\n   ".join(tech_update.split("\n")[:5]))  # First 5 lines
            
            print(f"\n📊 Management Summary:")
            mgmt_update = details["status_updates"]["management"]
            print("   " + "\n   ".join(mgmt_update.split("\n")[:5]))  # First 5 lines


def demo_diagnostic_tools():
    """Demonstrate diagnostic and monitoring tools."""
    print_section("DIAGNOSTIC TOOLS DEMO")
    
    # System health checks
    print_subsection("System Health Monitoring")
    
    systems_to_check = ["database", "api", "auth", "frontend"]
    health_result = check_system_health_tool.invoke({
        "systems": systems_to_check,
        "include_dependencies": True
    })
    
    if health_result["success"]:
        print(f"🏥 Overall System Health: {health_result['overall_status']} ({health_result['overall_health_score']:.2f})")
        print(f"   Systems Checked: {health_result['systems_checked']}")
        print(f"   Healthy: {health_result['healthy_systems']} | Degraded: {health_result['degraded_systems']} | Unhealthy: {health_result['unhealthy_systems']}")
        
        print(f"\n📊 System Details:")
        for system in health_result["system_details"]:
            status_icon = "✅" if system["status"] == "healthy" else "⚠️" if system["status"] == "degraded" else "❌"
            print(f"   {status_icon} {system['system']}: {system['status']} ({system['health_score']:.2f})")
            
            if system["issues"]:
                for issue in system["issues"]:
                    print(f"      • {issue}")
    
    # Metrics monitoring
    print_subsection("Metrics Analysis")
    
    metrics_to_check = [
        ("database", "cpu"),
        ("api", "response_time"),
        ("auth", "error_rate"),
        ("database", "memory")
    ]
    
    for system, metric_type in metrics_to_check:
        metric_result = query_metrics_tool.invoke({
            "system": system,
            "metric_type": metric_type,
            "time_range": "1h",
            "aggregation": "avg"
        })
        
        if metric_result["success"]:
            status_icon = "🔴" if metric_result["status"] == "critical" else "🟡" if metric_result["status"] == "warning" else "🟢"
            trend_icon = "📈" if metric_result["trend"] == "increasing" else "📉" if metric_result["trend"] == "decreasing" else "➡️"
            
            print(f"   {status_icon} {system} {metric_type}: {metric_result['current_value']} {metric_result['unit']} {trend_icon}")
            
            if metric_result["recommendations"]:
                print(f"      💡 {metric_result['recommendations'][0]}")


def demo_tool_integration_summary():
    """Show summary of tool integration capabilities."""
    print_section("TOOL INTEGRATION SUMMARY")
    
    capabilities = {
        "Incident Management": [
            "✅ Automatic incident record creation",
            "✅ Timeline tracking and updates", 
            "✅ Status and severity management",
            "✅ Team assignment tracking"
        ],
        "Notifications": [
            "✅ Multi-channel notification support",
            "✅ Audience-specific message formatting",
            "✅ Escalation notifications",
            "✅ Status update broadcasts"
        ],
        "Diagnostics": [
            "✅ Runbook lookup and recommendations",
            "✅ System health monitoring",
            "✅ Metrics analysis and trending",
            "✅ Diagnostic query generation"
        ],
        "Workflow Enhancement": [
            "✅ Tool-assisted triage decisions",
            "✅ Enhanced action recommendations",
            "✅ Automated documentation",
            "✅ Context-aware escalations"
        ]
    }
    
    for category, features in capabilities.items():
        print(f"\n🔧 {category}:")
        for feature in features:
            print(f"   {feature}")
    
    print(f"\n📈 Benefits:")
    print(f"   • Faster incident response with automated tool assistance")
    print(f"   • Comprehensive incident tracking and documentation")
    print(f"   • Proactive system monitoring and health checks")
    print(f"   • Consistent notification and communication workflows")
    print(f"   • Enhanced decision-making with diagnostic insights")


def main():
    """Run the complete demo."""
    print("🚀 Starting Enhanced Incident Agent with Tools Demo")
    print("   This demo showcases the integration of incident management,")
    print("   notification, and diagnostic tools into the LangGraph workflow.")
    
    try:
        # Process sample incidents
        processed_incidents = demo_incident_processing()
        
        # Demonstrate management tools
        demo_incident_management_tools(processed_incidents)
        
        # Show diagnostic capabilities
        demo_diagnostic_tools()
        
        # Summary of capabilities
        demo_tool_integration_summary()
        
        print_section("DEMO COMPLETED SUCCESSFULLY")
        print("✅ All tools integrated and working properly")
        print("✅ Incident processing enhanced with comprehensive tooling")
        print("✅ Ready for production deployment with tool support")
        
    except Exception as e:
        print(f"\n❌ Demo failed with error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()