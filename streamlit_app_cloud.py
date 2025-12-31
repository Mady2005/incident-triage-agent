"""Streamlit web interface for the Incident Triage Agent MVP - Cloud Demo Version."""

import streamlit as st
import json
from datetime import datetime, timedelta
import pandas as pd
from typing import Dict, Any, List
import time
import random

# Configure Streamlit page
st.set_page_config(
    page_title="Incident Triage Agent - Demo",
    page_icon="🚨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .incident-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
        border-left: 4px solid #ff6b6b;
    }
    .incident-card.critical {
        border-left-color: #ff4757;
        background-color: #fff5f5;
    }
    .incident-card.high {
        border-left-color: #ffa502;
        background-color: #fffbf0;
    }
    .incident-card.medium {
        border-left-color: #3742fa;
        background-color: #f0f4ff;
    }
    .incident-card.low {
        border-left-color: #2ed573;
        background-color: #f0fff4;
    }
    .metric-card {
        background-color: #ffffff;
        padding: 1rem;
        border-radius: 0.5rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        text-align: center;
    }
    .status-badge {
        padding: 0.25rem 0.5rem;
        border-radius: 0.25rem;
        font-size: 0.8rem;
        font-weight: bold;
    }
    .status-open { background-color: #ff6b6b; color: white; }
    .status-in_progress { background-color: #ffa502; color: white; }
    .status-resolved { background-color: #2ed573; color: white; }
    .demo-banner {
        background-color: #e3f2fd;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #2196f3;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state for demo data
if 'incidents' not in st.session_state:
    st.session_state.incidents = [
        {
            "incident_id": "INC-20241231-DEMO001",
            "title": "Database connection timeout",
            "description": "Multiple users reporting slow response times",
            "severity": "high",
            "status": "in_progress",
            "assigned_teams": ["Backend", "SRE"],
            "affected_systems": ["database", "api"],
            "escalation_needed": True,
            "created_at": (datetime.now() - timedelta(hours=2)).isoformat(),
            "updated_at": (datetime.now() - timedelta(minutes=30)).isoformat(),
            "suggested_actions": [
                "Check database connection pool status",
                "Review recent database queries for performance issues",
                "Scale database resources if needed",
                "Notify primary on-call engineer"
            ]
        },
        {
            "incident_id": "INC-20241231-DEMO002", 
            "title": "Authentication service errors",
            "description": "Users unable to log in to the application",
            "severity": "critical",
            "status": "open",
            "assigned_teams": ["Security", "Backend"],
            "affected_systems": ["auth", "api"],
            "escalation_needed": True,
            "created_at": (datetime.now() - timedelta(minutes=45)).isoformat(),
            "updated_at": (datetime.now() - timedelta(minutes=45)).isoformat(),
            "suggested_actions": [
                "Immediately investigate authentication service",
                "Check OAuth provider status",
                "Review security logs for anomalies",
                "Set up incident war room"
            ]
        },
        {
            "incident_id": "INC-20241231-DEMO003",
            "title": "Frontend deployment issues",
            "description": "New deployment causing UI rendering problems",
            "severity": "medium",
            "status": "resolved",
            "assigned_teams": ["Frontend"],
            "affected_systems": ["frontend"],
            "escalation_needed": False,
            "created_at": (datetime.now() - timedelta(hours=4)).isoformat(),
            "updated_at": (datetime.now() - timedelta(hours=1)).isoformat(),
            "suggested_actions": [
                "Rollback to previous deployment",
                "Review deployment pipeline",
                "Test in staging environment"
            ]
        }
    ]

def simulate_ai_triage(incident_data: Dict[str, Any]) -> Dict[str, Any]:
    """Simulate AI triage processing."""
    
    # Simulate processing time
    time.sleep(2)
    
    # Generate incident ID
    incident_id = f"INC-{datetime.now().strftime('%Y%m%d')}-{random.randint(100000, 999999):06d}"
    
    # AI severity classification based on keywords
    severity_keywords = {
        "critical": ["outage", "down", "critical", "emergency", "security breach", "data loss"],
        "high": ["slow", "timeout", "error", "failure", "performance"],
        "medium": ["issue", "problem", "bug", "glitch"],
        "low": ["question", "request", "minor"]
    }
    
    severity = "medium"  # default
    description_lower = incident_data.get("description", "").lower()
    title_lower = incident_data.get("title", "").lower()
    
    for sev, keywords in severity_keywords.items():
        if any(keyword in description_lower or keyword in title_lower for keyword in keywords):
            severity = sev
            break
    
    # Team assignment based on affected systems
    team_mapping = {
        "database": ["Backend", "SRE"],
        "api": ["Backend"],
        "frontend": ["Frontend"],
        "auth": ["Security", "Backend"],
        "infrastructure": ["SRE"],
        "network": ["SRE", "Infrastructure"],
        "storage": ["SRE"]
    }
    
    assigned_teams = set()
    for system in incident_data.get("affected_systems", []):
        assigned_teams.update(team_mapping.get(system, ["Backend"]))
    
    if not assigned_teams:
        assigned_teams = {"Backend"}
    
    # Generate suggested actions
    actions = [
        "Review recent deployments and changes",
        "Check monitoring dashboards for anomalies", 
        "Gather additional logs and metrics",
        "Document timeline and initial findings"
    ]
    
    if severity in ["critical", "high"]:
        actions.extend([
            "Notify primary on-call engineer immediately",
            "Set up incident war room/bridge",
            "Prepare communication for stakeholders"
        ])
    
    return {
        "incident_id": incident_id,
        "title": incident_data["title"],
        "description": incident_data["description"],
        "severity": severity,
        "status": "open",
        "assigned_teams": list(assigned_teams),
        "affected_systems": incident_data.get("affected_systems", []),
        "escalation_needed": severity in ["critical", "high"],
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "suggested_actions": actions,
        "source": incident_data.get("source", "demo"),
        "reporter": incident_data.get("reporter", "demo-user")
    }

def main():
    """Main Streamlit application."""
    
    # Demo banner
    st.markdown("""
    <div class="demo-banner">
        <h3>🎯 AI-Powered Incident Triage Agent - Live Demo</h3>
        <p><strong>This is a demonstration version</strong> showcasing the complete incident management system with simulated AI processing. 
        In production, this connects to a FastAPI backend with real AI models.</p>
        <p><strong>GitHub:</strong> <a href="https://github.com/Mady2005/incident-triage-agent" target="_blank">https://github.com/Mady2005/incident-triage-agent</a></p>
    </div>
    """, unsafe_allow_html=True)
    
    # Header
    st.title("🚨 Incident Triage Agent MVP")
    st.markdown("**Intelligent incident management with automated triage and response coordination**")
    
    # Sidebar
    st.sidebar.title("Navigation")
    page = st.sidebar.selectbox(
        "Choose a page",
        ["Dashboard", "Create Incident", "Incident Details", "System Health"]
    )
    
    if page == "Dashboard":
        show_dashboard()
    elif page == "Create Incident":
        show_create_incident()
    elif page == "Incident Details":
        show_incident_details()
    elif page == "System Health":
        show_system_health()

def show_dashboard():
    """Show the main dashboard."""
    st.header("📊 Incident Dashboard")
    
    incidents = st.session_state.incidents
    
    # Metrics row
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <h3>🎯 Total Incidents</h3>
            <h2>{len(incidents)}</h2>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        escalated = len([i for i in incidents if i.get("escalation_needed")])
        rate = int((escalated / len(incidents)) * 100) if incidents else 0
        st.markdown(f"""
        <div class="metric-card">
            <h3>⚡ Escalation Rate</h3>
            <h2>{rate}%</h2>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        active_incidents = len([i for i in incidents if i.get("status") != "resolved"])
        st.markdown(f"""
        <div class="metric-card">
            <h3>🔥 Active Incidents</h3>
            <h2>{active_incidents}</h2>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        critical_incidents = len([i for i in incidents if i.get("severity") == "critical"])
        st.markdown(f"""
        <div class="metric-card">
            <h3>🚨 Critical</h3>
            <h2>{critical_incidents}</h2>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Recent incidents
    st.subheader("📋 Recent Incidents")
    
    if not incidents:
        st.info("No incidents found. Create your first incident using the sidebar!")
        return
    
    # Display incidents
    for incident in incidents:
        severity = incident.get("severity", "unknown")
        status = incident.get("status", "open")
        
        # Create incident card
        st.markdown(f"""
        <div class="incident-card {severity}">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <h4>🎯 {incident.get('incident_id', 'Unknown ID')}</h4>
                    <p><strong>{incident.get('title', 'No title')}</strong></p>
                    <p>Teams: {', '.join(incident.get('assigned_teams', []))}</p>
                </div>
                <div>
                    <span class="status-badge status-{status}">{status.upper()}</span>
                    <br><br>
                    <span style="font-size: 0.9rem; color: #666;">
                        Severity: <strong>{severity.upper()}</strong>
                    </span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

def show_create_incident():
    """Show the create incident form."""
    st.header("🆕 Create New Incident")
    
    st.info("🤖 This demo simulates AI-powered triage processing. In production, this uses real AI models for intelligent classification.")
    
    with st.form("create_incident_form"):
        st.subheader("Incident Information")
        
        col1, col2 = st.columns(2)
        
        with col1:
            title = st.text_input("Incident Title*", placeholder="Brief description of the issue")
            source = st.selectbox("Source", ["monitoring", "user_report", "api", "chat"])
            reporter = st.text_input("Reporter", placeholder="Who is reporting this incident?")
        
        with col2:
            affected_systems = st.multiselect(
                "Affected Systems",
                ["database", "api", "frontend", "auth", "infrastructure", "network", "storage"]
            )
            severity_indicators = st.multiselect(
                "Severity Indicators",
                ["critical", "outage", "performance", "security", "timeout", "error", "slow", "down"]
            )
        
        description = st.text_area(
            "Detailed Description*",
            placeholder="Provide detailed information about the incident...",
            height=100
        )
        
        error_logs = st.text_area(
            "Error Logs (Optional)",
            placeholder="Paste relevant error logs here...",
            height=80
        )
        
        submitted = st.form_submit_button("🚨 Create Incident", type="primary")
        
        if submitted:
            if not title or not description:
                st.error("❌ Title and Description are required!")
                return
            
            # Prepare incident data
            incident_data = {
                "title": title,
                "description": description,
                "source": source,
                "reporter": reporter or "demo-user",
                "affected_systems": affected_systems,
                "error_logs": error_logs if error_logs else None,
                "severity_indicators": severity_indicators
            }
            
            # Simulate AI processing
            with st.spinner("🔄 Processing incident through AI triage..."):
                incident = simulate_ai_triage(incident_data)
            
            # Add to session state
            st.session_state.incidents.insert(0, incident)
            
            st.success("✅ Incident created successfully!")
            
            # Show results
            st.subheader("🎯 AI Triage Results")
            
            col1, col2 = st.columns(2)
            with col1:
                st.info(f"**Incident ID:** {incident['incident_id']}")
                st.info(f"**Severity:** {incident['severity'].upper()}")
                st.info(f"**Status:** {incident['status'].upper()}")
            
            with col2:
                st.info(f"**Assigned Teams:** {', '.join(incident['assigned_teams'])}")
                st.info(f"**Escalation Needed:** {'Yes' if incident['escalation_needed'] else 'No'}")
            
            # Show suggested actions
            if incident.get('suggested_actions'):
                st.subheader("📋 AI-Generated Suggested Actions")
                for i, action in enumerate(incident['suggested_actions'], 1):
                    st.write(f"{i}. {action}")

def show_incident_details():
    """Show detailed incident information."""
    st.header("🔍 Incident Details")
    
    incidents = st.session_state.incidents
    if not incidents:
        st.info("No incidents found.")
        return
    
    # Incident selector
    incident_options = {f"{inc['incident_id']} - {inc['title']}": inc for inc in incidents}
    selected = st.selectbox("Select an incident:", list(incident_options.keys()))
    
    if selected:
        details = incident_options[selected]
        
        # Header info
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Severity", details.get('severity', 'Unknown').upper())
        with col2:
            st.metric("Status", details.get('status', 'Unknown').upper())
        with col3:
            escalation = "Yes" if details.get('escalation_needed') else "No"
            st.metric("Escalation Needed", escalation)
        
        # Incident information
        st.subheader("📋 Incident Information")
        st.write(f"**Title:** {details.get('title', 'N/A')}")
        st.write(f"**Description:** {details.get('description', 'N/A')}")
        st.write(f"**Reporter:** {details.get('reporter', 'N/A')}")
        st.write(f"**Source:** {details.get('source', 'N/A')}")
        
        # Systems and teams
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("🖥️ Affected Systems")
            systems = details.get('affected_systems', [])
            if systems:
                for system in systems:
                    st.write(f"• {system}")
            else:
                st.write("No systems specified")
        
        with col2:
            st.subheader("👥 Assigned Teams")
            teams = details.get('assigned_teams', [])
            if teams:
                for team in teams:
                    st.write(f"• {team}")
            else:
                st.write("No teams assigned")
        
        # Suggested actions
        if details.get('suggested_actions'):
            st.subheader("📋 AI-Generated Suggested Actions")
            for i, action in enumerate(details['suggested_actions'], 1):
                st.write(f"{i}. {action}")
        
        # Timestamps
        st.subheader("⏰ Timeline")
        if details.get('created_at'):
            st.write(f"**Created:** {details['created_at']}")
        if details.get('updated_at'):
            st.write(f"**Updated:** {details['updated_at']}")

def show_system_health():
    """Show system health and statistics."""
    st.header("🏥 System Health")
    
    incidents = st.session_state.incidents
    
    # Overview metrics
    st.subheader("📊 System Overview")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Incidents", len(incidents))
    with col2:
        escalated = len([i for i in incidents if i.get("escalation_needed")])
        rate = int((escalated / len(incidents)) * 100) if incidents else 0
        st.metric("Escalation Rate", f"{rate}%")
    with col3:
        active = len([i for i in incidents if i.get('status') != 'resolved'])
        st.metric("Active Incidents", active)
    
    # Severity distribution
    st.subheader("📈 Severity Distribution")
    severity_counts = {}
    for incident in incidents:
        severity = incident.get('severity', 'unknown')
        severity_counts[severity] = severity_counts.get(severity, 0) + 1
    
    if severity_counts:
        df = pd.DataFrame(list(severity_counts.items()), columns=['Severity', 'Count'])
        st.bar_chart(df.set_index('Severity'))
    else:
        st.info("No severity data available")
    
    # Team workload
    st.subheader("👥 Team Workload")
    team_counts = {}
    for incident in incidents:
        for team in incident.get('assigned_teams', []):
            team_counts[team] = team_counts.get(team, 0) + 1
    
    if team_counts:
        df = pd.DataFrame(list(team_counts.items()), columns=['Team', 'Incidents'])
        st.bar_chart(df.set_index('Team'))
    else:
        st.info("No team workload data available")
    
    # Recent activity
    st.subheader("📅 Recent Activity")
    if incidents:
        timeline_data = []
        for incident in incidents:
            timeline_data.append({
                'Incident ID': incident.get('incident_id', 'Unknown'),
                'Title': incident.get('title', 'No title')[:50] + '...' if len(incident.get('title', '')) > 50 else incident.get('title', 'No title'),
                'Severity': incident.get('severity', 'unknown'),
                'Status': incident.get('status', 'open'),
                'Teams': ', '.join(incident.get('assigned_teams', []))
            })
        
        df = pd.DataFrame(timeline_data)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No recent activity")

if __name__ == "__main__":
    main()