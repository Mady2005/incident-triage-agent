"""Launch script for the Streamlit Incident Triage Agent MVP."""

import subprocess
import sys
import time
import requests
import os

def check_api_running():
    """Check if the API server is running."""
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        return response.status_code == 200
    except:
        return False

def start_api_server():
    """Start the API server in the background."""
    print("🚀 Starting API server...")
    try:
        # Start the API server
        api_process = subprocess.Popen([
            sys.executable, "run_api.py"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Wait a bit for the server to start
        time.sleep(3)
        
        # Check if it's running
        if check_api_running():
            print("✅ API server started successfully at http://localhost:8000")
            return api_process
        else:
            print("❌ Failed to start API server")
            return None
    except Exception as e:
        print(f"❌ Error starting API server: {e}")
        return None

def install_streamlit_requirements():
    """Install Streamlit requirements if needed."""
    try:
        import streamlit
        print("✅ Streamlit already installed")
        return True
    except ImportError:
        print("📦 Installing Streamlit requirements...")
        try:
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", "-r", "requirements-streamlit.txt"
            ])
            print("✅ Streamlit requirements installed")
            return True
        except Exception as e:
            print(f"❌ Failed to install requirements: {e}")
            return False

def main():
    """Main function to launch the Streamlit MVP."""
    print("🚨 Incident Triage Agent MVP - Streamlit Launcher")
    print("=" * 50)
    
    # Install requirements if needed
    if not install_streamlit_requirements():
        return
    
    # Check if API is already running
    if not check_api_running():
        print("🔄 API server not running, starting it...")
        api_process = start_api_server()
        if not api_process:
            print("❌ Cannot start without API server. Please run 'python run_api.py' manually.")
            return
    else:
        print("✅ API server already running at http://localhost:8000")
    
    # Launch Streamlit
    print("🎨 Launching Streamlit interface...")
    print("📱 Your MVP will open in your browser at http://localhost:8501")
    print("=" * 50)
    
    try:
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", "streamlit_app.py",
            "--server.port", "8501",
            "--server.address", "localhost"
        ])
    except KeyboardInterrupt:
        print("\n👋 Shutting down Streamlit...")
    except Exception as e:
        print(f"❌ Error running Streamlit: {e}")

if __name__ == "__main__":
    main()