"""
FastAPI Backend for Traffic Control System
Provides REST API endpoints for system integration
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
import uvicorn
import logging
import sys
import os
from pathlib import Path
import cv2
import numpy as np
from datetime import datetime
import json

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

# Import project modules
try:
    from src.security.security_system import SecuritySystem, StolenVehicle
    from src.detection.yolo_detector import YOLOVehicleDetector
    from src.tracking.deep_sort_tracker import DeepSORTTracker
    from src.simulation.sumo_environment import SUMOTrafficSimulation
except ImportError as e:
    logging.error(f"Failed to import modules: {e}")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Traffic Control System API",
    description="REST API for AI Traffic Control System",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global system components
security_system = None
detector = None
tracker = None
simulation = None

# Pydantic models for API requests/responses
class VehicleCheck(BaseModel):
    license_plate: str
    confidence: float
    location: str
    camera_id: str
    image_path: Optional[str] = None

class VehicleCheckResponse(BaseModel):
    license_plate: str
    is_stolen: bool
    confidence: float
    match_type: str
    alert_created: bool
    alert_id: Optional[int] = None
    vehicle_info: Optional[Dict] = None

class StolenVehicleAdd(BaseModel):
    license_plate: str
    vehicle_type: str
    color: str
    make: str
    model: str
    year: Optional[int] = None
    case_number: str
    reporting_agency: str
    priority: str = "medium"
    additional_info: Optional[str] = None

class TrafficLightControl(BaseModel):
    traffic_light_id: str
    phase: int
    duration: Optional[float] = None

class DetectionRequest(BaseModel):
    image_path: str
    confidence_threshold: Optional[float] = 0.5

class SystemStatus(BaseModel):
    status: str
    components: Dict[str, bool]
    uptime: str
    last_updated: str


@app.on_event("startup")
async def startup_event():
    """Initialize system components on startup"""
    global security_system, detector, tracker, simulation
    
    logger.info("Initializing Traffic Control System API...")
    
    try:
        # Initialize security system
        security_system = SecuritySystem()
        logger.info("Security system initialized")
        
        # Initialize detector
        detector = YOLOVehicleDetector(confidence_threshold=0.5)
        logger.info("Vehicle detector initialized")
        
        # Initialize tracker
        tracker = DeepSORTTracker()
        logger.info("Vehicle tracker initialized")
        
        # Initialize simulation
        simulation = SUMOTrafficSimulation(gui=False, simulation_time=3600)
        logger.info("Traffic simulation initialized")
        
        logger.info("API startup completed successfully")
        
    except Exception as e:
        logger.error(f"Startup failed: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global simulation
    
    logger.info("Shutting down Traffic Control System API...")
    
    if simulation:
        simulation.close()
    
    logger.info("API shutdown completed")


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


# System status endpoint
@app.get("/status", response_model=SystemStatus)
async def get_system_status():
    """Get overall system status"""
    global security_system, detector, tracker, simulation
    
    components = {
        "security_system": security_system is not None,
        "detector": detector is not None,
        "tracker": tracker is not None,
        "simulation": simulation is not None and simulation.is_running
    }
    
    overall_status = "operational" if all(components.values()) else "degraded"
    
    return SystemStatus(
        status=overall_status,
        components=components,
        uptime="N/A",  # Could be calculated from startup time
        last_updated=datetime.now().isoformat()
    )


# Security endpoints
@app.post("/security/check", response_model=VehicleCheckResponse)
async def check_vehicle(request: VehicleCheck):
    """Check vehicle against stolen database"""
    global security_system
    
    if not security_system:
        raise HTTPException(status_code=503, detail="Security system not available")
    
    try:
        result = security_system.check_vehicle(
            license_plate=request.license_plate,
            confidence=request.confidence,
            location=request.location,
            camera_id=request.camera_id,
            image_path=request.image_path
        )
        
        return VehicleCheckResponse(**result)
        
    except Exception as e:
        logger.error(f"Vehicle check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/security/stolen-vehicle")
async def add_stolen_vehicle(vehicle: StolenVehicleAdd):
    """Add stolen vehicle to database"""
    global security_system
    
    if not security_system:
        raise HTTPException(status_code=503, detail="Security system not available")
    
    try:
        stolen_vehicle = StolenVehicle(
            license_plate=vehicle.license_plate,
            vehicle_type=vehicle.vehicle_type,
            color=vehicle.color,
            make=vehicle.make,
            model=vehicle.model,
            year=vehicle.year,
            reported_date=datetime.now().strftime('%Y-%m-%d'),
            case_number=vehicle.case_number,
            reporting_agency=vehicle.reporting_agency,
            priority=vehicle.priority,
            additional_info=vehicle.additional_info
        )
        
        success = security_system.database.add_stolen_vehicle(stolen_vehicle)
        
        if success:
            return {"status": "success", "message": "Stolen vehicle added successfully"}
        else:
            raise HTTPException(status_code=400, detail="Failed to add stolen vehicle")
            
    except Exception as e:
        logger.error(f"Add stolen vehicle failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/security/alerts")
async def get_recent_alerts(hours: int = 24):
    """Get recent security alerts"""
    global security_system
    
    if not security_system:
        raise HTTPException(status_code=503, detail="Security system not available")
    
    try:
        alerts = security_system.alert_manager.get_recent_alerts(hours)
        return {"alerts": alerts, "count": len(alerts)}
        
    except Exception as e:
        logger.error(f"Get alerts failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/security/statistics")
async def get_security_statistics():
    """Get security system statistics"""
    global security_system
    
    if not security_system:
        raise HTTPException(status_code=503, detail="Security system not available")
    
    try:
        dashboard_data = security_system.get_dashboard_data()
        return dashboard_data
        
    except Exception as e:
        logger.error(f"Get statistics failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Detection endpoints
@app.post("/detection/detect")
async def detect_vehicles(request: DetectionRequest):
    """Detect vehicles in image"""
    global detector
    
    if not detector:
        raise HTTPException(status_code=503, detail="Detector not available")
    
    try:
        # Load image
        if not os.path.exists(request.image_path):
            raise HTTPException(status_code=404, detail="Image file not found")
        
        image = cv2.imread(request.image_path)
        if image is None:
            raise HTTPException(status_code=400, detail="Invalid image file")
        
        # Update confidence threshold if provided
        if request.confidence_threshold:
            detector.conf_threshold = request.confidence_threshold
        
        # Detect vehicles
        detections = detector.detect_vehicles(image)
        
        return {
            "detections": detections,
            "image_path": request.image_path,
            "processing_time": detections.get("processing_time", 0)
        }
        
    except Exception as e:
        logger.error(f"Detection failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/detection/upload")
async def upload_and_detect(file: UploadFile = File(...)):
    """Upload image and detect vehicles"""
    global detector
    
    if not detector:
        raise HTTPException(status_code=503, detail="Detector not available")
    
    try:
        # Validate file type
        if not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="File must be an image")
        
        # Save uploaded file
        upload_dir = Path("temp/uploads")
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = upload_dir / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}"
        
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Load and process image
        image = cv2.imread(str(file_path))
        if image is None:
            raise HTTPException(status_code=400, detail="Invalid image file")
        
        # Detect vehicles
        detections = detector.detect_vehicles(image)
        
        # Clean up uploaded file
        os.remove(file_path)
        
        return {
            "detections": detections,
            "filename": file.filename,
            "processing_time": detections.get("processing_time", 0)
        }
        
    except Exception as e:
        logger.error(f"Upload and detect failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/detection/statistics")
async def get_detection_statistics():
    """Get detection system statistics"""
    global detector
    
    if not detector:
        raise HTTPException(status_code=503, detail="Detector not available")
    
    try:
        stats = detector.get_performance_stats()
        return {"statistics": stats}
        
    except Exception as e:
        logger.error(f"Get detection statistics failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Traffic control endpoints
@app.post("/control/traffic-light")
async def control_traffic_light(request: TrafficLightControl):
    """Control traffic light phase"""
    global simulation
    
    if not simulation:
        raise HTTPException(status_code=503, detail="Simulation not available")
    
    try:
        simulation.set_traffic_light_phase(
            request.traffic_light_id,
            request.phase,
            request.duration
        )
        
        return {
            "status": "success",
            "message": f"Traffic light {request.traffic_light_id} set to phase {request.phase}",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Traffic light control failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/control/emergency")
async def emergency_override(direction: str):
    """Emergency vehicle override"""
    global simulation
    
    if not simulation:
        raise HTTPException(status_code=503, detail="Simulation not available")
    
    try:
        # Add emergency vehicle to simulation
        route_map = {
            "north": "route_NS",
            "south": "route_SN", 
            "east": "route_EW",
            "west": "route_WE"
        }
        
        route = route_map.get(direction.lower())
        if not route:
            raise HTTPException(status_code=400, detail="Invalid direction")
        
        simulation.add_emergency_vehicle(route)
        
        return {
            "status": "success",
            "message": f"Emergency override activated for {direction} direction",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Emergency override failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/control/intersection-state")
async def get_intersection_state():
    """Get current intersection state"""
    global simulation
    
    if not simulation:
        raise HTTPException(status_code=503, detail="Simulation not available")
    
    try:
        state = simulation.get_intersection_state()
        return {"intersection_state": state}
        
    except Exception as e:
        logger.error(f"Get intersection state failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Simulation endpoints
@app.get("/simulation/metrics")
async def get_simulation_metrics():
    """Get simulation performance metrics"""
    global simulation
    
    if not simulation:
        raise HTTPException(status_code=503, detail="Simulation not available")
    
    try:
        metrics = simulation.get_performance_metrics()
        return {"metrics": metrics}
        
    except Exception as e:
        logger.error(f"Get simulation metrics failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/simulation/reset")
async def reset_simulation():
    """Reset traffic simulation"""
    global simulation
    
    if not simulation:
        raise HTTPException(status_code=503, detail="Simulation not available")
    
    try:
        simulation.close()
        simulation = SUMOTrafficSimulation(gui=False, simulation_time=3600)
        
        return {
            "status": "success",
            "message": "Simulation reset successfully",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Simulation reset failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Tracking endpoints
@app.get("/tracking/statistics")
async def get_tracking_statistics():
    """Get tracking system statistics"""
    global tracker
    
    if not tracker:
        raise HTTPException(status_code=503, detail="Tracker not available")
    
    try:
        stats = tracker.get_statistics()
        return {"statistics": stats}
        
    except Exception as e:
        logger.error(f"Get tracking statistics failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Background tasks
async def process_detection_task(image_path: str):
    """Background task for processing detection"""
    global detector, tracker, security_system
    
    try:
        # Load image
        image = cv2.imread(image_path)
        if image is None:
            logger.error(f"Failed to load image: {image_path}")
            return
        
        # Detect vehicles
        detections = detector.detect_vehicles(image, return_crops=True)
        
        # Track vehicles
        tracked_objects = tracker.update(detections['vehicles'])
        
        # Process each tracked vehicle for security check
        for obj in tracked_objects:
            # This would typically involve license plate recognition
            # For demo purposes, we'll simulate it
            pass
            
        logger.info(f"Processed {len(tracked_objects)} tracked vehicles")
        
    except Exception as e:
        logger.error(f"Background detection task failed: {e}")


@app.post("/process/background")
async def process_image_background(
    background_tasks: BackgroundTasks,
    image_path: str
):
    """Process image in background"""
    background_tasks.add_task(process_detection_task, image_path)
    
    return {
        "status": "accepted",
        "message": "Image processing started in background",
        "image_path": image_path
    }


# WebSocket endpoint for real-time updates (optional)
try:
    from fastapi import WebSocket, WebSocketDisconnect
    
    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        """WebSocket endpoint for real-time updates"""
        await websocket.accept()
        
        try:
            while True:
                # Send periodic updates
                if simulation:
                    state = simulation.get_intersection_state()
                    await websocket.send_json({
                        "type": "intersection_state",
                        "data": state,
                        "timestamp": datetime.now().isoformat()
                    })
                
                await asyncio.sleep(5)  # Send update every 5 seconds
                
        except WebSocketDisconnect:
            logger.info("WebSocket client disconnected")
        except Exception as e:
            logger.error(f"WebSocket error: {e}")

except ImportError:
    logger.warning("WebSocket support not available")


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8502,
        reload=True,
        log_level="info"
    )