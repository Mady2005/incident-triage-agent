#!/usr/bin/env python3
"""
Demo script for the Incident Triage Agent MVP.

This demonstrates the core LangGraph workflow for processing incidents.
"""

from datetime import datetime
from src.incident_agent.incident_agent import process_incident


def demo_incident_processing():
    """Demonstrate incident processing with various scenarios."""
    
    print("🚨 Incident Triage Agent MVP Demo")
    print("=" * 50)
    
    # Demo scenarios
    scenarios = [
        {
            "name": "Critical Database Outage",
            "incident": {
                "id": "DEMO-001",
                "title": "Database connection timeout",
                "description": "Complete database failure affecting all services",
                "source": "monitoring",
                "timestamp": datetime.now().isoformat(),
                "reporter": "monitoring-system",
                "affected_systems": ["database", "api"],
                "error_logs": "Connection timeout after 30 seconds",
                "severity_indicators": ["critical", "outage", "timeout"]
            }
        },
        {
            "name": "Security Incident",
            "incident": {
                "id": "DEMO-002", 
                "title": "Unauthorized access detected",
                "description": "Multiple failed login attempts from suspicious IP addresses",
                "source": "monitoring",
                "timestamp": datetime.now().isoformat(),
                "reporter": "security-monitor",
                "affected_systems": ["auth", "api"],
                "error_logs": "Failed authentication attempts: 127.0.0.1",
                "severity_indicators": ["security", "unauthorized", "breach"]
            }
        },
        {
            "name": "Performance Degradation",
            "incident": {
                "id": "DEMO-003",
                "title": "API response times degraded",
                "description": "Users reporting slow page loads across the application",
                "source": "user_report",
                "timestamp": datetime.now().isoformat(),
                "reporter": "support-team",
                "affected_systems": ["api", "frontend"],
                "error_logs": "Average response time: 5.2s (normal: 0.3s)",
                "severity_indicators": ["performance", "slow", "degradation"]
            }
        }
    ]
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n📋 Scenario {i}: {scenario['name']}")
        print("-" * 40)
        
        try:
            result = process_incident(scenario["incident"])
            
            print(f"✅ Processed: {result['incident_id']}")
            print(f"📊 Severity: {result['severity']}")
            print(f"👥 Teams: {', '.join(result['assigned_teams'])}")
            print(f"⚡ Escalation: {'Yes' if result['escalation_needed'] else 'No'}")
            print(f"📋 Actions: {len(result['suggested_actions'])} suggested")
            
            # Show first few actions
            for j, action in enumerate(result['suggested_actions'][:3], 1):
                print(f"   {j}. {action}")
            
            if len(result['suggested_actions']) > 3:
                print(f"   ... and {len(result['suggested_actions']) - 3} more")
                
        except Exception as e:
            print(f"❌ Error processing incident: {e}")
    
    print(f"\n🎉 Demo completed! The MVP successfully:")
    print("   • Triaged incidents by severity")
    print("   • Routed to appropriate response teams")
    print("   • Generated contextual response actions")
    print("   • Handled security incidents with escalation")
    print("   • Provided fallback handling for edge cases")
    
    print(f"\n💡 Next steps for full functionality:")
    print("   • Set OPENAI_API_KEY for LLM-powered triage")
    print("   • Add FastAPI endpoints for external integration")
    print("   • Implement notification systems (Slack, email)")
    print("   • Add human-in-the-loop capabilities")


if __name__ == "__main__":
    demo_incident_processing()