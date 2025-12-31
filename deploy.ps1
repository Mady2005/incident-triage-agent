# Incident Triage Agent MVP - PowerShell Deployment Script

Write-Host "🚀 Deploying Incident Triage Agent MVP..." -ForegroundColor Green

# Check if Docker is installed
try {
    docker --version | Out-Null
} catch {
    Write-Host "❌ Docker is not installed. Please install Docker Desktop first." -ForegroundColor Red
    exit 1
}

# Check if Docker Compose is available
try {
    docker-compose --version | Out-Null
} catch {
    Write-Host "❌ Docker Compose is not available. Please ensure Docker Desktop is running." -ForegroundColor Red
    exit 1
}

# Create logs directory
if (!(Test-Path "logs")) {
    New-Item -ItemType Directory -Path "logs" | Out-Null
}

# Build and start the services
Write-Host "📦 Building Docker image..." -ForegroundColor Yellow
docker-compose build

Write-Host "🔧 Starting services..." -ForegroundColor Yellow
docker-compose up -d

# Wait for the service to be ready
Write-Host "⏳ Waiting for service to be ready..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

# Health check
Write-Host "🏥 Performing health check..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 10
    if ($response.StatusCode -eq 200) {
        Write-Host "✅ Service is healthy!" -ForegroundColor Green
    } else {
        throw "Health check returned status code: $($response.StatusCode)"
    }
} catch {
    Write-Host "❌ Health check failed. Checking logs..." -ForegroundColor Red
    docker-compose logs incident-agent
    exit 1
}

Write-Host ""
Write-Host "🎉 Deployment successful!" -ForegroundColor Green
Write-Host ""
Write-Host "📖 API Documentation: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "🔍 Health Check: http://localhost:8000/health" -ForegroundColor Cyan
Write-Host "📊 System Stats: http://localhost:8000/stats" -ForegroundColor Cyan
Write-Host ""
Write-Host "🔧 Management Commands:" -ForegroundColor Yellow
Write-Host "  View logs: docker-compose logs -f incident-agent"
Write-Host "  Stop service: docker-compose down"
Write-Host "  Restart: docker-compose restart"
Write-Host "  Update: docker-compose pull; docker-compose up -d"
Write-Host ""
Write-Host "💡 To test the API, run: python demo_api.py" -ForegroundColor Magenta