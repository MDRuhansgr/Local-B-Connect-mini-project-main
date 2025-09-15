"""
Logging utilities for Traffic Control System
Provides centralized logging configuration and utilities
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional
import json
from datetime import datetime


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging"""
    
    def format(self, record):
        """Format log record as JSON"""
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                          'filename', 'module', 'exc_info', 'exc_text', 'stack_info',
                          'lineno', 'funcName', 'created', 'msecs', 'relativeCreated',
                          'thread', 'threadName', 'processName', 'process', 'getMessage']:
                log_entry[key] = value
        
        return json.dumps(log_entry)


class ColoredFormatter(logging.Formatter):
    """Colored console formatter"""
    
    # Color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'        # Reset
    }
    
    def format(self, record):
        """Format log record with colors"""
        # Get color for log level
        color = self.COLORS.get(record.levelname, '')
        reset = self.COLORS['RESET']
        
        # Format the record
        formatted = super().format(record)
        
        # Add colors
        return f"{color}{formatted}{reset}"


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    log_format: str = "standard",
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
    console_output: bool = True
) -> logging.Logger:
    """
    Setup centralized logging configuration
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (optional)
        log_format: Format type ("standard", "detailed", "json")
        max_bytes: Maximum log file size before rotation
        backup_count: Number of backup files to keep
        console_output: Whether to output to console
        
    Returns:
        Configured root logger
    """
    # Convert string level to logging level
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    
    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Define formatters
    formatters = {
        "standard": logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        ),
        "detailed": logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(funcName)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        ),
        "json": JSONFormatter()
    }
    
    formatter = formatters.get(log_format, formatters["standard"])
    
    # Console handler
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(numeric_level)
        
        # Use colored formatter for console
        if log_format != "json":
            console_formatter = ColoredFormatter(formatter._fmt, formatter.datefmt)
            console_handler.setFormatter(console_formatter)
        else:
            console_handler.setFormatter(formatter)
        
        root_logger.addHandler(console_handler)
    
    # File handler
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Rotating file handler
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count
        )
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)
        
        root_logger.addHandler(file_handler)
    
    # Set up specific logger levels for third-party libraries
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('matplotlib').setLevel(logging.WARNING)
    logging.getLogger('PIL').setLevel(logging.WARNING)
    
    return root_logger


class PerformanceLogger:
    """Logger for performance metrics and timing"""
    
    def __init__(self, logger_name: str = "performance"):
        self.logger = logging.getLogger(logger_name)
    
    def log_processing_time(self, operation: str, processing_time: float, **kwargs):
        """Log processing time for operations"""
        self.logger.info(
            f"Performance: {operation}",
            extra={
                'operation': operation,
                'processing_time': processing_time,
                'metric_type': 'processing_time',
                **kwargs
            }
        )
    
    def log_throughput(self, operation: str, count: int, duration: float, **kwargs):
        """Log throughput metrics"""
        throughput = count / duration if duration > 0 else 0
        
        self.logger.info(
            f"Throughput: {operation}",
            extra={
                'operation': operation,
                'count': count,
                'duration': duration,
                'throughput': throughput,
                'metric_type': 'throughput',
                **kwargs
            }
        )
    
    def log_system_metrics(self, cpu_percent: float, memory_mb: float, **kwargs):
        """Log system resource metrics"""
        self.logger.info(
            "System metrics",
            extra={
                'cpu_percent': cpu_percent,
                'memory_mb': memory_mb,
                'metric_type': 'system_metrics',
                **kwargs
            }
        )


class SecurityLogger:
    """Logger for security events and alerts"""
    
    def __init__(self, logger_name: str = "security"):
        self.logger = logging.getLogger(logger_name)
    
    def log_stolen_vehicle_detection(
        self,
        license_plate: str,
        confidence: float,
        location: str,
        alert_id: Optional[int] = None,
        **kwargs
    ):
        """Log stolen vehicle detection"""
        self.logger.warning(
            f"STOLEN VEHICLE DETECTED: {license_plate}",
            extra={
                'event_type': 'stolen_vehicle_detection',
                'license_plate': license_plate,
                'confidence': confidence,
                'location': location,
                'alert_id': alert_id,
                **kwargs
            }
        )
    
    def log_security_alert(
        self,
        alert_level: str,
        message: str,
        alert_id: Optional[int] = None,
        **kwargs
    ):
        """Log general security alert"""
        log_level = {
            'info': logging.INFO,
            'warning': logging.WARNING,
            'critical': logging.CRITICAL
        }.get(alert_level.lower(), logging.INFO)
        
        self.logger.log(
            log_level,
            f"SECURITY ALERT [{alert_level.upper()}]: {message}",
            extra={
                'event_type': 'security_alert',
                'alert_level': alert_level,
                'alert_id': alert_id,
                **kwargs
            }
        )
    
    def log_unauthorized_access(self, source: str, **kwargs):
        """Log unauthorized access attempts"""
        self.logger.error(
            f"UNAUTHORIZED ACCESS ATTEMPT from {source}",
            extra={
                'event_type': 'unauthorized_access',
                'source': source,
                **kwargs
            }
        )


class TrafficLogger:
    """Logger for traffic-specific events"""
    
    def __init__(self, logger_name: str = "traffic"):
        self.logger = logging.getLogger(logger_name)
    
    def log_traffic_control_action(
        self,
        intersection_id: str,
        action: str,
        phase: int,
        duration: float,
        **kwargs
    ):
        """Log traffic control actions"""
        self.logger.info(
            f"Traffic control: {action} at {intersection_id}",
            extra={
                'event_type': 'traffic_control',
                'intersection_id': intersection_id,
                'action': action,
                'phase': phase,
                'duration': duration,
                **kwargs
            }
        )
    
    def log_emergency_override(
        self,
        intersection_id: str,
        direction: str,
        vehicle_id: Optional[str] = None,
        **kwargs
    ):
        """Log emergency vehicle overrides"""
        self.logger.warning(
            f"EMERGENCY OVERRIDE: {direction} at {intersection_id}",
            extra={
                'event_type': 'emergency_override',
                'intersection_id': intersection_id,
                'direction': direction,
                'vehicle_id': vehicle_id,
                **kwargs
            }
        )
    
    def log_traffic_metrics(
        self,
        intersection_id: str,
        throughput: float,
        avg_wait_time: float,
        queue_length: int,
        **kwargs
    ):
        """Log traffic performance metrics"""
        self.logger.info(
            f"Traffic metrics for {intersection_id}",
            extra={
                'event_type': 'traffic_metrics',
                'intersection_id': intersection_id,
                'throughput': throughput,
                'avg_wait_time': avg_wait_time,
                'queue_length': queue_length,
                'metric_type': 'traffic_performance',
                **kwargs
            }
        )


def get_logger(name: str) -> logging.Logger:
    """Get logger instance by name"""
    return logging.getLogger(name)


def get_performance_logger() -> PerformanceLogger:
    """Get performance logger instance"""
    return PerformanceLogger()


def get_security_logger() -> SecurityLogger:
    """Get security logger instance"""
    return SecurityLogger()


def get_traffic_logger() -> TrafficLogger:
    """Get traffic logger instance"""
    return TrafficLogger()


def main():
    """Test logging setup"""
    # Setup logging
    setup_logging(
        level="DEBUG",
        log_file="logs/test.log",
        log_format="detailed",
        console_output=True
    )
    
    # Test basic logging
    logger = logging.getLogger(__name__)
    logger.debug("Debug message")
    logger.info("Info message")
    logger.warning("Warning message")
    logger.error("Error message")
    logger.critical("Critical message")
    
    # Test performance logging
    perf_logger = get_performance_logger()
    perf_logger.log_processing_time("test_operation", 0.123, frame_id=1)
    perf_logger.log_throughput("detection", 100, 10.0)
    
    # Test security logging
    security_logger = get_security_logger()
    security_logger.log_stolen_vehicle_detection("KA01AB1234", 0.95, "Intersection 1", alert_id=123)
    security_logger.log_security_alert("critical", "Test security alert", alert_id=124)
    
    # Test traffic logging
    traffic_logger = get_traffic_logger()
    traffic_logger.log_traffic_control_action("INT001", "phase_change", 2, 45.0)
    traffic_logger.log_emergency_override("INT001", "north", vehicle_id="EMG001")
    traffic_logger.log_traffic_metrics("INT001", 1500.0, 23.5, 12)
    
    print("Logging test completed. Check logs/test.log")


if __name__ == "__main__":
    main()