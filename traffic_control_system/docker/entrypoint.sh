#!/bin/bash

# Traffic Control System Docker Entrypoint Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

# Initialize application
initialize_app() {
    log "Initializing Traffic Control System..."
    
    # Create required directories
    mkdir -p /app/data/{models,datasets,logs}
    mkdir -p /app/logs
    mkdir -p /app/temp
    
    # Set permissions
    chmod -R 755 /app/data
    chmod -R 755 /app/logs
    chmod -R 755 /app/temp
    
    # Initialize database if it doesn't exist
    if [ ! -f "/app/data/security_db.sqlite" ]; then
        log "Initializing security database..."
        python3 -c "
from src.security.security_system import SecuritySystem
security_system = SecuritySystem('/app/data/security_db.sqlite')
print('Security database initialized successfully')
"
    fi
    
    # Download pre-trained models if needed
    if [ ! -f "/app/data/models/yolov8n.pt" ]; then
        log "Downloading YOLOv8 model..."
        mkdir -p /app/data/models
        wget -O /app/data/models/yolov8n.pt https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.pt
    fi
    
    log "Initialization complete!"
}

# Check GPU availability
check_gpu() {
    if command -v nvidia-smi &> /dev/null; then
        log "GPU detected:"
        nvidia-smi --query-gpu=name,memory.total,memory.free --format=csv,noheader,nounits
    else
        warn "No GPU detected, using CPU mode"
    fi
}

# Start dashboard service
start_dashboard() {
    log "Starting Streamlit dashboard..."
    cd /app
    exec streamlit run src/dashboard/streamlit_dashboard.py \
        --server.port=8501 \
        --server.address=0.0.0.0 \
        --server.headless=true \
        --server.fileWatcherType=none \
        --browser.gatherUsageStats=false
}

# Start API service
start_api() {
    log "Starting FastAPI service..."
    cd /app
    exec uvicorn src.api.main:app \
        --host 0.0.0.0 \
        --port 8502 \
        --reload
}

# Start training service
start_training() {
    log "Starting DRL training..."
    cd /app
    python3 -m src.control.drl_traffic_agent
}

# Start simulation service
start_simulation() {
    log "Starting SUMO simulation..."
    cd /app
    python3 -m src.simulation.sumo_environment
}

# Start detection service
start_detection() {
    log "Starting detection service..."
    cd /app
    python3 -m src.detection.yolo_detector
}

# Start all services
start_all() {
    log "Starting all services..."
    
    # Start services in background
    start_api &
    API_PID=$!
    
    # Start dashboard in foreground
    start_dashboard
}

# Health check
health_check() {
    log "Performing health check..."
    
    # Check if dashboard is running
    if curl -f http://localhost:8501/_stcore/health > /dev/null 2>&1; then
        log "Dashboard: OK"
    else
        error "Dashboard: FAILED"
        exit 1
    fi
    
    # Check if API is running
    if curl -f http://localhost:8502/health > /dev/null 2>&1; then
        log "API: OK"
    else
        warn "API: Not responding"
    fi
    
    # Check GPU
    check_gpu
    
    log "Health check complete"
}

# Show usage
show_usage() {
    echo "Traffic Control System Docker Container"
    echo ""
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  dashboard    Start Streamlit dashboard (default)"
    echo "  api          Start FastAPI service"
    echo "  training     Start DRL training"
    echo "  simulation   Start SUMO simulation"
    echo "  detection    Start detection service"
    echo "  all          Start all services"
    echo "  health       Perform health check"
    echo "  bash         Open bash shell"
    echo "  help         Show this help message"
}

# Main execution
main() {
    log "Traffic Control System starting..."
    
    # Initialize application
    initialize_app
    
    # Check GPU
    check_gpu
    
    # Parse command
    COMMAND=${1:-dashboard}
    
    case "$COMMAND" in
        dashboard)
            start_dashboard
            ;;
        api)
            start_api
            ;;
        training)
            start_training
            ;;
        simulation)
            start_simulation
            ;;
        detection)
            start_detection
            ;;
        all)
            start_all
            ;;
        health)
            health_check
            ;;
        bash)
            log "Opening bash shell..."
            exec /bin/bash
            ;;
        help)
            show_usage
            ;;
        *)
            error "Unknown command: $COMMAND"
            show_usage
            exit 1
            ;;
    esac
}

# Trap signals for graceful shutdown
trap 'log "Shutting down..."; kill $(jobs -p) 2>/dev/null; exit 0' SIGTERM SIGINT

# Run main function
main "$@"