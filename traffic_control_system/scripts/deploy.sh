#!/bin/bash

# Traffic Control System Deployment Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DOCKER_COMPOSE_FILE="$PROJECT_ROOT/docker-compose.yml"
ENV_FILE="$PROJECT_ROOT/.env"

# Logging functions
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO: $1${NC}"
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    # Check NVIDIA Docker (optional)
    if command -v nvidia-docker &> /dev/null || docker info | grep -q nvidia; then
        log "NVIDIA Docker runtime detected"
    else
        warn "NVIDIA Docker runtime not found. GPU acceleration will not be available."
    fi
    
    # Check available disk space
    AVAILABLE_SPACE=$(df -BG "$PROJECT_ROOT" | awk 'NR==2 {print $4}' | sed 's/G//')
    if [ "$AVAILABLE_SPACE" -lt 10 ]; then
        warn "Less than 10GB disk space available. Consider freeing up space."
    fi
    
    log "Prerequisites check completed"
}

# Create environment file
create_env_file() {
    if [ ! -f "$ENV_FILE" ]; then
        log "Creating environment file..."
        
        cat > "$ENV_FILE" << EOF
# Traffic Control System Environment Configuration

# Display for GUI applications
DISPLAY=${DISPLAY:-:0}

# Database configuration
DB_PATH=/app/data/security_db.sqlite

# Redis configuration
REDIS_URL=redis://redis:6379

# InfluxDB configuration
INFLUXDB_URL=http://influxdb:8086
INFLUXDB_TOKEN=traffic-admin-token-123456789
INFLUXDB_ORG=traffic_org
INFLUXDB_BUCKET=traffic_data

# Email notifications
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
ALERT_EMAIL=security@police.gov.in

# API configuration
API_HOST=0.0.0.0
API_PORT=8502

# Dashboard configuration
DASHBOARD_HOST=0.0.0.0
DASHBOARD_PORT=8501

# Security
SECRET_KEY=$(openssl rand -hex 32)

# Timezone
TZ=Asia/Kolkata

# Log level
LOG_LEVEL=INFO

# Model paths
YOLO_MODEL_PATH=/app/data/models/yolov8n.pt
DRL_MODEL_PATH=/app/data/models/ppo_traffic_model.zip

# SUMO configuration
SUMO_GUI=false
SUMO_STEP_LENGTH=1.0
EOF
        
        log "Environment file created at $ENV_FILE"
        warn "Please edit $ENV_FILE to configure your specific settings"
    else
        log "Environment file already exists"
    fi
}

# Generate SSL certificates
generate_ssl_certs() {
    SSL_DIR="$PROJECT_ROOT/config/nginx/ssl"
    
    if [ ! -d "$SSL_DIR" ]; then
        log "Generating SSL certificates..."
        mkdir -p "$SSL_DIR"
        
        # Generate self-signed certificate
        openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
            -keyout "$SSL_DIR/key.pem" \
            -out "$SSL_DIR/cert.pem" \
            -subj "/C=IN/ST=Karnataka/L=Bangalore/O=Traffic Control System/OU=IT Department/CN=traffic-control.local"
        
        log "SSL certificates generated"
        warn "Using self-signed certificates. For production, use proper SSL certificates."
    else
        log "SSL certificates already exist"
    fi
}

# Create required directories
create_directories() {
    log "Creating required directories..."
    
    mkdir -p "$PROJECT_ROOT"/{data/{models,datasets,logs},logs,temp,config/{grafana,nginx/ssl}}
    
    # Set permissions
    chmod -R 755 "$PROJECT_ROOT/data"
    chmod -R 755 "$PROJECT_ROOT/logs"
    chmod -R 755 "$PROJECT_ROOT/temp"
    
    log "Directories created"
}

# Download required models
download_models() {
    MODELS_DIR="$PROJECT_ROOT/data/models"
    
    if [ ! -f "$MODELS_DIR/yolov8n.pt" ]; then
        log "Downloading YOLOv8 model..."
        mkdir -p "$MODELS_DIR"
        wget -O "$MODELS_DIR/yolov8n.pt" "https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.pt"
        log "YOLOv8 model downloaded"
    else
        log "YOLOv8 model already exists"
    fi
}

# Build Docker images
build_images() {
    log "Building Docker images..."
    
    cd "$PROJECT_ROOT"
    
    if command -v docker-compose &> /dev/null; then
        docker-compose build --no-cache
    else
        docker compose build --no-cache
    fi
    
    log "Docker images built successfully"
}

# Start services
start_services() {
    log "Starting services..."
    
    cd "$PROJECT_ROOT"
    
    if command -v docker-compose &> /dev/null; then
        docker-compose up -d
    else
        docker compose up -d
    fi
    
    log "Services started"
}

# Stop services
stop_services() {
    log "Stopping services..."
    
    cd "$PROJECT_ROOT"
    
    if command -v docker-compose &> /dev/null; then
        docker-compose down
    else
        docker compose down
    fi
    
    log "Services stopped"
}

# Show service status
show_status() {
    log "Service status:"
    
    cd "$PROJECT_ROOT"
    
    if command -v docker-compose &> /dev/null; then
        docker-compose ps
    else
        docker compose ps
    fi
}

# Show logs
show_logs() {
    local service=${1:-}
    
    cd "$PROJECT_ROOT"
    
    if [ -n "$service" ]; then
        log "Showing logs for service: $service"
        if command -v docker-compose &> /dev/null; then
            docker-compose logs -f "$service"
        else
            docker compose logs -f "$service"
        fi
    else
        log "Showing logs for all services"
        if command -v docker-compose &> /dev/null; then
            docker-compose logs -f
        else
            docker compose logs -f
        fi
    fi
}

# Health check
health_check() {
    log "Performing health check..."
    
    # Check dashboard
    if curl -f http://localhost:8501/_stcore/health > /dev/null 2>&1; then
        log "✅ Dashboard: OK"
    else
        error "❌ Dashboard: FAILED"
    fi
    
    # Check API
    if curl -f http://localhost:8502/health > /dev/null 2>&1; then
        log "✅ API: OK"
    else
        error "❌ API: FAILED"
    fi
    
    # Check Grafana
    if curl -f http://localhost:3000/api/health > /dev/null 2>&1; then
        log "✅ Grafana: OK"
    else
        error "❌ Grafana: FAILED"
    fi
    
    # Check Redis
    if docker exec traffic_redis redis-cli ping > /dev/null 2>&1; then
        log "✅ Redis: OK"
    else
        error "❌ Redis: FAILED"
    fi
    
    # Check InfluxDB
    if curl -f http://localhost:8086/health > /dev/null 2>&1; then
        log "✅ InfluxDB: OK"
    else
        error "❌ InfluxDB: FAILED"
    fi
    
    log "Health check completed"
}

# Clean up
cleanup() {
    log "Cleaning up..."
    
    cd "$PROJECT_ROOT"
    
    # Stop and remove containers
    if command -v docker-compose &> /dev/null; then
        docker-compose down -v --remove-orphans
    else
        docker compose down -v --remove-orphans
    fi
    
    # Remove images
    docker image prune -f
    
    # Remove volumes (optional)
    read -p "Do you want to remove data volumes? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker volume prune -f
        warn "Data volumes removed. All data will be lost!"
    fi
    
    log "Cleanup completed"
}

# Full deployment
full_deploy() {
    log "Starting full deployment..."
    
    check_prerequisites
    create_directories
    create_env_file
    generate_ssl_certs
    download_models
    build_images
    start_services
    
    # Wait for services to start
    log "Waiting for services to start..."
    sleep 30
    
    health_check
    
    log "Full deployment completed!"
    info "Access the dashboard at: https://localhost"
    info "Access Grafana at: http://localhost:3000 (admin/trafficcontrol123)"
    info "API documentation at: http://localhost:8502/docs"
}

# Show usage
show_usage() {
    echo "Traffic Control System Deployment Script"
    echo ""
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  deploy       Full deployment (default)"
    echo "  build        Build Docker images"
    echo "  start        Start services"
    echo "  stop         Stop services"
    echo "  restart      Restart services"
    echo "  status       Show service status"
    echo "  logs [svc]   Show logs (optionally for specific service)"
    echo "  health       Perform health check"
    echo "  cleanup      Clean up containers and images"
    echo "  help         Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 deploy          # Full deployment"
    echo "  $0 logs nginx      # Show nginx logs"
    echo "  $0 restart         # Restart all services"
}

# Main execution
main() {
    COMMAND=${1:-deploy}
    
    case "$COMMAND" in
        deploy)
            full_deploy
            ;;
        build)
            check_prerequisites
            create_directories
            build_images
            ;;
        start)
            start_services
            ;;
        stop)
            stop_services
            ;;
        restart)
            stop_services
            sleep 5
            start_services
            ;;
        status)
            show_status
            ;;
        logs)
            show_logs "$2"
            ;;
        health)
            health_check
            ;;
        cleanup)
            cleanup
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
trap 'log "Deployment interrupted"; exit 1' SIGTERM SIGINT

# Run main function
main "$@"