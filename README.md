# 🚨 Incident Triage Agent

**AI-Powered Incident Management System with Intelligent Triage and Response Coordination**

**Created by: Mady2005**

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red.svg)](https://streamlit.io/)
[![LangGraph](https://img.shields.io/badge/LangGraph-Latest-purple.svg)](https://langchain-ai.github.io/langgraph/)

## 🎯 **Overview**

The Incident Triage Agent is my comprehensive AI-powered system that automates incident management workflows. It intelligently classifies incidents, routes them to appropriate teams, and provides actionable response recommendations.

### **Key Features**

🤖 **AI-Powered Triage** - Automatic severity classification and team routing  
📊 **Web Dashboard** - Beautiful Streamlit interface for incident management  
🔧 **Comprehensive Tools** - 12+ integrated tools for complete incident lifecycle  
📡 **REST API** - Full FastAPI backend with 8 endpoints  
🔔 **Smart Notifications** - Slack integration with rich formatting  
📈 **Real-time Monitoring** - System health checks and metrics analysis  
🧪 **Thoroughly Tested** - 75+ tests with property-based testing  
🐳 **Production Ready** - Docker deployment with monitoring  

## 🚀 **Quick Start**

### **1. Clone and Setup**
```bash
git clone https://github.com/Mady2005/incident-triage-agent.git
cd incident-triage-agent
pip install -r requirements.txt
```

### **2. Launch the MVP**
```bash
# Start both API and Streamlit interface
python run_streamlit.py
```

### **3. Access Your Application**
- **Web Interface:** http://localhost:8501
- **API Docs:** http://localhost:8000/docs
- **Health Check:** http://localhost:8000/health

## 📱 **Web Interface Features**

### **Dashboard** 📊
- Real-time incident metrics and statistics
- Visual severity indicators with color coding
- Quick actions for incident management
- Recent incidents overview

### **Create Incident** 🆕
- Smart form with validation
- AI-powered processing with immediate results
- Automatic team assignment and severity classification
- Generated action recommendations

### **Incident Details** 🔍
- Complete incident information and timeline
- Team assignments and status tracking
- AI-generated suggested actions
- System impact analysis

### **System Health** 🏥
- Overall system statistics and trends
- Severity distribution charts
- Team workload monitoring
- Recent activity timeline

## 🏗️ **Architecture**

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Streamlit     │    │    FastAPI       │    │   LangGraph     │
│   Frontend      │◄──►│    Backend       │◄──►│   Workflow      │
│   (Port 8501)   │    │   (Port 8000)    │    │   Engine        │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Web UI        │    │   REST API       │    │   AI Tools      │
│   - Dashboard   │    │   - 8 Endpoints  │    │   - 12+ Tools   │
│   - Forms       │    │   - Validation   │    │   - Runbooks    │
│   - Charts      │    │   - Storage      │    │   - Diagnostics │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## 🔧 **Core Components**

### **AI Workflow Engine** (`src/incident_agent/`)
- **LangGraph Pipeline** - 3-node workflow (Triage → Route → Respond)
- **Intelligent Classification** - Severity and team assignment
- **Action Generation** - Context-aware response recommendations

### **Tools Integration** (`src/incident_agent/tools/`)
- **Incident Management** - CRUD operations with timeline tracking
- **Notifications** - Multi-channel alerts with audience-specific formatting
- **Diagnostics** - Runbook lookup, metrics analysis, health checks

### **API Layer** (`src/incident_agent/api/`)
- **FastAPI Backend** - 8 REST endpoints with full documentation
- **Data Validation** - Pydantic models with comprehensive validation
- **Error Handling** - Graceful degradation and detailed error responses

### **Notifications** (`src/incident_agent/notifications/`)
- **Slack Integration** - Rich message formatting with team channels
- **Multi-audience** - Technical, management, and customer communications
- **Escalation Workflows** - Automated escalation with context preservation

## 📊 **Sample Usage**

### **Create an Incident**
```python
import requests

incident = {
    "title": "Database connection failure",
    "description": "All database connections are failing",
    "source": "monitoring",
    "reporter": "ops-team",
    "affected_systems": ["database", "api", "auth"],
    "severity_indicators": ["critical", "outage", "database"]
}

response = requests.post("http://localhost:8000/incidents/", json=incident)
print(response.json())
```

### **Expected AI Response**
```json
{
    "incident_id": "INC-20241231-A1B2C3D4",
    "severity": "critical",
    "assigned_teams": ["Backend", "SRE", "Security"],
    "suggested_actions": [
        "Notify primary on-call engineer immediately",
        "Set up incident war room/bridge",
        "Check database server status and connectivity",
        "Verify connection pool configuration",
        "Scale database resources if needed"
    ],
    "escalation_needed": true
}
```

## 🧪 **Testing**

### **Run All Tests**
```bash
# Run the complete test suite (75+ tests)
python -m pytest tests/incident_agent/ -v

# Run specific test categories
python -m pytest tests/incident_agent/test_incident_tools.py -v
python -m pytest tests/incident_agent/test_diagnostic_tools.py -v
python -m pytest tests/incident_agent/test_api.py -v
```

### **Test Coverage**
- **Incident Tools** - 9 tests covering CRUD operations
- **Diagnostic Tools** - 18 tests covering health checks and metrics
- **Notification Tools** - 10 tests covering multi-channel alerts
- **API Integration** - 13 tests covering all endpoints
- **Workflow Integration** - End-to-end testing

## 🚀 **Deployment**

### **Docker Deployment**
```bash
# Build and run with Docker
docker-compose up -d

# Access at http://localhost:8501
```

### **Manual Deployment**
```bash
# Terminal 1: Start API
python run_api.py

# Terminal 2: Start Streamlit
streamlit run streamlit_app.py --server.port 8501
```

### **Environment Configuration**
```bash
# Optional: For full AI functionality
export OPENAI_API_KEY="your-openai-key"

# Optional: For Slack notifications
export SLACK_WEBHOOK_URL="your-slack-webhook"
export SLACK_DEFAULT_CHANNEL="#incidents"
```

## 📈 **Demo Scripts**

### **API Demo**
```bash
python demo_api.py
```
Demonstrates all API endpoints with sample incidents.

### **Tools Demo**
```bash
python demo_incident_agent_tools.py
```
Shows comprehensive tool integration with diagnostic capabilities.

### **Notifications Demo**
```bash
python demo_notifications.py
```
Tests Slack notification system with different message types.

## 🎯 **Use Cases**

### **DevOps Teams**
- Automated incident triage and routing
- Integration with monitoring systems
- Standardized response procedures

### **SRE Teams**
- Intelligent escalation workflows
- Runbook automation and recommendations
- System health monitoring

### **Security Teams**
- Security incident classification
- Automated containment suggestions
- Compliance reporting

### **Management**
- Real-time incident visibility
- Executive summaries and reporting
- Team workload monitoring

## 🔧 **Customization**

### **Add New Teams**
Edit `src/incident_agent/models/team.py`:
```python
AVAILABLE_TEAMS = [
    "Backend", "Frontend", "SRE", "Security", 
    "YourNewTeam"  # Add your team here
]
```

### **Add New Systems**
Edit `streamlit_app.py` and API models:
```python
affected_systems = ["database", "api", "your-system"]
```

### **Custom Runbooks**
Edit `src/incident_agent/tools/diagnostic_tools.py`:
```python
RUNBOOK_DATABASE = {
    "your-system": {
        "your-issue": {
            "title": "Your Issue Resolution",
            "steps": ["Step 1", "Step 2", "Step 3"]
        }
    }
}
```

## 🤝 **Contributing**

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 **License**

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 **Acknowledgments**

- **LangGraph** - For the powerful workflow orchestration
- **FastAPI** - For the excellent API framework
- **Streamlit** - For the beautiful web interface
- **Pydantic** - For robust data validation

---

## 🎉 **Get Started Now!**

```bash
git clone https://github.com/Mady2005/incident-triage-agent.git
cd incident-triage-agent
python run_streamlit.py
```

**Your AI-powered incident management system will be running at http://localhost:8501** 🚀

---

**Built with ❤️ by Mady2005 for better incident response**