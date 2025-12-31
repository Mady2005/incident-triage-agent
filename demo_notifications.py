#!/usr/bin/env python3
"""
Demo script for the Incident Triage Agent with Slack notifications.

This demonstrates the enhanced incident processing with notification support.
"""

import os
from datetime import datetime
from src.incident_agent.incident_agent_notifications import (
    process_incident_with_notifications,
    send_test_slack_notification,
    escalate_incident_with_notification,
    slack_notifier
)


def demo_notification_system():
    """Demonstrate the notification-enhanced incident processing."""
    
    print("📢 Incident Triage Agent - Notification Demo")
    print("=" * 60)
    
    # Check Slack configuration
    if slack_notifier and slack_notifier.is_enabled():
        print("✅ Slack notifications are ENABLED")
        print(f"   Webhook URL: {slack_notifier.webhook_url[:50]}...")
        print(f"   Default Channel: {slack_notifier.default_channel}")
        print(f"   Team Channels: {len(slack_notifier.team_channels)} configured")
        
        # Test Slack connection
        print("\n🧪 Testing Slack connection...")
        if send_test_slack_notification():
            print("✅ Test notification sent successfully!")
        else:
            print("❌ Test notification failed")
    else:
        print("⚠️  Slack notifications are DISABLED")
        print("   To enable: Set SLACK_WEBHOOK_URL in your .env file")
        print("   Example: SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK")
    
    print("\n" + "=" * 60)
    
    # Demo scenarios with notifications
    scenarios = [
        {
            "name": "Critical Production Outage",
            "data": {
                "id": "CRIT-001",
                "title": "Complete service outage - all systems down",
                "description": "Total system failure affecting all users. Revenue impact estimated at $10k/minute.",
                "source": "monitoring",
                "timestamp": datetime.now().isoformat(),
                "reporter": "monitoring-system",
                "affected_systems": ["database", "api", "frontend", "payment"],
                "error_logs": "All health checks failing. Database connection pool exhausted.",
                "severity_indicators": ["critical", "outage", "down", "total failure"]
            }
        },
        {
            "name": "Security Breach Alert",
            "data": {
                "id": "SEC-001",
                "title": "Unauthorized access detected in admin panel",
                "description": "Multiple failed login attempts followed by successful breach of admin account.",
                "source": "security",
                "timestamp": datetime.now().isoformat(),
                "reporter": "security-monitor",
                "affected_systems": ["auth", "admin", "user-data"],
                "error_logs": "Suspicious IP: 192.168.1.100. Admin account compromised.",
                "severity_indicators": ["security", "breach", "unauthorized", "admin"]
            }
        },
        {
            "name": "Performance Degradation",
            "data": {
                "id": "PERF-001",
                "title": "API response times increased by 300%",
                "description": "Gradual performance degradation over the last hour. Users reporting slow page loads.",
                "source": "monitoring",
                "timestamp": datetime.now().isoformat(),
                "reporter": "performance-monitor",
                "affected_systems": ["api", "database"],
                "error_logs": "Average response time: 2.1s (normal: 0.7s). Database query time increased.",
                "severity_indicators": ["performance", "slow", "degradation"]
            }
        }
    ]
    
    processed_incidents = []
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n📋 Scenario {i}: {scenario['name']}")
        print("-" * 50)
        
        try:
            result = process_incident_with_notifications(scenario["data"])
            processed_incidents.append(result)
            
            print(f"✅ Processed: {result['incident_id']}")
            print(f"📊 Severity: {result['severity']}")
            print(f"👥 Teams: {', '.join(result['assigned_teams'])}")
            print(f"⚡ Escalation: {'Yes' if result['escalation_needed'] else 'No'}")
            print(f"📢 Notifications: {'Sent' if result['notifications_sent'] else 'Disabled'}")
            print(f"📋 Actions: {len(result['suggested_actions'])} suggested")
            
            # Show first few actions
            for j, action in enumerate(result['suggested_actions'][:2], 1):
                print(f"   {j}. {action}")
            if len(result['suggested_actions']) > 2:
                print(f"   ... and {len(result['suggested_actions']) - 2} more")
                
        except Exception as e:
            print(f"❌ Error processing incident: {e}")
    
    # Demo escalation with notification
    if processed_incidents:
        print(f"\n🚨 Demonstrating Escalation Notification...")
        print("-" * 50)
        
        first_incident = processed_incidents[0]
        escalation_success = escalate_incident_with_notification(
            incident_id=first_incident["incident_id"],
            escalation_reason="Initial response team unable to resolve within SLA",
            incident_data={
                "incident_id": first_incident["incident_id"],
                "severity": "critical",
                "title": scenarios[0]["data"]["title"],
                "description": scenarios[0]["data"]["description"],
                "affected_systems": scenarios[0]["data"]["affected_systems"],
                "assigned_teams": first_incident["assigned_teams"]
            }
        )
        
        if escalation_success:
            print("✅ Escalation notification sent successfully")
        else:
            print("❌ Escalation notification failed")
    
    print(f"\n🎉 Notification Demo completed!")
    
    if slack_notifier and slack_notifier.is_enabled():
        print(f"📱 Check your Slack channels for notifications:")
        print(f"   • {slack_notifier.default_channel} (all incidents)")
        for team, channel in slack_notifier.team_channels.items():
            print(f"   • {channel} ({team} team)")
    else:
        print(f"💡 To see notifications in action:")
        print(f"   1. Create a Slack webhook: https://api.slack.com/messaging/webhooks")
        print(f"   2. Copy .env.example to .env")
        print(f"   3. Set SLACK_WEBHOOK_URL in .env")
        print(f"   4. Run this demo again")
    
    print(f"\n📊 Summary:")
    print(f"   • Processed {len(processed_incidents)} incidents")
    print(f"   • Notifications: {'Enabled' if slack_notifier and slack_notifier.is_enabled() else 'Disabled'}")
    print(f"   • All incidents triaged and routed successfully")


if __name__ == "__main__":
    demo_notification_system()