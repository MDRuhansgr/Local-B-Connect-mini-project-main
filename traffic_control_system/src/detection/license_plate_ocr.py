"""
EasyOCR-based License Plate Recognition Module
Implements license plate detection and text recognition for security features
"""

import cv2
import numpy as np
import easyocr
import re
from typing import List, Dict, Tuple, Optional
import logging
from pathlib import Path
import sqlite3
from datetime import datetime

logger = logging.getLogger(__name__)


class LicensePlateOCR:
    """
    EasyOCR License Plate Recognition System
    
    Features:
    - Multi-language support
    - Fuzzy matching for partial reads
    - Integration with stolen vehicle database
    - Real-time processing capability
    """
    
    def __init__(
        self,
        languages: List[str] = ['en'],
        gpu: bool = True,
        confidence_threshold: float = 0.6,
        db_path: str = "data/security_db.sqlite"
    ):
        """
        Initialize License Plate OCR system
        
        Args:
            languages: List of languages for OCR ('en', 'hi', etc.)
            gpu: Whether to use GPU acceleration
            confidence_threshold: Minimum confidence for text recognition
            db_path: Path to security database
        """
        self.confidence_threshold = confidence_threshold
        self.db_path = db_path
        
        # Initialize EasyOCR reader
        try:
            self.reader = easyocr.Reader(languages, gpu=gpu)
            logger.info(f"EasyOCR initialized with languages: {languages}")
        except Exception as e:
            logger.error(f"Failed to initialize EasyOCR: {e}")
            self.reader = None
        
        # License plate patterns for different regions
        self.plate_patterns = {
            'indian_new': r'^[A-Z]{2}[0-9]{2}[A-Z]{1,2}[0-9]{4}$',  # KA01AB1234
            'indian_old': r'^[A-Z]{2}[0-9]{2}[A-Z]{1,2}[0-9]{1,4}$', # KA01A123
            'us': r'^[A-Z0-9]{2,8}$',  # ABC1234
            'generic': r'^[A-Z0-9]{4,10}$'  # General pattern
        }
        
        # Initialize security database
        self._init_security_db()
        
        # Statistics tracking
        self.stats = {
            'total_detections': 0,
            'successful_reads': 0,
            'security_alerts': 0,
            'processing_times': []
        }
    
    def _init_security_db(self):
        """Initialize security database for stolen vehicles"""
        try:
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create tables
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS stolen_vehicles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    license_plate TEXT UNIQUE NOT NULL,
                    vehicle_type TEXT,
                    color TEXT,
                    make TEXT,
                    model TEXT,
                    reported_date TEXT,
                    status TEXT DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS security_alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    license_plate TEXT NOT NULL,
                    detection_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    confidence REAL,
                    location TEXT,
                    image_path TEXT,
                    status TEXT DEFAULT 'pending'
                )
            ''')
            
            # Insert sample stolen vehicle data for testing
            sample_data = [
                ('KA01AB1234', 'car', 'red', 'Toyota', 'Camry', '2024-01-15'),
                ('MH02CD5678', 'motorcycle', 'black', 'Honda', 'CBR', '2024-02-10'),
                ('DL03EF9012', 'truck', 'white', 'Tata', 'LPT', '2024-01-20'),
                ('TN04GH3456', 'car', 'blue', 'Hyundai', 'i20', '2024-02-05'),
                ('UP05IJ7890', 'bus', 'yellow', 'Ashok', 'Leyland', '2024-01-30')
            ]
            
            cursor.executemany('''
                INSERT OR IGNORE INTO stolen_vehicles 
                (license_plate, vehicle_type, color, make, model, reported_date)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', sample_data)
            
            conn.commit()
            conn.close()
            
            logger.info("Security database initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize security database: {e}")
    
    def preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """
        Preprocess image for better OCR results
        
        Args:
            image: Input image (license plate crop)
            
        Returns:
            Preprocessed image
        """
        # Convert to grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        # Resize if too small
        height, width = gray.shape
        if width < 100:
            scale = 100 / width
            new_width = int(width * scale)
            new_height = int(height * scale)
            gray = cv2.resize(gray, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
        
        # Apply CLAHE for better contrast
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        
        # Gaussian blur to reduce noise
        blurred = cv2.GaussianBlur(enhanced, (3, 3), 0)
        
        # Adaptive thresholding
        thresh = cv2.adaptiveThreshold(
            blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )
        
        # Morphological operations to clean up
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        processed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        
        return processed
    
    def detect_license_plates(self, image: np.ndarray) -> List[Dict]:
        """
        Detect license plate regions in image
        
        Args:
            image: Input image
            
        Returns:
            List of detected license plate regions
        """
        plates = []
        
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Use Haar cascade or contour detection for plate detection
        # For simplicity, we'll use contour-based detection
        
        # Edge detection
        edges = cv2.Canny(gray, 50, 150)
        
        # Find contours
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for contour in contours:
            # Calculate contour properties
            area = cv2.contourArea(contour)
            if area < 1000:  # Filter small contours
                continue
            
            # Get bounding rectangle
            x, y, w, h = cv2.boundingRect(contour)
            
            # Check aspect ratio (license plates are typically rectangular)
            aspect_ratio = w / h
            if 2.0 <= aspect_ratio <= 5.0:  # Typical license plate aspect ratio
                # Extract region of interest
                roi = image[y:y+h, x:x+w]
                
                plates.append({
                    'bbox': [x, y, x+w, y+h],
                    'roi': roi,
                    'area': area,
                    'aspect_ratio': aspect_ratio
                })
        
        # Sort by area (largest first)
        plates.sort(key=lambda x: x['area'], reverse=True)
        
        return plates
    
    def read_license_plate(self, plate_image: np.ndarray) -> Dict:
        """
        Read text from license plate image
        
        Args:
            plate_image: Cropped license plate image
            
        Returns:
            OCR results with text and confidence
        """
        start_time = cv2.getTickCount()
        
        if self.reader is None:
            return {'text': '', 'confidence': 0.0, 'processing_time': 0.0}
        
        try:
            # Preprocess image
            processed_image = self.preprocess_image(plate_image)
            
            # Run OCR
            results = self.reader.readtext(processed_image)
            
            # Process results
            best_result = {'text': '', 'confidence': 0.0}
            
            for (bbox, text, confidence) in results:
                # Clean up text
                cleaned_text = self._clean_text(text)
                
                # Check if it matches license plate pattern
                if self._validate_license_plate(cleaned_text) and confidence > best_result['confidence']:
                    best_result = {
                        'text': cleaned_text,
                        'confidence': confidence,
                        'bbox': bbox
                    }
            
            # Calculate processing time
            processing_time = (cv2.getTickCount() - start_time) / cv2.getTickFrequency()
            best_result['processing_time'] = processing_time
            
            # Update statistics
            self.stats['total_detections'] += 1
            if best_result['confidence'] > self.confidence_threshold:
                self.stats['successful_reads'] += 1
            self.stats['processing_times'].append(processing_time)
            
            return best_result
            
        except Exception as e:
            logger.error(f"OCR failed: {e}")
            return {'text': '', 'confidence': 0.0, 'processing_time': 0.0}
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize OCR text"""
        # Remove special characters and spaces
        cleaned = re.sub(r'[^A-Z0-9]', '', text.upper())
        
        # Common OCR corrections
        corrections = {
            '0': 'O', 'O': '0',  # Context-dependent
            '1': 'I', 'I': '1',
            '5': 'S', 'S': '5',
            '8': 'B', 'B': '8'
        }
        
        # Apply corrections based on position (numbers vs letters)
        # This is a simplified approach - more sophisticated logic can be added
        
        return cleaned
    
    def _validate_license_plate(self, text: str) -> bool:
        """Validate if text matches license plate patterns"""
        if len(text) < 4:
            return False
        
        # Check against known patterns
        for pattern_name, pattern in self.plate_patterns.items():
            if re.match(pattern, text):
                return True
        
        return False
    
    def check_security_database(self, license_plate: str) -> Dict:
        """
        Check if license plate is in stolen vehicle database
        
        Args:
            license_plate: License plate text to check
            
        Returns:
            Security check results
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Exact match
            cursor.execute('''
                SELECT * FROM stolen_vehicles 
                WHERE license_plate = ? AND status = 'active'
            ''', (license_plate,))
            
            exact_match = cursor.fetchone()
            
            if exact_match:
                # Log security alert
                cursor.execute('''
                    INSERT INTO security_alerts 
                    (license_plate, confidence, location)
                    VALUES (?, ?, ?)
                ''', (license_plate, 1.0, 'intersection_camera'))
                
                conn.commit()
                self.stats['security_alerts'] += 1
                
                conn.close()
                
                return {
                    'is_stolen': True,
                    'match_type': 'exact',
                    'confidence': 1.0,
                    'vehicle_info': {
                        'license_plate': exact_match[1],
                        'vehicle_type': exact_match[2],
                        'color': exact_match[3],
                        'make': exact_match[4],
                        'model': exact_match[5],
                        'reported_date': exact_match[6]
                    }
                }
            
            # Fuzzy matching for partial reads
            cursor.execute('''
                SELECT * FROM stolen_vehicles 
                WHERE status = 'active'
            ''')
            
            all_stolen = cursor.fetchall()
            conn.close()
            
            # Simple fuzzy matching
            for stolen in all_stolen:
                stolen_plate = stolen[1]
                similarity = self._calculate_similarity(license_plate, stolen_plate)
                
                if similarity > 0.8:  # 80% similarity threshold
                    return {
                        'is_stolen': True,
                        'match_type': 'fuzzy',
                        'confidence': similarity,
                        'vehicle_info': {
                            'license_plate': stolen[1],
                            'vehicle_type': stolen[2],
                            'color': stolen[3],
                            'make': stolen[4],
                            'model': stolen[5],
                            'reported_date': stolen[6]
                        }
                    }
            
            return {'is_stolen': False, 'match_type': 'none', 'confidence': 0.0}
            
        except Exception as e:
            logger.error(f"Security database check failed: {e}")
            return {'is_stolen': False, 'match_type': 'error', 'confidence': 0.0}
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two strings (simple Levenshtein-based)"""
        if not text1 or not text2:
            return 0.0
        
        # Simple character-based similarity
        matches = sum(1 for a, b in zip(text1, text2) if a == b)
        max_len = max(len(text1), len(text2))
        
        return matches / max_len if max_len > 0 else 0.0
    
    def process_vehicle_detection(
        self, 
        frame: np.ndarray, 
        vehicle_detections: List[Dict]
    ) -> List[Dict]:
        """
        Process vehicle detections to extract license plates
        
        Args:
            frame: Original frame
            vehicle_detections: Vehicle detection results from YOLO
            
        Returns:
            Enhanced detections with license plate information
        """
        enhanced_detections = []
        
        for vehicle in vehicle_detections:
            enhanced_vehicle = vehicle.copy()
            
            # Extract vehicle crop
            x1, y1, x2, y2 = vehicle['bbox']
            vehicle_crop = frame[y1:y2, x1:x2]
            
            # Detect license plates in vehicle crop
            plates = self.detect_license_plates(vehicle_crop)
            
            license_plate_info = {'detected': False, 'text': '', 'confidence': 0.0}
            
            if plates:
                # Process the best plate candidate
                best_plate = plates[0]
                ocr_result = self.read_license_plate(best_plate['roi'])
                
                if ocr_result['confidence'] > self.confidence_threshold:
                    license_plate_info = {
                        'detected': True,
                        'text': ocr_result['text'],
                        'confidence': ocr_result['confidence'],
                        'bbox': best_plate['bbox'],
                        'processing_time': ocr_result['processing_time']
                    }
                    
                    # Security check
                    security_result = self.check_security_database(ocr_result['text'])
                    license_plate_info['security'] = security_result
            
            enhanced_vehicle['license_plate'] = license_plate_info
            enhanced_detections.append(enhanced_vehicle)
        
        return enhanced_detections
    
    def get_statistics(self) -> Dict:
        """Get OCR system statistics"""
        success_rate = 0.0
        if self.stats['total_detections'] > 0:
            success_rate = self.stats['successful_reads'] / self.stats['total_detections']
        
        avg_processing_time = 0.0
        if self.stats['processing_times']:
            avg_processing_time = np.mean(self.stats['processing_times'])
        
        return {
            'total_detections': self.stats['total_detections'],
            'successful_reads': self.stats['successful_reads'],
            'success_rate': success_rate,
            'security_alerts': self.stats['security_alerts'],
            'avg_processing_time': avg_processing_time
        }
    
    def visualize_results(
        self, 
        frame: np.ndarray, 
        enhanced_detections: List[Dict]
    ) -> np.ndarray:
        """
        Visualize license plate detection results
        
        Args:
            frame: Original frame
            enhanced_detections: Enhanced detection results
            
        Returns:
            Annotated frame
        """
        annotated_frame = frame.copy()
        
        for vehicle in enhanced_detections:
            x1, y1, x2, y2 = vehicle['bbox']
            
            # Draw vehicle bounding box
            color = (0, 255, 0)  # Green for normal vehicles
            
            # Check for security alerts
            if vehicle['license_plate']['detected']:
                lp_info = vehicle['license_plate']
                if lp_info.get('security', {}).get('is_stolen', False):
                    color = (0, 0, 255)  # Red for stolen vehicles
                    
                    # Add alert text
                    cv2.putText(
                        annotated_frame,
                        "SECURITY ALERT!",
                        (x1, y1 - 40),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.8,
                        (0, 0, 255),
                        2
                    )
            
            cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 2)
            
            # Add license plate text if detected
            if vehicle['license_plate']['detected']:
                lp_text = vehicle['license_plate']['text']
                confidence = vehicle['license_plate']['confidence']
                
                label = f"{lp_text} ({confidence:.2f})"
                cv2.putText(
                    annotated_frame,
                    label,
                    (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    color,
                    2
                )
        
        return annotated_frame


def main():
    """Test the License Plate OCR system"""
    # Initialize OCR system
    ocr_system = LicensePlateOCR(languages=['en'])
    
    # Test with sample image or webcam
    cap = cv2.VideoCapture(0)
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # For testing, we'll simulate vehicle detections
        # In real implementation, this would come from YOLO detector
        height, width = frame.shape[:2]
        sample_detections = [
            {
                'id': 0,
                'class': 'car',
                'confidence': 0.9,
                'bbox': [100, 100, 300, 200],
                'center': [200, 150],
                'dimensions': [200, 100],
                'area': 20000
            }
        ]
        
        # Process detections
        enhanced_detections = ocr_system.process_vehicle_detection(frame, sample_detections)
        
        # Visualize results
        annotated_frame = ocr_system.visualize_results(frame, enhanced_detections)
        
        # Display frame
        cv2.imshow('License Plate Recognition', annotated_frame)
        
        # Print statistics periodically
        if cv2.waitKey(1) & 0xFF == ord('s'):
            stats = ocr_system.get_statistics()
            print(f"OCR Statistics: {stats}")
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()