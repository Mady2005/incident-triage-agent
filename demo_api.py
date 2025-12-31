#!/usr/bin/env python3
"""
Demo script for the Incident Triage Agent API.

This demonstrates how to interact with the API endpoints.
"""

import requests
import json
from datetime import datetime
import time


def demo_api_interaction():
    """Demonstrate API interaction with various scenarios."""
    
    base_url = "http://localhost:8000"
    
    print("🌐 Incident Triage Agent API Demo")
    print("=" * 50)
    print(f"📡 API Base URL: {base_url}")
    
    # Check if API is running
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            print("✅ API is running and healthy")
            health_data = response.json()
            print(f"   Version: {health_data['version']}")
            print(f"   Status: {health_data['status']}")
        else:
            print("❌ API health check failed")
            return
    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot connect to API: {e}")
        print("💡 Make sure to run 'python run_api.py' first")
        return
    
    print("\n" + "=" * 50)
    
    # Demo scenarios
    scenarios = [
        {
            "name": "Critical Database Outage",
            "data": {
                "title": "Database connection timeout",
                "description": "Complete database failure affecting all services",
                "source": "monitoring",
                "reporter": "monitoring-system",
                "affected_systems": ["database", "api"],
                "error_logs": "Connection timeout after 30 seconds",
                "severity_indicators": ["critical", "outage", "timeout"]
            }
        },
        {
            "name": "Security Incident",
            "data": {
                "title": "Unauthorized access detected",
                "description": "Multiple failed login attempts from suspicious IP addresses",
                "source": "monitoring",
                "reporter": "security-monitor",
                "affected_systems": ["auth", "api"],
                "error_logs": "Failed authentication attempts: 192.168.1.100",
                "severity_indicators": ["security", "unauthorized", "breach"]
            }
        },
        {
            "name": "Performance Issue",
            "data": {
                "title": "API response times degraded",
                "description": "Users reporting slow page loads",
                "source": "user_report",
                "reporter": "support-team",
                "affected_systems": ["api", "frontend"],
                "error_logs": "Average response time: 5.2s (normal: 0.3s)",
                "severity_indicators": ["performance", "slow"]
            }
        }
    ]
    
    created_incidents = []
    
    # Create incidents
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n📋 Scenario {i}: {scenario['name']}")
        print("-" * 40)
        
        try:
            response = requests.post(f"{base_url}/incidents/", json=scenario["data"])
            
            if response.status_code == 201:
                incident = response.json()
                created_incidents.append(incident["incident_id"])
                
                print(f"✅ Created: {incident['incident_id']}")
                print(f"📊 Severity: {incident['severity']}")
                print(f"👥 Teams: {', '.join(incident['assigned_teams'])}")
                print(f"⚡ Escalation: {'Yes' if incident['escalation_needed'] else 'No'}")
                print(f"📋 Actions: {len(incident['suggested_actions'])} suggested")
                
                # Show first few actions
                for j, action in enumerate(incident['suggested_actions'][:2], 1):
                    print(f"   {j}. {action}")
                if len(incident['suggested_actions']) > 2:
                    print(f"   ... and {len(incident['suggested_actions']) - 2} more")
                    
            else:
                print(f"❌ Failed to create incident: {response.status_code}")
                print(f"   Error: {response.text}")
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Request failed: {e}")
    
    # Demonstrate other API features
    if created_incidents:
        print(f"\n🔍 Demonstrating other API features...")
        print("-" * 40)
        
        # Get incident details
        incident_id = created_incidents[0]
        try:
            response = requests.get(f"{base_url}/incidents/{incident_id}")
            if response.status_code == 200:
                print(f"✅ Retrieved incident details for {incident_id}")
            else:
                print(f"❌ Failed to retrieve incident: {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"❌ Failed to retrieve incident: {e}")
        
        # List all incidents
        try:
            response = requests.get(f"{base_url}/incidents/")
            if response.status_code == 200:
                incidents = response.json()
                print(f"✅ Listed {len(incidents)} total incidents")
            else:
                print(f"❌ Failed to list incidents: {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"❌ Failed to list incidents: {e}")
        
        # Update severity
        try:
            update_data = {
                "new_severity": "critical",
                "reason": "Impact assessment revealed critical business impact",
                "updated_by": "incident-commander"
            }
            response = requests.put(f"{base_url}/incidents/{incident_id}/severity", json=update_data)
            if response.status_code == 200:
                print(f"✅ Updated severity for {incident_id}")
            else:
                print(f"❌ Failed to update severity: {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"❌ Failed to update severity: {e}")
        
        # Get system stats
        try:
            response = requests.get(f"{base_url}/stats")
            if response.status_code == 200:
                stats = response.json()
                print(f"✅ System stats:")
                print(f"   Total incidents: {stats['total_incidents']}")
                print(f"   Escalation rate: {stats['escalation_rate']}%")
                if stats['severity_distribution']:
                    print(f"   Severity distribution: {stats['severity_distribution']}")
            else:
                print(f"❌ Failed to get stats: {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"❌ Failed to get stats: {e}")
    
    print(f"\n🎉 API Demo completed!")
    print(f"📖 Full API documentation: {base_url}/docs")
    print(f"🔧 Interactive API explorer: {base_url}/redoc")
    
    print(f"\n💡 Try these endpoints manually:")
    print(f"   GET  {base_url}/health")
    print(f"   GET  {base_url}/incidents/")
    print(f"   GET  {base_url}/stats")
    print(f"   POST {base_url}/incidents/ (with JSON body)")


if __name__ == "__main__":
    demo_api_interaction()