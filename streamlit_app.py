"""Streamlit web interface for the Incident Triage Agent MVP."""

import streamlit as st
import requests
import json
from datetime import datetime
import pandas as pd
from typing import Dict, Any, List
import time

# Configure Streamlit page
st.set_page_config(
    page_title="Incident Triage Agent",
    page_icon="🚨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API Configuration
API_BASE_URL = "http://localhost:8000"

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
</style>
""", unsafe_allow_html=True)

def check_api_health() -> bool:
    """Check if the API is running."""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        return response.status_code == 200
    except:
        return False

def create_incident(incident_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new incident via API."""
    try:
        response = requests.post(f"{API_BASE_URL}/incidents/", json=incident_data, timeout=30)
        if response.status_code == 201:
            return {"success": True, "data": response.json()}
        else:
            return {"success": False, "error": f"API Error: {response.status_code}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def get_incidents() -> List[Dict[str, Any]]:
    """Get all incidents from API."""
    try:
        response = requests.get(f"{API_BASE_URL}/incidents/", timeout=10)
        if response.status_code == 200:
            return response.json()
        return []
    except:
        return []

def get_incident_details(incident_id: str) -> Dict[str, Any]:
    """Get detailed incident information."""
    try:
        response = requests.get(f"{API_BASE_URL}/incidents/{incident_id}", timeout=10)
        if response.status_code == 200:
            return response.json()
        return {}
    except:
        return {}

def get_system_stats() -> Dict[str, Any]:
    """Get system statistics."""
    try:
        response = requests.get(f"{API_BASE_URL}/stats", timeout=10)
        if response.status_code == 200:
            return response.json()
        return {}
    except:
        return {}

def escalate_incident(incident_id: str, reason: str, urgency: str, target_team: str) -> bool:
    """Escalate an incident."""
    try:
        data = {
            "escalation_reason": reason,
            "urgency_level": urgency,
            "target_team": target_team,
            "additional_context": f"Escalated via Streamlit interface at {datetime.now().isoformat()}"
        }
        response = requests.post(f"{API_BASE_URL}/incidents/{incident_id}/escalate", json=data, timeout=10)
        return response.status_code == 200
    except:
        return False

def main():
    """Main Streamlit application."""
    
    # Header
    st.title("🚨 Incident Triage Agent MVP")
    st.markdown("**Intelligent incident management with automated triage and response coordination**")
    
    # Check API status
    api_healthy = check_api_health()
    
    if not api_healthy:
        st.error("🔴 API Server is not running! Please start the API server first:")
        st.code("python run_api.py", language="bash")
        st.stop()
    
    st.success("🟢 API Server is running")
    
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
    
    # Get system stats
    stats = get_system_stats()
    incidents = get_incidents()
    
    # Metrics row
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("""
        <div class="metric-card">
            <h3>🎯 Total Incidents</h3>
            <h2>{}</h2>
        </div>
        """.format(stats.get("total_incidents", 0)), unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="metric-card">
            <h3>⚡ Escalation Rate</h3>
            <h2>{}%</h2>
        </div>
        """.format(stats.get("escalation_rate", 0)), unsafe_allow_html=True)
    
    with col3:
        active_incidents = len([i for i in incidents if i.get("status") != "resolved"])
        st.markdown("""
        <div class="metric-card">
            <h3>🔥 Active Incidents</h3>
            <h2>{}</h2>
        </div>
        """.format(active_incidents), unsafe_allow_html=True)
    
    with col4:
        critical_incidents = len([i for i in incidents if i.get("severity") == "critical"])
        st.markdown("""
        <div class="metric-card">
            <h3>🚨 Critical</h3>
            <h2>{}</h2>
        </div>
        """.format(critical_incidents), unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Recent incidents
    st.subheader("📋 Recent Incidents")
    
    if not incidents:
        st.info("No incidents found. Create your first incident using the sidebar!")
        return
    
    # Display incidents
    for incident in incidents[:10]:  # Show last 10
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
        
        # Action buttons
        col1, col2, col3 = st.columns([1, 1, 4])
        with col1:
            if st.button(f"📋 Details", key=f"details_{incident['incident_id']}"):
                st.session_state.selected_incident = incident['incident_id']
                st.rerun()
        
        with col2:
            if incident.get("status") != "resolved":
                if st.button(f"⚡ Escalate", key=f"escalate_{incident['incident_id']}"):
                    st.session_state.escalate_incident = incident['incident_id']
                    st.rerun()
    
    # Handle escalation
    if hasattr(st.session_state, 'escalate_incident'):
        incident_id = st.session_state.escalate_incident
        st.subheader(f"⚡ Escalate Incident {incident_id}")
        
        with st.form("escalation_form"):
            reason = st.text_area("Escalation Reason", placeholder="Why is this incident being escalated?")
            urgency = st.selectbox("Urgency Level", ["low", "medium", "high", "critical"])
            target_team = st.selectbox("Target Team", ["management", "senior-sre", "security", "executive"])
            
            if st.form_submit_button("🚀 Escalate Incident"):
                if escalate_incident(incident_id, reason, urgency, target_team):
                    st.success(f"✅ Incident {incident_id} escalated successfully!")
                    del st.session_state.escalate_incident
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("❌ Failed to escalate incident")

def show_create_incident():
    """Show the create incident form."""
    st.header("🆕 Create New Incident")
    
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
                "reporter": reporter or "streamlit-user",
                "affected_systems": affected_systems,
                "error_logs": error_logs if error_logs else None,
                "severity_indicators": severity_indicators
            }
            
            # Create incident
            with st.spinner("🔄 Processing incident through AI triage..."):
                result = create_incident(incident_data)
            
            if result["success"]:
                incident = result["data"]
                st.success("✅ Incident created successfully!")
                
                # Show results
                st.subheader("🎯 Triage Results")
                
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
                    st.subheader("📋 Suggested Actions")
                    for i, action in enumerate(incident['suggested_actions'][:5], 1):
                        st.write(f"{i}. {action}")
                
            else:
                st.error(f"❌ Failed to create incident: {result['error']}")

def show_incident_details():
    """Show detailed incident information."""
    st.header("🔍 Incident Details")
    
    incidents = get_incidents()
    if not incidents:
        st.info("No incidents found.")
        return
    
    # Incident selector
    incident_options = {f"{inc['incident_id']} - {inc['title']}": inc['incident_id'] for inc in incidents}
    selected = st.selectbox("Select an incident:", list(incident_options.keys()))
    
    if selected:
        incident_id = incident_options[selected]
        details = get_incident_details(incident_id)
        
        if details:
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
                st.subheader("📋 Suggested Actions")
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
    
    # Get stats
    stats = get_system_stats()
    incidents = get_incidents()
    
    if not stats:
        st.warning("Unable to fetch system statistics")
        return
    
    # Overview metrics
    st.subheader("📊 System Overview")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Incidents", stats.get("total_incidents", 0))
    with col2:
        st.metric("Escalation Rate", f"{stats.get('escalation_rate', 0)}%")
    with col3:
        active = len([i for i in incidents if i.get('status') != 'resolved'])
        st.metric("Active Incidents", active)
    
    # Severity distribution
    st.subheader("📈 Severity Distribution")
    severity_dist = stats.get("severity_distribution", {})
    if severity_dist:
        df = pd.DataFrame(list(severity_dist.items()), columns=['Severity', 'Count'])
        st.bar_chart(df.set_index('Severity'))
    else:
        st.info("No severity data available")
    
    # Team workload
    st.subheader("👥 Team Workload")
    team_workload = stats.get("team_workload", {})
    if team_workload:
        df = pd.DataFrame(list(team_workload.items()), columns=['Team', 'Incidents'])
        st.bar_chart(df.set_index('Team'))
    else:
        st.info("No team workload data available")
    
    # Recent activity
    st.subheader("📅 Recent Activity")
    if incidents:
        # Create timeline
        timeline_data = []
        for incident in incidents[-10:]:  # Last 10 incidents
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