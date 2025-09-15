"""
Configuration Manager for Traffic Control System
Handles system configuration loading and management
"""

import yaml
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Union
import os
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SystemConfig:
    """System configuration data class"""
    # Detection settings
    detection_model_path: str = "data/models/yolov8n.pt"
    detection_confidence: float = 0.5
    detection_device: str = "auto"
    
    # OCR settings
    ocr_languages: list = None
    ocr_confidence: float = 0.6
    
    # Tracking settings
    tracking_max_age: int = 30
    tracking_min_hits: int = 3
    tracking_iou_threshold: float = 0.3
    
    # Control settings
    control_num_lanes: int = 8
    control_learning_rate: float = 3e-4
    control_model_path: str = "data/models/ppo_traffic_model.zip"
    
    # Security settings
    security_db_path: str = "data/security_db.sqlite"
    security_email_enabled: bool = False
    security_smtp_server: str = "smtp.gmail.com"
    security_smtp_port: int = 587
    
    # Simulation settings
    simulation_gui: bool = False
    simulation_duration: int = 3600
    simulation_step_length: float = 1.0
    
    # Video settings
    video_width: int = 1920
    video_height: int = 1080
    video_fps: int = 30
    video_display: bool = False
    
    # Processing settings
    processing_num_threads: int = 2
    processing_max_queue_size: int = 10
    
    def __post_init__(self):
        if self.ocr_languages is None:
            self.ocr_languages = ['en']


class ConfigManager:
    """
    Configuration Manager
    
    Handles loading, validation, and management of system configuration
    """
    
    def __init__(self, config_path: str = "config/system_config.yaml"):
        """
        Initialize configuration manager
        
        Args:
            config_path: Path to configuration file
        """
        self.config_path = Path(config_path)
        self.config_data = {}
        self.system_config = SystemConfig()
        
        self._load_config()
        self._validate_config()
        
        logger.info(f"Configuration loaded from {config_path}")
    
    def _load_config(self):
        """Load configuration from file"""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r') as f:
                    if self.config_path.suffix.lower() == '.yaml' or self.config_path.suffix.lower() == '.yml':
                        self.config_data = yaml.safe_load(f)
                    elif self.config_path.suffix.lower() == '.json':
                        self.config_data = json.load(f)
                    else:
                        logger.warning(f"Unsupported config file format: {self.config_path.suffix}")
                        self.config_data = {}
            else:
                logger.warning(f"Config file not found: {self.config_path}")
                self._create_default_config()
                
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            self.config_data = {}
    
    def _create_default_config(self):
        """Create default configuration file"""
        default_config = {
            'detection': {
                'model_path': 'data/models/yolov8n.pt',
                'confidence_threshold': 0.5,
                'nms_threshold': 0.45,
                'input_size': 640,
                'device': 'auto'
            },
            'ocr': {
                'languages': ['en'],
                'confidence_threshold': 0.6,
                'gpu': True
            },
            'tracking': {
                'max_age': 30,
                'min_hits': 3,
                'iou_threshold': 0.3
            },
            'control': {
                'num_lanes': 8,
                'learning_rate': 0.0003,
                'model_path': 'data/models/ppo_traffic_model.zip',
                'reward_weights': {
                    'throughput': 0.3,
                    'waiting_time': 0.4,
                    'fairness': 0.2,
                    'emissions': 0.1
                }
            },
            'security': {
                'db_path': 'data/security_db.sqlite',
                'notifications': {
                    'email': {
                        'enabled': False,
                        'smtp_server': 'smtp.gmail.com',
                        'smtp_port': 587,
                        'from': 'traffic-system@example.com',
                        'to': ['security@police.gov.in'],
                        'username': 'your-email@gmail.com',
                        'password': 'your-app-password'
                    },
                    'webhook': {
                        'enabled': False,
                        'url': 'https://your-webhook-url.com/alerts',
                        'headers': {
                            'Authorization': 'Bearer your-token'
                        }
                    }
                }
            },
            'simulation': {
                'gui': False,
                'duration': 3600,
                'step_length': 1.0,
                'network_file': None,
                'route_file': None
            },
            'video': {
                'width': 1920,
                'height': 1080,
                'fps': 30,
                'display': False
            },
            'processing': {
                'num_threads': 2,
                'max_queue_size': 10
            },
            'logging': {
                'level': 'INFO',
                'file': 'logs/traffic_control.log',
                'max_size': '10MB',
                'backup_count': 5
            },
            'database': {
                'url': 'sqlite:///data/traffic_control.db',
                'echo': False
            },
            'api': {
                'host': '0.0.0.0',
                'port': 8502,
                'debug': False
            },
            'dashboard': {
                'host': '0.0.0.0',
                'port': 8501,
                'auto_refresh': True,
                'refresh_interval': 5
            }
        }
        
        # Create config directory
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save default config
        with open(self.config_path, 'w') as f:
            yaml.dump(default_config, f, default_flow_style=False, indent=2)
        
        self.config_data = default_config
        logger.info(f"Created default configuration file: {self.config_path}")
    
    def _validate_config(self):
        """Validate configuration parameters"""
        try:
            # Validate detection settings
            detection_config = self.config_data.get('detection', {})
            if detection_config.get('confidence_threshold', 0.5) < 0 or detection_config.get('confidence_threshold', 0.5) > 1:
                logger.warning("Invalid detection confidence threshold, using default 0.5")
                detection_config['confidence_threshold'] = 0.5
            
            # Validate paths
            model_path = detection_config.get('model_path', 'data/models/yolov8n.pt')
            if model_path and not Path(model_path).exists() and not model_path.startswith('http'):
                logger.warning(f"Detection model not found: {model_path}")
            
            # Validate control settings
            control_config = self.config_data.get('control', {})
            if control_config.get('num_lanes', 8) <= 0:
                logger.warning("Invalid number of lanes, using default 8")
                control_config['num_lanes'] = 8
            
            # Validate video settings
            video_config = self.config_data.get('video', {})
            if video_config.get('fps', 30) <= 0:
                logger.warning("Invalid video FPS, using default 30")
                video_config['fps'] = 30
            
            logger.info("Configuration validation completed")
            
        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation
        
        Args:
            key: Configuration key (e.g., 'detection.confidence_threshold')
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        try:
            keys = key.split('.')
            value = self.config_data
            
            for k in keys:
                if isinstance(value, dict) and k in value:
                    value = value[k]
                else:
                    return default
            
            # Handle environment variable overrides
            env_key = key.upper().replace('.', '_')
            if env_key in os.environ:
                env_value = os.environ[env_key]
                
                # Try to convert to appropriate type
                if isinstance(value, bool):
                    return env_value.lower() in ('true', '1', 'yes', 'on')
                elif isinstance(value, int):
                    try:
                        return int(env_value)
                    except ValueError:
                        logger.warning(f"Invalid integer value for {env_key}: {env_value}")
                        return value
                elif isinstance(value, float):
                    try:
                        return float(env_value)
                    except ValueError:
                        logger.warning(f"Invalid float value for {env_key}: {env_value}")
                        return value
                else:
                    return env_value
            
            return value
            
        except Exception as e:
            logger.error(f"Error getting config value for key '{key}': {e}")
            return default
    
    def set(self, key: str, value: Any):
        """
        Set configuration value using dot notation
        
        Args:
            key: Configuration key
            value: Value to set
        """
        try:
            keys = key.split('.')
            config = self.config_data
            
            for k in keys[:-1]:
                if k not in config:
                    config[k] = {}
                config = config[k]
            
            config[keys[-1]] = value
            
        except Exception as e:
            logger.error(f"Error setting config value for key '{key}': {e}")
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """
        Get entire configuration section
        
        Args:
            section: Section name
            
        Returns:
            Configuration section
        """
        return self.config_data.get(section, {})
    
    def save(self, config_path: Optional[str] = None):
        """
        Save configuration to file
        
        Args:
            config_path: Optional path to save config (uses current path if None)
        """
        try:
            save_path = Path(config_path) if config_path else self.config_path
            
            with open(save_path, 'w') as f:
                if save_path.suffix.lower() in ['.yaml', '.yml']:
                    yaml.dump(self.config_data, f, default_flow_style=False, indent=2)
                elif save_path.suffix.lower() == '.json':
                    json.dump(self.config_data, f, indent=2)
                else:
                    logger.error(f"Unsupported config file format: {save_path.suffix}")
                    return
            
            logger.info(f"Configuration saved to {save_path}")
            
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
    
    def reload(self):
        """Reload configuration from file"""
        self._load_config()
        self._validate_config()
        logger.info("Configuration reloaded")
    
    def get_system_config(self) -> SystemConfig:
        """Get system configuration as dataclass"""
        return SystemConfig(
            detection_model_path=self.get('detection.model_path', 'data/models/yolov8n.pt'),
            detection_confidence=self.get('detection.confidence_threshold', 0.5),
            detection_device=self.get('detection.device', 'auto'),
            ocr_languages=self.get('ocr.languages', ['en']),
            ocr_confidence=self.get('ocr.confidence_threshold', 0.6),
            tracking_max_age=self.get('tracking.max_age', 30),
            tracking_min_hits=self.get('tracking.min_hits', 3),
            tracking_iou_threshold=self.get('tracking.iou_threshold', 0.3),
            control_num_lanes=self.get('control.num_lanes', 8),
            control_learning_rate=self.get('control.learning_rate', 3e-4),
            control_model_path=self.get('control.model_path', 'data/models/ppo_traffic_model.zip'),
            security_db_path=self.get('security.db_path', 'data/security_db.sqlite'),
            security_email_enabled=self.get('security.notifications.email.enabled', False),
            security_smtp_server=self.get('security.notifications.email.smtp_server', 'smtp.gmail.com'),
            security_smtp_port=self.get('security.notifications.email.smtp_port', 587),
            simulation_gui=self.get('simulation.gui', False),
            simulation_duration=self.get('simulation.duration', 3600),
            simulation_step_length=self.get('simulation.step_length', 1.0),
            video_width=self.get('video.width', 1920),
            video_height=self.get('video.height', 1080),
            video_fps=self.get('video.fps', 30),
            video_display=self.get('video.display', False),
            processing_num_threads=self.get('processing.num_threads', 2),
            processing_max_queue_size=self.get('processing.max_queue_size', 10)
        )
    
    def __str__(self) -> str:
        """String representation of configuration"""
        return f"ConfigManager(config_path={self.config_path})"
    
    def __repr__(self) -> str:
        """Detailed string representation"""
        return f"ConfigManager(config_path={self.config_path}, sections={list(self.config_data.keys())})"


def main():
    """Test configuration manager"""
    config = ConfigManager("config/system_config.yaml")
    
    print("Configuration sections:", list(config.config_data.keys()))
    print("Detection confidence:", config.get('detection.confidence_threshold'))
    print("Control learning rate:", config.get('control.learning_rate'))
    print("Video display:", config.get('video.display'))
    
    # Test environment variable override
    os.environ['DETECTION_CONFIDENCE_THRESHOLD'] = '0.7'
    print("Detection confidence (with env override):", config.get('detection.confidence_threshold'))
    
    # Get system config
    sys_config = config.get_system_config()
    print("System config:", sys_config)


if __name__ == "__main__":
    main()