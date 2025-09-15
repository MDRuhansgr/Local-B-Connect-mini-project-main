"""
Main Traffic Control System Integration
Orchestrates all system components for end-to-end traffic management
"""

import cv2
import numpy as np
import logging
import time
import threading
import queue
from pathlib import Path
from typing import Dict, List, Optional, Any
import json
from datetime import datetime
import argparse
import signal
import sys

# Import system components
from detection.yolo_detector import YOLOVehicleDetector
from detection.license_plate_ocr import LicensePlateOCR
from tracking.deep_sort_tracker import DeepSORTTracker
from control.drl_traffic_agent import PPOTrafficAgent, TrafficEnvironment
from simulation.sumo_environment import SUMOTrafficSimulation
from security.security_system import SecuritySystem
from utils.config_manager import ConfigManager
from utils.logger import setup_logging

logger = logging.getLogger(__name__)


class TrafficControlSystem:
    """
    Main Traffic Control System Class
    
    Integrates all components for comprehensive traffic management:
    - Real-time vehicle detection and tracking
    - License plate recognition and security checks
    - AI-powered traffic signal control
    - Performance monitoring and analytics
    """
    
    def __init__(self, config_path: str = "config/system_config.yaml"):
        """
        Initialize Traffic Control System
        
        Args:
            config_path: Path to system configuration file
        """
        self.config = ConfigManager(config_path)
        self.is_running = False
        self.performance_metrics = {
            'total_vehicles_detected': 0,
            'total_vehicles_tracked': 0,
            'security_alerts_generated': 0,
            'avg_processing_time': 0.0,
            'system_uptime': 0.0
        }
        
        # Initialize system components
        self._initialize_components()
        
        # Threading components
        self.frame_queue = queue.Queue(maxsize=10)
        self.result_queue = queue.Queue()
        self.processing_threads = []
        
        # System state
        self.current_intersection_state = {}
        self.last_control_action = None
        self.start_time = time.time()
        
        logger.info("Traffic Control System initialized")
    
    def _initialize_components(self):
        """Initialize all system components"""
        try:
            # Vehicle detection
            self.detector = YOLOVehicleDetector(
                model_path=self.config.get('detection.model_path', 'yolov8n.pt'),
                conf_threshold=self.config.get('detection.confidence_threshold', 0.5),
                device=self.config.get('detection.device', 'auto')
            )
            logger.info("Vehicle detector initialized")
            
            # License plate recognition
            self.ocr_system = LicensePlateOCR(
                languages=self.config.get('ocr.languages', ['en']),
                confidence_threshold=self.config.get('ocr.confidence_threshold', 0.6)
            )
            logger.info("OCR system initialized")
            
            # Vehicle tracking
            self.tracker = DeepSORTTracker(
                max_age=self.config.get('tracking.max_age', 30),
                min_hits=self.config.get('tracking.min_hits', 3),
                iou_threshold=self.config.get('tracking.iou_threshold', 0.3)
            )
            logger.info("Vehicle tracker initialized")
            
            # Security system
            self.security_system = SecuritySystem(
                db_path=self.config.get('security.db_path', 'data/security_db.sqlite'),
                notification_config=self.config.get('security.notifications', {})
            )
            logger.info("Security system initialized")
            
            # Traffic simulation
            self.simulation = SUMOTrafficSimulation(
                gui=self.config.get('simulation.gui', False),
                simulation_time=self.config.get('simulation.duration', 3600)
            )
            logger.info("Traffic simulation initialized")
            
            # DRL traffic control agent
            self.traffic_env = TrafficEnvironment(
                num_lanes=self.config.get('control.num_lanes', 8),
                reward_weights=self.config.get('control.reward_weights', {})
            )
            
            self.control_agent = PPOTrafficAgent(
                env=self.traffic_env,
                learning_rate=self.config.get('control.learning_rate', 3e-4)
            )
            
            # Load pre-trained model if available
            model_path = self.config.get('control.model_path')
            if model_path and Path(model_path).exists():
                self.control_agent.load_model(model_path)
                logger.info(f"Loaded pre-trained control model: {model_path}")
            
            logger.info("DRL control agent initialized")
            
        except Exception as e:
            logger.error(f"Component initialization failed: {e}")
            raise
    
    def start_video_processing(self, video_source: str = "0"):
        """
        Start video processing pipeline
        
        Args:
            video_source: Video source (camera index, video file, or RTSP stream)
        """
        logger.info(f"Starting video processing from source: {video_source}")
        
        # Initialize video capture
        if video_source.isdigit():
            cap = cv2.VideoCapture(int(video_source))
        else:
            cap = cv2.VideoCapture(video_source)
        
        if not cap.isOpened():
            logger.error(f"Failed to open video source: {video_source}")
            return
        
        # Set video properties
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.get('video.width', 1920))
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.get('video.height', 1080))
        cap.set(cv2.CAP_PROP_FPS, self.config.get('video.fps', 30))
        
        # Start processing threads
        self._start_processing_threads()
        
        self.is_running = True
        frame_count = 0
        
        try:
            while self.is_running:
                ret, frame = cap.read()
                if not ret:
                    logger.warning("Failed to read frame")
                    break
                
                # Add frame to processing queue
                try:
                    self.frame_queue.put((frame_count, frame), timeout=0.1)
                    frame_count += 1
                except queue.Full:
                    logger.warning("Frame queue full, dropping frame")
                
                # Process results
                self._process_results()
                
                # Control traffic signals
                if frame_count % 30 == 0:  # Every 30 frames (~1 second at 30fps)
                    self._update_traffic_control()
                
                # Display frame (optional)
                if self.config.get('video.display', False):
                    self._display_frame(frame)
                
                # Performance monitoring
                if frame_count % 300 == 0:  # Every 10 seconds
                    self._log_performance_metrics()
                
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        finally:
            self.stop()
            cap.release()
            cv2.destroyAllWindows()
    
    def _start_processing_threads(self):
        """Start background processing threads"""
        num_threads = self.config.get('processing.num_threads', 2)
        
        for i in range(num_threads):
            thread = threading.Thread(
                target=self._processing_worker,
                name=f"ProcessingThread-{i}",
                daemon=True
            )
            thread.start()
            self.processing_threads.append(thread)
        
        logger.info(f"Started {num_threads} processing threads")
    
    def _processing_worker(self):
        """Background worker for frame processing"""
        while self.is_running:
            try:
                # Get frame from queue
                frame_id, frame = self.frame_queue.get(timeout=1.0)
                
                # Process frame
                result = self._process_frame(frame_id, frame)
                
                # Put result in result queue
                self.result_queue.put(result)
                
                self.frame_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Processing worker error: {e}")
    
    def _process_frame(self, frame_id: int, frame: np.ndarray) -> Dict:
        """
        Process individual frame through the complete pipeline
        
        Args:
            frame_id: Frame identifier
            frame: Video frame
            
        Returns:
            Processing results
        """
        start_time = time.time()
        
        try:
            # Step 1: Vehicle Detection
            detections = self.detector.detect_vehicles(frame, return_crops=True)
            
            # Step 2: License Plate Recognition
            enhanced_detections = self.ocr_system.process_vehicle_detection(
                frame, detections['vehicles']
            )
            
            # Step 3: Vehicle Tracking
            tracked_objects = self.tracker.update(enhanced_detections)
            
            # Step 4: Security Checks
            security_results = []
            for obj in tracked_objects:
                if obj.get('license_plate', {}).get('detected', False):
                    lp_text = obj['license_plate']['text']
                    lp_confidence = obj['license_plate']['confidence']
                    
                    # Check against stolen vehicle database
                    security_result = self.security_system.check_vehicle(
                        license_plate=lp_text,
                        confidence=lp_confidence,
                        location="Main Intersection",
                        camera_id="CAM001"
                    )
                    
                    security_results.append(security_result)
                    
                    if security_result['is_stolen']:
                        self.performance_metrics['security_alerts_generated'] += 1
            
            # Step 5: Update intersection state
            self._update_intersection_state(tracked_objects)
            
            processing_time = time.time() - start_time
            
            # Update performance metrics
            self.performance_metrics['total_vehicles_detected'] += len(detections['vehicles'])
            self.performance_metrics['total_vehicles_tracked'] += len(tracked_objects)
            
            # Update average processing time
            self.performance_metrics['avg_processing_time'] = (
                self.performance_metrics['avg_processing_time'] * 0.9 + 
                processing_time * 0.1
            )
            
            return {
                'frame_id': frame_id,
                'timestamp': datetime.now().isoformat(),
                'detections': detections,
                'tracked_objects': tracked_objects,
                'security_results': security_results,
                'processing_time': processing_time,
                'intersection_state': self.current_intersection_state.copy()
            }
            
        except Exception as e:
            logger.error(f"Frame processing failed: {e}")
            return {
                'frame_id': frame_id,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def _update_intersection_state(self, tracked_objects: List[Dict]):
        """Update current intersection state based on tracked objects"""
        # Calculate lane densities and queue lengths
        lane_densities = np.zeros(8)  # 8 lanes
        queue_lengths = np.zeros(8)
        waiting_times = np.zeros(8)
        
        # Simple lane assignment based on vehicle position
        # In real implementation, this would use lane detection
        for obj in tracked_objects:
            center_x, center_y = obj['center']
            
            # Determine lane based on position (simplified)
            lane_idx = int((center_x / 1920) * 8) % 8  # Assume 1920px width
            
            lane_densities[lane_idx] += 1
            
            # Estimate waiting time based on speed
            speed = obj.get('speed_kmh', 0)
            if speed < 5:  # Slow or stationary
                waiting_times[lane_idx] += 10  # Simplified waiting time
        
        # Normalize densities
        max_vehicles_per_lane = 20  # Assumed capacity
        lane_densities = np.clip(lane_densities / max_vehicles_per_lane, 0, 1)
        
        self.current_intersection_state = {
            'lane_densities': lane_densities.tolist(),
            'queue_lengths': queue_lengths.tolist(),
            'waiting_times': waiting_times.tolist(),
            'total_vehicles': len(tracked_objects),
            'timestamp': datetime.now().isoformat()
        }
    
    def _update_traffic_control(self):
        """Update traffic signal control using DRL agent"""
        try:
            if not self.current_intersection_state:
                return
            
            # Prepare state for DRL agent
            state_vector = np.array(
                self.current_intersection_state['lane_densities'] +
                self.current_intersection_state['queue_lengths'] +
                self.current_intersection_state['waiting_times'] +
                [0.0] * 8  # Additional features (phase info, time, etc.)
            ).astype(np.float32)
            
            # Get action from DRL agent
            action, _ = self.control_agent.predict(state_vector, deterministic=True)
            
            # Decode action to traffic light control
            phase_selection = int(action[0] * 4)  # 4 phases
            duration = 10 + action[1] * 50  # 10-60 seconds
            
            # Apply to simulation
            tl_ids = list(self.simulation.traffic_lights.keys())
            if tl_ids:
                self.simulation.set_traffic_light_phase(tl_ids[0], phase_selection, duration)
                
                self.last_control_action = {
                    'phase': phase_selection,
                    'duration': duration,
                    'timestamp': datetime.now().isoformat()
                }
                
                logger.debug(f"Applied traffic control: Phase {phase_selection}, Duration {duration}s")
            
        except Exception as e:
            logger.error(f"Traffic control update failed: {e}")
    
    def _process_results(self):
        """Process results from processing threads"""
        while not self.result_queue.empty():
            try:
                result = self.result_queue.get_nowait()
                
                # Log significant events
                if result.get('security_results'):
                    for security_result in result['security_results']:
                        if security_result['is_stolen']:
                            logger.warning(
                                f"SECURITY ALERT: Stolen vehicle {security_result['license_plate']} "
                                f"detected (Alert ID: {security_result.get('alert_id')})"
                            )
                
                # Store result for analysis (optional)
                # self._store_result(result)
                
            except queue.Empty:
                break
            except Exception as e:
                logger.error(f"Result processing failed: {e}")
    
    def _display_frame(self, frame: np.ndarray):
        """Display processed frame (for debugging)"""
        # This would typically show the annotated frame
        # For now, just display the original frame
        cv2.imshow('Traffic Control System', frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            self.stop()
    
    def _log_performance_metrics(self):
        """Log current performance metrics"""
        self.performance_metrics['system_uptime'] = time.time() - self.start_time
        
        logger.info(f"Performance Metrics: {json.dumps(self.performance_metrics, indent=2)}")
        
        # Log to file for analysis
        metrics_file = Path("logs/performance_metrics.json")
        metrics_file.parent.mkdir(exist_ok=True)
        
        with open(metrics_file, 'a') as f:
            f.write(json.dumps({
                'timestamp': datetime.now().isoformat(),
                'metrics': self.performance_metrics
            }) + '\n')
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get current system status"""
        return {
            'is_running': self.is_running,
            'uptime': time.time() - self.start_time,
            'performance_metrics': self.performance_metrics,
            'intersection_state': self.current_intersection_state,
            'last_control_action': self.last_control_action,
            'component_status': {
                'detector': self.detector is not None,
                'tracker': self.tracker is not None,
                'ocr_system': self.ocr_system is not None,
                'security_system': self.security_system is not None,
                'simulation': self.simulation is not None and self.simulation.is_running,
                'control_agent': self.control_agent is not None
            }
        }
    
    def train_drl_agent(self, total_timesteps: int = 100000):
        """Train the DRL traffic control agent"""
        logger.info(f"Starting DRL agent training for {total_timesteps} timesteps")
        
        try:
            self.control_agent.train(total_timesteps=total_timesteps)
            logger.info("DRL agent training completed")
        except Exception as e:
            logger.error(f"DRL training failed: {e}")
    
    def stop(self):
        """Stop the traffic control system"""
        logger.info("Stopping Traffic Control System...")
        
        self.is_running = False
        
        # Wait for processing threads to finish
        for thread in self.processing_threads:
            thread.join(timeout=5.0)
        
        # Close system components
        if hasattr(self, 'simulation'):
            self.simulation.close()
        
        logger.info("Traffic Control System stopped")
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.stop()


def signal_handler(signum, frame):
    """Handle system signals for graceful shutdown"""
    logger.info(f"Received signal {signum}")
    sys.exit(0)


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="AI Traffic Control System")
    parser.add_argument("--config", default="config/system_config.yaml", help="Configuration file path")
    parser.add_argument("--video-source", default="0", help="Video source (camera index or file path)")
    parser.add_argument("--train", action="store_true", help="Train DRL agent")
    parser.add_argument("--train-timesteps", type=int, default=100000, help="Training timesteps")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(level=args.log_level)
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("Starting AI Traffic Control System")
    
    try:
        with TrafficControlSystem(args.config) as system:
            
            if args.train:
                # Training mode
                system.train_drl_agent(args.train_timesteps)
            else:
                # Normal operation mode
                system.start_video_processing(args.video_source)
                
    except Exception as e:
        logger.error(f"System failed: {e}")
        sys.exit(1)
    
    logger.info("AI Traffic Control System shutdown complete")


if __name__ == "__main__":
    main()