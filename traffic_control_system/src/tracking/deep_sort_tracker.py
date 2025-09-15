"""
DeepSORT Multi-Object Tracking Module
Implements vehicle tracking with ID consistency and speed estimation
"""

import cv2
import numpy as np
from typing import List, Dict, Tuple, Optional
import logging
from collections import defaultdict, deque
from dataclasses import dataclass
from scipy.optimize import linear_sum_assignment
from scipy.spatial.distance import cdist
import math

logger = logging.getLogger(__name__)


@dataclass
class TrackState:
    """Track state representation"""
    TENTATIVE = 1
    CONFIRMED = 2
    DELETED = 3


@dataclass
class Detection:
    """Detection representation for tracking"""
    bbox: List[float]  # [x1, y1, x2, y2]
    confidence: float
    feature: Optional[np.ndarray] = None
    class_id: int = 0
    

class KalmanFilter:
    """
    Kalman Filter for vehicle state estimation
    State: [x, y, vx, vy, w, h, vw, vh] where (x,y) is center, (w,h) is size, v is velocity
    """
    
    def __init__(self):
        # State transition matrix (8x8)
        self.F = np.eye(8)
        self.F[0, 2] = 1  # x += vx
        self.F[1, 3] = 1  # y += vy
        self.F[4, 6] = 1  # w += vw
        self.F[5, 7] = 1  # h += vh
        
        # Measurement matrix (4x8) - we observe [x, y, w, h]
        self.H = np.zeros((4, 8))
        self.H[0, 0] = 1  # observe x
        self.H[1, 1] = 1  # observe y
        self.H[2, 4] = 1  # observe w
        self.H[3, 5] = 1  # observe h
        
        # Process noise covariance
        self.Q = np.eye(8) * 0.01
        self.Q[2:4, 2:4] *= 1000  # velocity uncertainty
        self.Q[6:8, 6:8] *= 1000  # size velocity uncertainty
        
        # Measurement noise covariance
        self.R = np.eye(4) * 10
        
        # Initial state covariance
        self.P = np.eye(8) * 1000
        self.P[2:4, 2:4] *= 10000  # high velocity uncertainty
        self.P[6:8, 6:8] *= 10000  # high size velocity uncertainty
    
    def predict(self, x: np.ndarray, P: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Predict next state"""
        x_pred = self.F @ x
        P_pred = self.F @ P @ self.F.T + self.Q
        return x_pred, P_pred
    
    def update(self, x: np.ndarray, P: np.ndarray, z: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Update state with measurement"""
        y = z - self.H @ x  # Innovation
        S = self.H @ P @ self.H.T + self.R  # Innovation covariance
        K = P @ self.H.T @ np.linalg.inv(S)  # Kalman gain
        
        x_updated = x + K @ y
        P_updated = (np.eye(8) - K @ self.H) @ P
        
        return x_updated, P_updated
    
    def gating_distance(self, x: np.ndarray, P: np.ndarray, z: np.ndarray) -> float:
        """Calculate Mahalanobis distance for gating"""
        y = z - self.H @ x
        S = self.H @ P @ self.H.T + self.R
        return y.T @ np.linalg.inv(S) @ y


class Track:
    """Individual vehicle track"""
    
    def __init__(self, detection: Detection, track_id: int, max_age: int = 30):
        self.track_id = track_id
        self.max_age = max_age
        self.time_since_update = 0
        self.hits = 1
        self.hit_streak = 1
        self.age = 1
        self.state = TrackState.TENTATIVE
        
        # Initialize Kalman filter
        self.kf = KalmanFilter()
        
        # Convert detection to state
        bbox = detection.bbox
        x = (bbox[0] + bbox[2]) / 2
        y = (bbox[1] + bbox[3]) / 2
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        
        # Initial state [x, y, vx, vy, w, h, vw, vh]
        self.x = np.array([x, y, 0, 0, w, h, 0, 0]).astype(float)
        self.P = self.kf.P.copy()
        
        # Track history for speed calculation
        self.history = deque(maxlen=10)
        self.history.append({
            'position': (x, y),
            'timestamp': cv2.getTickCount() / cv2.getTickFrequency(),
            'bbox': bbox
        })
        
        # Vehicle properties
        self.vehicle_class = getattr(detection, 'class_id', 0)
        self.confidence_history = deque([detection.confidence], maxlen=5)
        
        # Speed estimation
        self.speed_kmh = 0.0
        self.direction = 0.0  # angle in degrees
        
    def predict(self):
        """Predict next state"""
        self.x, self.P = self.kf.predict(self.x, self.P)
        self.age += 1
        self.time_since_update += 1
    
    def update(self, detection: Detection):
        """Update track with new detection"""
        # Convert detection to measurement
        bbox = detection.bbox
        x = (bbox[0] + bbox[2]) / 2
        y = (bbox[1] + bbox[3]) / 2
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        
        z = np.array([x, y, w, h])
        
        # Update Kalman filter
        self.x, self.P = self.kf.update(self.x, self.P, z)
        
        # Update track properties
        self.time_since_update = 0
        self.hits += 1
        self.hit_streak += 1
        
        # Update confidence
        self.confidence_history.append(detection.confidence)
        
        # Update history for speed calculation
        current_time = cv2.getTickCount() / cv2.getTickFrequency()
        self.history.append({
            'position': (x, y),
            'timestamp': current_time,
            'bbox': bbox
        })
        
        # Calculate speed
        self._calculate_speed()
        
        # Update track state
        if self.state == TrackState.TENTATIVE and self.hits >= 3:
            self.state = TrackState.CONFIRMED
    
    def _calculate_speed(self, pixels_per_meter: float = 10.0):
        """Calculate vehicle speed in km/h"""
        if len(self.history) < 2:
            return
        
        # Use last two positions for speed calculation
        current = self.history[-1]
        previous = self.history[-2]
        
        # Calculate distance in pixels
        dx = current['position'][0] - previous['position'][0]
        dy = current['position'][1] - previous['position'][1]
        distance_pixels = math.sqrt(dx*dx + dy*dy)
        
        # Convert to meters (approximate)
        distance_meters = distance_pixels / pixels_per_meter
        
        # Calculate time difference
        dt = current['timestamp'] - previous['timestamp']
        
        if dt > 0:
            # Speed in m/s
            speed_ms = distance_meters / dt
            
            # Convert to km/h
            self.speed_kmh = speed_ms * 3.6
            
            # Calculate direction
            self.direction = math.degrees(math.atan2(dy, dx))
    
    def get_state(self) -> Dict:
        """Get current track state"""
        # Convert state back to bbox
        x, y, _, _, w, h, _, _ = self.x
        bbox = [x - w/2, y - h/2, x + w/2, y + h/2]
        
        return {
            'track_id': self.track_id,
            'bbox': bbox,
            'center': (x, y),
            'speed_kmh': self.speed_kmh,
            'direction': self.direction,
            'confidence': np.mean(self.confidence_history),
            'hits': self.hits,
            'age': self.age,
            'state': self.state,
            'vehicle_class': self.vehicle_class
        }
    
    def mark_missed(self):
        """Mark track as missed"""
        self.time_since_update += 1
        self.hit_streak = 0
        
        if self.time_since_update > self.max_age:
            self.state = TrackState.DELETED
    
    def is_confirmed(self) -> bool:
        """Check if track is confirmed"""
        return self.state == TrackState.CONFIRMED
    
    def is_deleted(self) -> bool:
        """Check if track should be deleted"""
        return self.state == TrackState.DELETED


class DeepSORTTracker:
    """
    DeepSORT Multi-Object Tracker
    
    Features:
    - Kalman filter for motion prediction
    - Hungarian algorithm for assignment
    - Track lifecycle management
    - Speed estimation
    - ID consistency
    """
    
    def __init__(
        self,
        max_age: int = 30,
        min_hits: int = 3,
        iou_threshold: float = 0.3,
        max_distance: float = 0.7
    ):
        """
        Initialize DeepSORT tracker
        
        Args:
            max_age: Maximum number of frames to keep alive a track without detections
            min_hits: Minimum number of hits to confirm a track
            iou_threshold: IoU threshold for association
            max_distance: Maximum distance for association
        """
        self.max_age = max_age
        self.min_hits = min_hits
        self.iou_threshold = iou_threshold
        self.max_distance = max_distance
        
        self.tracks = []
        self.next_id = 1
        self.frame_count = 0
        
        # Statistics
        self.stats = {
            'total_tracks': 0,
            'active_tracks': 0,
            'confirmed_tracks': 0,
            'deleted_tracks': 0,
            'avg_track_length': 0.0
        }
        
        logger.info("DeepSORT tracker initialized")
    
    def update(self, detections: List[Dict]) -> List[Dict]:
        """
        Update tracker with new detections
        
        Args:
            detections: List of detection dictionaries from YOLO
            
        Returns:
            List of tracked objects with IDs
        """
        self.frame_count += 1
        
        # Convert detections to Detection objects
        detection_objects = []
        for det in detections:
            detection_objects.append(Detection(
                bbox=det['bbox'],
                confidence=det['confidence'],
                class_id=det.get('class_id', 0)
            ))
        
        # Predict all tracks
        for track in self.tracks:
            track.predict()
        
        # Associate detections to tracks
        matched_tracks, unmatched_detections, unmatched_tracks = self._associate_detections_to_tracks(
            detection_objects, self.tracks
        )
        
        # Update matched tracks
        for track_idx, det_idx in matched_tracks:
            self.tracks[track_idx].update(detection_objects[det_idx])
        
        # Create new tracks for unmatched detections
        for det_idx in unmatched_detections:
            self._initiate_track(detection_objects[det_idx])
        
        # Mark unmatched tracks as missed
        for track_idx in unmatched_tracks:
            self.tracks[track_idx].mark_missed()
        
        # Remove deleted tracks
        self.tracks = [track for track in self.tracks if not track.is_deleted()]
        
        # Get current track states
        tracked_objects = []
        for track in self.tracks:
            if track.is_confirmed():
                tracked_objects.append(track.get_state())
        
        # Update statistics
        self._update_statistics()
        
        return tracked_objects
    
    def _associate_detections_to_tracks(
        self, 
        detections: List[Detection], 
        tracks: List[Track]
    ) -> Tuple[List[Tuple[int, int]], List[int], List[int]]:
        """
        Associate detections to tracks using Hungarian algorithm
        
        Returns:
            matched_tracks: List of (track_idx, detection_idx) pairs
            unmatched_detections: List of detection indices
            unmatched_tracks: List of track indices
        """
        if not tracks or not detections:
            return [], list(range(len(detections))), list(range(len(tracks)))
        
        # Calculate cost matrix (IoU + appearance)
        cost_matrix = np.zeros((len(tracks), len(detections)))
        
        for t, track in enumerate(tracks):
            track_bbox = track.get_state()['bbox']
            
            for d, detection in enumerate(detections):
                # Calculate IoU
                iou = self._calculate_iou(track_bbox, detection.bbox)
                
                # Cost is 1 - IoU (lower is better)
                cost_matrix[t, d] = 1 - iou
        
        # Apply Hungarian algorithm
        track_indices, detection_indices = linear_sum_assignment(cost_matrix)
        
        # Filter matches based on threshold
        matched_tracks = []
        unmatched_detections = list(range(len(detections)))
        unmatched_tracks = list(range(len(tracks)))
        
        for t, d in zip(track_indices, detection_indices):
            if cost_matrix[t, d] < (1 - self.iou_threshold):
                matched_tracks.append((t, d))
                unmatched_detections.remove(d)
                unmatched_tracks.remove(t)
        
        return matched_tracks, unmatched_detections, unmatched_tracks
    
    def _calculate_iou(self, bbox1: List[float], bbox2: List[float]) -> float:
        """Calculate Intersection over Union (IoU)"""
        x1_1, y1_1, x2_1, y2_1 = bbox1
        x1_2, y1_2, x2_2, y2_2 = bbox2
        
        # Calculate intersection
        x1_i = max(x1_1, x1_2)
        y1_i = max(y1_1, y1_2)
        x2_i = min(x2_1, x2_2)
        y2_i = min(y2_1, y2_2)
        
        if x2_i <= x1_i or y2_i <= y1_i:
            return 0.0
        
        intersection = (x2_i - x1_i) * (y2_i - y1_i)
        
        # Calculate areas
        area1 = (x2_1 - x1_1) * (y2_1 - y1_1)
        area2 = (x2_2 - x1_2) * (y2_2 - y1_2)
        
        # Calculate union
        union = area1 + area2 - intersection
        
        return intersection / union if union > 0 else 0.0
    
    def _initiate_track(self, detection: Detection):
        """Create new track from detection"""
        new_track = Track(detection, self.next_id, self.max_age)
        self.tracks.append(new_track)
        self.next_id += 1
        self.stats['total_tracks'] += 1
    
    def _update_statistics(self):
        """Update tracking statistics"""
        self.stats['active_tracks'] = len(self.tracks)
        self.stats['confirmed_tracks'] = sum(1 for track in self.tracks if track.is_confirmed())
        
        # Calculate average track length
        if self.tracks:
            total_length = sum(track.hits for track in self.tracks)
            self.stats['avg_track_length'] = total_length / len(self.tracks)
    
    def get_statistics(self) -> Dict:
        """Get tracking statistics"""
        return self.stats.copy()
    
    def visualize_tracks(
        self, 
        frame: np.ndarray, 
        tracked_objects: List[Dict],
        show_trails: bool = True,
        show_speed: bool = True
    ) -> np.ndarray:
        """
        Visualize tracking results
        
        Args:
            frame: Input frame
            tracked_objects: Tracking results
            show_trails: Whether to show track trails
            show_speed: Whether to show speed information
            
        Returns:
            Annotated frame
        """
        annotated_frame = frame.copy()
        
        # Color map for different track IDs
        colors = [
            (255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0),
            (255, 0, 255), (0, 255, 255), (128, 0, 128), (255, 165, 0),
            (0, 128, 128), (128, 128, 0)
        ]
        
        for obj in tracked_objects:
            track_id = obj['track_id']
            bbox = obj['bbox']
            center = obj['center']
            speed = obj['speed_kmh']
            
            # Get color for this track
            color = colors[track_id % len(colors)]
            
            # Draw bounding box
            x1, y1, x2, y2 = [int(coord) for coord in bbox]
            cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 2)
            
            # Draw center point
            center_x, center_y = [int(coord) for coord in center]
            cv2.circle(annotated_frame, (center_x, center_y), 5, color, -1)
            
            # Add track ID
            label = f"ID: {track_id}"
            if show_speed:
                label += f" | {speed:.1f} km/h"
            
            # Calculate text position
            (text_width, text_height), baseline = cv2.getTextSize(
                label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2
            )
            
            # Draw text background
            cv2.rectangle(
                annotated_frame,
                (x1, y1 - text_height - baseline - 10),
                (x1 + text_width + 10, y1),
                color,
                -1
            )
            
            # Draw text
            cv2.putText(
                annotated_frame,
                label,
                (x1 + 5, y1 - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 255),
                2
            )
            
            # Draw speed vector
            if show_speed and speed > 1.0:  # Only show if moving
                direction = obj.get('direction', 0)
                vector_length = min(50, int(speed))  # Scale vector by speed
                
                end_x = center_x + int(vector_length * math.cos(math.radians(direction)))
                end_y = center_y + int(vector_length * math.sin(math.radians(direction)))
                
                cv2.arrowedLine(
                    annotated_frame,
                    (center_x, center_y),
                    (end_x, end_y),
                    color,
                    3
                )
        
        # Add tracking statistics
        stats_text = f"Active Tracks: {len(tracked_objects)} | Frame: {self.frame_count}"
        cv2.putText(
            annotated_frame,
            stats_text,
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2
        )
        
        return annotated_frame


def main():
    """Test the DeepSORT tracker"""
    # Initialize tracker
    tracker = DeepSORTTracker(
        max_age=30,
        min_hits=3,
        iou_threshold=0.3
    )
    
    # Test with webcam or video
    cap = cv2.VideoCapture(0)
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # Simulate detections (in real implementation, these come from YOLO)
        # For testing, create some dummy detections
        height, width = frame.shape[:2]
        dummy_detections = [
            {
                'bbox': [100, 100, 200, 180],
                'confidence': 0.9,
                'class_id': 0,
                'class': 'car'
            },
            {
                'bbox': [300, 150, 400, 230],
                'confidence': 0.85,
                'class_id': 0,
                'class': 'car'
            }
        ]
        
        # Update tracker
        tracked_objects = tracker.update(dummy_detections)
        
        # Visualize results
        annotated_frame = tracker.visualize_tracks(
            frame, 
            tracked_objects,
            show_speed=True
        )
        
        # Display frame
        cv2.imshow('DeepSORT Tracking', annotated_frame)
        
        # Print statistics every 30 frames
        if tracker.frame_count % 30 == 0:
            stats = tracker.get_statistics()
            print(f"Tracking stats: {stats}")
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()