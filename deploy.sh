#!/bin/bash
# Incident Triage Agent MVP - Deployment Script

set -e

echo "🚀 Deploying Incident Triage Agent MVP..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Create logs directory
mkdir -p logs

# Build and start the services
echo "📦 Building Docker image..."
docker-compose build

echo "🔧 Starting services..."
docker-compose up -d

# Wait for the service to be ready
echo "⏳ Waiting for service to be ready..."
sleep 10

# Health check
echo "🏥 Performing health check..."
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ Service is healthy!"
else
    echo "❌ Health check failed. Checking logs..."
    docker-compose logs incident-agent
    exit 1
fi

echo ""
echo "🎉 Deployment successful!"
echo ""
echo "📖 API Documentation: http://localhost:8000/docs"
echo "🔍 Health Check: http://localhost:8000/health"
echo "📊 System Stats: http://localhost:8000/stats"
echo ""
echo "🔧 Management Commands:"
echo "  View logs: docker-compose logs -f incident-agent"
echo "  Stop service: docker-compose down"
echo "  Restart: docker-compose restart"
echo "  Update: docker-compose pull && docker-compose up -d"
echo ""
echo "💡 To test the API, run: python demo_api.py"