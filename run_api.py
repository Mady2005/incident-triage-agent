#!/usr/bin/env python3
"""
Startup script for the Incident Triage Agent API.

This script starts the FastAPI server for the incident agent.
"""

import uvicorn
import sys
import os

# Add src to path so imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

if __name__ == "__main__":
    print("🚀 Starting Incident Triage Agent API...")
    print("📖 API Documentation will be available at: http://localhost:8000/docs")
    print("🔍 Health check available at: http://localhost:8000/health")
    print("⚡ Press Ctrl+C to stop the server")
    print("-" * 60)
    
    uvicorn.run(
        "incident_agent.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Enable auto-reload for development
        log_level="info"
    )