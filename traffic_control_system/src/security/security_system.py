"""
Security System Module
Implements stolen vehicle detection and alert management
"""

import sqlite3
import json
import logging
import hashlib
import time
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
import numpy as np
from pathlib import Path
import cv2
import smtplib
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
from email.mime.image import MimeImage
import requests
from dataclasses import dataclass, asdict
import threading
import queue
import pickle

logger = logging.getLogger(__name__)


@dataclass
class StolenVehicle:
    """Stolen vehicle record"""
    license_plate: str
    vehicle_type: str
    color: str
    make: str
    model: str
    year: Optional[int]
    reported_date: str
    case_number: str
    reporting_agency: str
    status: str = "active"
    priority: str = "medium"  # low, medium, high, critical
    additional_info: Optional[str] = None


@dataclass
class SecurityAlert:
    """Security alert record"""
    id: Optional[int]
    license_plate: str
    detection_time: str
    confidence: float
    location: str
    camera_id: str
    image_path: Optional[str]
    vehicle_info: Optional[Dict]
    alert_level: str  # info, warning, critical
    status: str = "pending"  # pending, investigating, resolved, false_positive
    assigned_officer: Optional[str] = None
    response_time: Optional[float] = None
    notes: Optional[str] = None


class StolenVehicleDatabase:
    """
    Stolen Vehicle Database Manager
    
    Features:
    - SQLite database for stolen vehicles
    - Fuzzy matching for partial license plates
    - Vehicle information management
    - Alert history tracking
    """
    
    def __init__(self, db_path: str = "data/security_db.sqlite"):
        """
        Initialize stolen vehicle database
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        self._init_database()
        self._populate_sample_data()
        
        logger.info(f"Stolen vehicle database initialized: {db_path}")
    
    def _init_database(self):
        """Initialize database tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Stolen vehicles table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stolen_vehicles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                license_plate TEXT UNIQUE NOT NULL,
                vehicle_type TEXT NOT NULL,
                color TEXT,
                make TEXT,
                model TEXT,
                year INTEGER,
                reported_date TEXT NOT NULL,
                case_number TEXT UNIQUE,
                reporting_agency TEXT,
                status TEXT DEFAULT 'active',
                priority TEXT DEFAULT 'medium',
                additional_info TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Security alerts table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS security_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                license_plate TEXT NOT NULL,
                detection_time TIMESTAMP NOT NULL,
                confidence REAL NOT NULL,
                location TEXT,
                camera_id TEXT,
                image_path TEXT,
                vehicle_info TEXT,
                alert_level TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                assigned_officer TEXT,
                response_time REAL,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Alert notifications table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alert_notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_id INTEGER NOT NULL,
                notification_type TEXT NOT NULL,
                recipient TEXT NOT NULL,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'sent',
                FOREIGN KEY (alert_id) REFERENCES security_alerts (id)
            )
        ''')
        
        # Create indices for performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_license_plate ON stolen_vehicles(license_plate)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_status ON stolen_vehicles(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_alert_time ON security_alerts(detection_time)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_alert_status ON security_alerts(status)')
        
        conn.commit()
        conn.close()
    
    def _populate_sample_data(self):
        """Populate database with sample stolen vehicle data"""
        sample_vehicles = [
            StolenVehicle("KA01AB1234", "car", "red", "Toyota", "Camry", 2020, "2024-01-15", "CASE001", "Bangalore Police", priority="high"),
            StolenVehicle("MH02CD5678", "motorcycle", "black", "Honda", "CBR600RR", 2019, "2024-02-10", "CASE002", "Mumbai Police", priority="medium"),
            StolenVehicle("DL03EF9012", "truck", "white", "Tata", "LPT 1618", 2018, "2024-01-20", "CASE003", "Delhi Police", priority="low"),
            StolenVehicle("TN04GH3456", "car", "blue", "Hyundai", "i20", 2021, "2024-02-05", "CASE004", "Chennai Police", priority="critical"),
            StolenVehicle("UP05IJ7890", "bus", "yellow", "Ashok Leyland", "Viking", 2017, "2024-01-30", "CASE005", "UP Police", priority="medium"),
            StolenVehicle("GJ06KL1234", "car", "silver", "Maruti", "Swift", 2022, "2024-02-12", "CASE006", "Gujarat Police", priority="high"),
            StolenVehicle("RJ07MN5678", "suv", "black", "Mahindra", "XUV500", 2020, "2024-01-25", "CASE007", "Rajasthan Police", priority="medium"),
            StolenVehicle("WB08OP9012", "car", "white", "Ford", "EcoSport", 2019, "2024-02-08", "CASE008", "West Bengal Police", priority="low"),
            StolenVehicle("AP09QR3456", "motorcycle", "red", "Yamaha", "R15", 2021, "2024-01-18", "CASE009", "AP Police", priority="high"),
            StolenVehicle("KL10ST7890", "car", "green", "Tata", "Nexon", 2022, "2024-02-15", "CASE010", "Kerala Police", priority="medium")
        ]
        
        for vehicle in sample_vehicles:
            self.add_stolen_vehicle(vehicle)
    
    def add_stolen_vehicle(self, vehicle: StolenVehicle) -> bool:
        """Add stolen vehicle to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO stolen_vehicles 
                (license_plate, vehicle_type, color, make, model, year, 
                 reported_date, case_number, reporting_agency, status, priority, additional_info)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                vehicle.license_plate, vehicle.vehicle_type, vehicle.color,
                vehicle.make, vehicle.model, vehicle.year, vehicle.reported_date,
                vehicle.case_number, vehicle.reporting_agency, vehicle.status,
                vehicle.priority, vehicle.additional_info
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Added stolen vehicle: {vehicle.license_plate}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add stolen vehicle: {e}")
            return False
    
    def search_stolen_vehicle(self, license_plate: str, fuzzy: bool = True) -> Optional[Dict]:
        """
        Search for stolen vehicle by license plate
        
        Args:
            license_plate: License plate to search
            fuzzy: Enable fuzzy matching
            
        Returns:
            Stolen vehicle information if found
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Exact match first
            cursor.execute('''
                SELECT * FROM stolen_vehicles 
                WHERE license_plate = ? AND status = 'active'
            ''', (license_plate,))
            
            result = cursor.fetchone()
            
            if result:
                conn.close()
                return self._row_to_dict(result)
            
            # Fuzzy matching if enabled
            if fuzzy:
                cursor.execute('''
                    SELECT * FROM stolen_vehicles 
                    WHERE status = 'active'
                ''')
                
                all_vehicles = cursor.fetchall()
                
                for vehicle in all_vehicles:
                    stored_plate = vehicle[1]  # license_plate column
                    similarity = self._calculate_similarity(license_plate, stored_plate)
                    
                    if similarity > 0.8:  # 80% similarity threshold
                        conn.close()
                        result_dict = self._row_to_dict(vehicle)
                        result_dict['match_similarity'] = similarity
                        result_dict['match_type'] = 'fuzzy'
                        return result_dict
            
            conn.close()
            return None
            
        except Exception as e:
            logger.error(f"Database search failed: {e}")
            return None
    
    def _row_to_dict(self, row: Tuple) -> Dict:
        """Convert database row to dictionary"""
        columns = [
            'id', 'license_plate', 'vehicle_type', 'color', 'make', 'model',
            'year', 'reported_date', 'case_number', 'reporting_agency',
            'status', 'priority', 'additional_info', 'created_at', 'updated_at'
        ]
        
        return dict(zip(columns, row))
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two license plates"""
        if not text1 or not text2:
            return 0.0
        
        # Levenshtein distance-based similarity
        def levenshtein_distance(s1, s2):
            if len(s1) < len(s2):
                return levenshtein_distance(s2, s1)
            
            if len(s2) == 0:
                return len(s1)
            
            previous_row = list(range(len(s2) + 1))
            for i, c1 in enumerate(s1):
                current_row = [i + 1]
                for j, c2 in enumerate(s2):
                    insertions = previous_row[j + 1] + 1
                    deletions = current_row[j] + 1
                    substitutions = previous_row[j] + (c1 != c2)
                    current_row.append(min(insertions, deletions, substitutions))
                previous_row = current_row
            
            return previous_row[-1]
        
        distance = levenshtein_distance(text1.upper(), text2.upper())
        max_len = max(len(text1), len(text2))
        
        return 1.0 - (distance / max_len) if max_len > 0 else 0.0
    
    def get_statistics(self) -> Dict:
        """Get database statistics"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Total stolen vehicles
            cursor.execute('SELECT COUNT(*) FROM stolen_vehicles WHERE status = "active"')
            total_active = cursor.fetchone()[0]
            
            # By priority
            cursor.execute('''
                SELECT priority, COUNT(*) FROM stolen_vehicles 
                WHERE status = "active" GROUP BY priority
            ''')
            by_priority = dict(cursor.fetchall())
            
            # By vehicle type
            cursor.execute('''
                SELECT vehicle_type, COUNT(*) FROM stolen_vehicles 
                WHERE status = "active" GROUP BY vehicle_type
            ''')
            by_type = dict(cursor.fetchall())
            
            # Recent alerts
            cursor.execute('''
                SELECT COUNT(*) FROM security_alerts 
                WHERE detection_time > datetime('now', '-24 hours')
            ''')
            recent_alerts = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                'total_active_stolen': total_active,
                'by_priority': by_priority,
                'by_vehicle_type': by_type,
                'recent_alerts_24h': recent_alerts
            }
            
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {}


class AlertManager:
    """
    Security Alert Management System
    
    Features:
    - Alert creation and management
    - Multi-channel notifications (email, SMS, API)
    - Alert prioritization and escalation
    - Response tracking
    """
    
    def __init__(
        self,
        db_path: str = "data/security_db.sqlite",
        notification_config: Dict = None
    ):
        """
        Initialize alert manager
        
        Args:
            db_path: Path to security database
            notification_config: Notification configuration
        """
        self.db_path = db_path
        self.notification_config = notification_config or {}
        
        # Alert queue for processing
        self.alert_queue = queue.Queue()
        self.processing_thread = threading.Thread(target=self._process_alerts, daemon=True)
        self.processing_thread.start()
        
        # Alert statistics
        self.stats = {
            'total_alerts': 0,
            'alerts_today': 0,
            'response_times': [],
            'false_positives': 0
        }
        
        logger.info("Alert manager initialized")
    
    def create_alert(
        self,
        license_plate: str,
        confidence: float,
        location: str,
        camera_id: str,
        vehicle_info: Dict,
        image_path: Optional[str] = None
    ) -> int:
        """
        Create new security alert
        
        Args:
            license_plate: Detected license plate
            confidence: Detection confidence
            location: Detection location
            camera_id: Camera identifier
            vehicle_info: Vehicle information from stolen database
            image_path: Path to captured image
            
        Returns:
            Alert ID
        """
        try:
            # Determine alert level based on vehicle priority and confidence
            priority = vehicle_info.get('priority', 'medium')
            alert_level = self._determine_alert_level(priority, confidence)
            
            # Create alert record
            alert = SecurityAlert(
                id=None,
                license_plate=license_plate,
                detection_time=datetime.now().isoformat(),
                confidence=confidence,
                location=location,
                camera_id=camera_id,
                image_path=image_path,
                vehicle_info=vehicle_info,
                alert_level=alert_level,
                status="pending"
            )
            
            # Insert into database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO security_alerts 
                (license_plate, detection_time, confidence, location, camera_id,
                 image_path, vehicle_info, alert_level, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                alert.license_plate, alert.detection_time, alert.confidence,
                alert.location, alert.camera_id, alert.image_path,
                json.dumps(alert.vehicle_info), alert.alert_level, alert.status
            ))
            
            alert_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            # Add to processing queue
            alert.id = alert_id
            self.alert_queue.put(alert)
            
            # Update statistics
            self.stats['total_alerts'] += 1
            self._update_daily_stats()
            
            logger.info(f"Security alert created: ID={alert_id}, Plate={license_plate}, Level={alert_level}")
            
            return alert_id
            
        except Exception as e:
            logger.error(f"Failed to create alert: {e}")
            return -1
    
    def _determine_alert_level(self, priority: str, confidence: float) -> str:
        """Determine alert level based on priority and confidence"""
        if priority == "critical":
            return "critical"
        elif priority == "high" and confidence > 0.8:
            return "critical"
        elif priority == "high" or (priority == "medium" and confidence > 0.9):
            return "warning"
        else:
            return "info"
    
    def _process_alerts(self):
        """Process alerts from queue (runs in separate thread)"""
        while True:
            try:
                alert = self.alert_queue.get(timeout=1)
                self._handle_alert(alert)
                self.alert_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Alert processing failed: {e}")
    
    def _handle_alert(self, alert: SecurityAlert):
        """Handle individual alert"""
        try:
            # Send notifications based on alert level
            if alert.alert_level == "critical":
                self._send_immediate_notifications(alert)
            elif alert.alert_level == "warning":
                self._send_standard_notifications(alert)
            else:
                self._send_info_notifications(alert)
            
            # Update alert status
            self._update_alert_status(alert.id, "notified")
            
            logger.info(f"Alert {alert.id} processed and notifications sent")
            
        except Exception as e:
            logger.error(f"Failed to handle alert {alert.id}: {e}")
    
    def _send_immediate_notifications(self, alert: SecurityAlert):
        """Send immediate notifications for critical alerts"""
        # Email notification
        self._send_email_notification(alert, urgent=True)
        
        # SMS notification (if configured)
        if 'sms' in self.notification_config:
            self._send_sms_notification(alert)
        
        # API webhook (if configured)
        if 'webhook' in self.notification_config:
            self._send_webhook_notification(alert)
    
    def _send_standard_notifications(self, alert: SecurityAlert):
        """Send standard notifications"""
        # Email notification
        self._send_email_notification(alert, urgent=False)
        
        # API webhook (if configured)
        if 'webhook' in self.notification_config:
            self._send_webhook_notification(alert)
    
    def _send_info_notifications(self, alert: SecurityAlert):
        """Send info-level notifications"""
        # Log to system only for info alerts
        logger.info(f"Info alert: {alert.license_plate} detected at {alert.location}")
    
    def _send_email_notification(self, alert: SecurityAlert, urgent: bool = False):
        """Send email notification"""
        email_config = self.notification_config.get('email', {})
        if not email_config:
            return
        
        try:
            # Create message
            msg = MimeMultipart()
            msg['From'] = email_config['from']
            msg['To'] = ', '.join(email_config['to'])
            
            if urgent:
                msg['Subject'] = f"URGENT: Stolen Vehicle Alert - {alert.license_plate}"
            else:
                msg['Subject'] = f"Stolen Vehicle Alert - {alert.license_plate}"
            
            # Email body
            body = self._create_email_body(alert)
            msg.attach(MimeText(body, 'html'))
            
            # Attach image if available
            if alert.image_path and Path(alert.image_path).exists():
                with open(alert.image_path, 'rb') as f:
                    img_data = f.read()
                image = MimeImage(img_data)
                image.add_header('Content-Disposition', 'attachment', filename='detection.jpg')
                msg.attach(image)
            
            # Send email
            server = smtplib.SMTP(email_config['smtp_server'], email_config['smtp_port'])
            server.starttls()
            server.login(email_config['username'], email_config['password'])
            server.send_message(msg)
            server.quit()
            
            # Log notification
            self._log_notification(alert.id, 'email', email_config['to'])
            
        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")
    
    def _create_email_body(self, alert: SecurityAlert) -> str:
        """Create HTML email body"""
        vehicle_info = alert.vehicle_info or {}
        
        return f"""
        <html>
        <body>
            <h2>Stolen Vehicle Detection Alert</h2>
            <table border="1" style="border-collapse: collapse;">
                <tr><th>License Plate</th><td>{alert.license_plate}</td></tr>
                <tr><th>Detection Time</th><td>{alert.detection_time}</td></tr>
                <tr><th>Location</th><td>{alert.location}</td></tr>
                <tr><th>Camera ID</th><td>{alert.camera_id}</td></tr>
                <tr><th>Confidence</th><td>{alert.confidence:.2f}</td></tr>
                <tr><th>Alert Level</th><td>{alert.alert_level.upper()}</td></tr>
            </table>
            
            <h3>Vehicle Information</h3>
            <table border="1" style="border-collapse: collapse;">
                <tr><th>Make/Model</th><td>{vehicle_info.get('make', 'Unknown')} {vehicle_info.get('model', '')}</td></tr>
                <tr><th>Color</th><td>{vehicle_info.get('color', 'Unknown')}</td></tr>
                <tr><th>Type</th><td>{vehicle_info.get('vehicle_type', 'Unknown')}</td></tr>
                <tr><th>Year</th><td>{vehicle_info.get('year', 'Unknown')}</td></tr>
                <tr><th>Case Number</th><td>{vehicle_info.get('case_number', 'Unknown')}</td></tr>
                <tr><th>Reporting Agency</th><td>{vehicle_info.get('reporting_agency', 'Unknown')}</td></tr>
                <tr><th>Priority</th><td>{vehicle_info.get('priority', 'Unknown')}</td></tr>
            </table>
            
            <p><strong>Please respond to this alert immediately if it requires urgent action.</strong></p>
        </body>
        </html>
        """
    
    def _send_webhook_notification(self, alert: SecurityAlert):
        """Send webhook notification"""
        webhook_config = self.notification_config.get('webhook', {})
        if not webhook_config:
            return
        
        try:
            payload = {
                'alert_id': alert.id,
                'license_plate': alert.license_plate,
                'detection_time': alert.detection_time,
                'confidence': alert.confidence,
                'location': alert.location,
                'camera_id': alert.camera_id,
                'alert_level': alert.alert_level,
                'vehicle_info': alert.vehicle_info
            }
            
            response = requests.post(
                webhook_config['url'],
                json=payload,
                headers=webhook_config.get('headers', {}),
                timeout=10
            )
            
            if response.status_code == 200:
                self._log_notification(alert.id, 'webhook', webhook_config['url'])
            else:
                logger.error(f"Webhook failed with status {response.status_code}")
                
        except Exception as e:
            logger.error(f"Failed to send webhook notification: {e}")
    
    def _log_notification(self, alert_id: int, notification_type: str, recipient: str):
        """Log notification in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO alert_notifications (alert_id, notification_type, recipient)
                VALUES (?, ?, ?)
            ''', (alert_id, notification_type, str(recipient)))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to log notification: {e}")
    
    def _update_alert_status(self, alert_id: int, status: str):
        """Update alert status"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE security_alerts 
                SET status = ?, updated_at = CURRENT_TIMESTAMP 
                WHERE id = ?
            ''', (status, alert_id))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to update alert status: {e}")
    
    def _update_daily_stats(self):
        """Update daily statistics"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT COUNT(*) FROM security_alerts 
                WHERE DATE(detection_time) = DATE('now')
            ''')
            
            self.stats['alerts_today'] = cursor.fetchone()[0]
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to update daily stats: {e}")
    
    def get_alert_statistics(self) -> Dict:
        """Get alert statistics"""
        self._update_daily_stats()
        return self.stats.copy()
    
    def get_recent_alerts(self, hours: int = 24) -> List[Dict]:
        """Get recent alerts"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM security_alerts 
                WHERE detection_time > datetime('now', '-{} hours')
                ORDER BY detection_time DESC
            '''.format(hours))
            
            alerts = []
            columns = [desc[0] for desc in cursor.description]
            
            for row in cursor.fetchall():
                alert_dict = dict(zip(columns, row))
                if alert_dict['vehicle_info']:
                    alert_dict['vehicle_info'] = json.loads(alert_dict['vehicle_info'])
                alerts.append(alert_dict)
            
            conn.close()
            return alerts
            
        except Exception as e:
            logger.error(f"Failed to get recent alerts: {e}")
            return []


class SecuritySystem:
    """
    Complete Security System Integration
    
    Combines stolen vehicle database with alert management
    """
    
    def __init__(
        self,
        db_path: str = "data/security_db.sqlite",
        notification_config: Dict = None
    ):
        """Initialize security system"""
        self.database = StolenVehicleDatabase(db_path)
        self.alert_manager = AlertManager(db_path, notification_config)
        
        logger.info("Security system initialized")
    
    def check_vehicle(
        self,
        license_plate: str,
        confidence: float,
        location: str,
        camera_id: str,
        image_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Check vehicle against stolen database and create alert if needed
        
        Args:
            license_plate: Detected license plate
            confidence: Detection confidence
            location: Detection location
            camera_id: Camera identifier
            image_path: Path to captured image
            
        Returns:
            Check result with alert information
        """
        # Search stolen vehicle database
        stolen_vehicle = self.database.search_stolen_vehicle(license_plate, fuzzy=True)
        
        result = {
            'license_plate': license_plate,
            'is_stolen': False,
            'confidence': confidence,
            'match_type': 'none',
            'alert_created': False,
            'alert_id': None
        }
        
        if stolen_vehicle:
            result['is_stolen'] = True
            result['vehicle_info'] = stolen_vehicle
            result['match_type'] = stolen_vehicle.get('match_type', 'exact')
            
            # Create security alert
            alert_id = self.alert_manager.create_alert(
                license_plate=license_plate,
                confidence=confidence,
                location=location,
                camera_id=camera_id,
                vehicle_info=stolen_vehicle,
                image_path=image_path
            )
            
            if alert_id > 0:
                result['alert_created'] = True
                result['alert_id'] = alert_id
        
        return result
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get overall system status"""
        db_stats = self.database.get_statistics()
        alert_stats = self.alert_manager.get_alert_statistics()
        
        return {
            'database_stats': db_stats,
            'alert_stats': alert_stats,
            'system_health': 'operational',
            'last_updated': datetime.now().isoformat()
        }
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get data for security dashboard"""
        return {
            'system_status': self.get_system_status(),
            'recent_alerts': self.alert_manager.get_recent_alerts(24),
            'stolen_vehicles_count': self.database.get_statistics()['total_active_stolen']
        }


def main():
    """Test security system"""
    print("Testing Security System...")
    
    # Initialize security system
    notification_config = {
        'email': {
            'from': 'traffic-system@example.com',
            'to': ['security@police.gov.in'],
            'smtp_server': 'smtp.gmail.com',
            'smtp_port': 587,
            'username': 'your-email@gmail.com',
            'password': 'your-app-password'
        }
    }
    
    security_system = SecuritySystem(notification_config=notification_config)
    
    # Test vehicle check
    print("\nTesting stolen vehicle detection...")
    
    # Test with known stolen vehicle
    result1 = security_system.check_vehicle(
        license_plate="KA01AB1234",
        confidence=0.95,
        location="Intersection Camera 1",
        camera_id="CAM001"
    )
    
    print(f"Check result 1: {result1}")
    
    # Test with fuzzy match
    result2 = security_system.check_vehicle(
        license_plate="KA01AB123X",  # Similar to KA01AB1234
        confidence=0.85,
        location="Intersection Camera 2",
        camera_id="CAM002"
    )
    
    print(f"Check result 2: {result2}")
    
    # Test with non-stolen vehicle
    result3 = security_system.check_vehicle(
        license_plate="KA99XY9999",
        confidence=0.90,
        location="Intersection Camera 3",
        camera_id="CAM003"
    )
    
    print(f"Check result 3: {result3}")
    
    # Get system status
    print("\nSystem Status:")
    status = security_system.get_system_status()
    print(json.dumps(status, indent=2, default=str))
    
    # Get recent alerts
    print("\nRecent Alerts:")
    recent_alerts = security_system.alert_manager.get_recent_alerts(24)
    for alert in recent_alerts:
        print(f"Alert {alert['id']}: {alert['license_plate']} at {alert['location']} - {alert['alert_level']}")


if __name__ == "__main__":
    main()