"""
Configuration Manager for Parchís Pathfinding.

Handles loading and saving of settings and calibration data.
"""

import os
import yaml
from typing import Any, Optional, Dict
import logging
import shutil

logger = logging.getLogger(__name__)


class ConfigManager:
    """
    Manages configuration files for Parchís Pathfinding.
    
    Configuration files:
    - settings.yaml: Runtime settings (ADB, overlay, debug)
    - calibration.yaml: Calibrated values (colors, positions)
    """
    
    DEFAULT_SETTINGS = {
        'adb': {
            'host': '127.0.0.1',
            'port': 5555,
            'timeout': 10,
            'retry_count': 3,
        },
        'overlay': {
            'enabled': True,
            'opacity': 0.3,
            'highlight_color': 'green',
            'show_message': True,
        },
        'detection': {
            'min_piece_area': 500,
            'confidence_threshold': 0.7,
            'capture_latency_ms': 500,
        },
        'pathfinding': {
            'show_top_n': 3,
            'auto_detect_dice': False,
        },
        'debug': {
            'enabled': False,
            'save_screenshots': False,
            'log_level': 'INFO',
        }
    }
    
    DEFAULT_CALIBRATION = {
        'corners': {
            'top_left': [0.1, 0.1],
            'top_right': [0.9, 0.1],
            'bottom_left': [0.1, 0.9],
            'bottom_right': [0.9, 0.9],
        },
        'hsv_ranges': {
            'blue': {'lower': [100, 150, 50], 'upper': [140, 255, 255]},
            'yellow': {'lower': [20, 150, 150], 'upper': [30, 255, 255]},
            'green': {'lower': [40, 100, 50], 'upper': [80, 255, 255]},
            'red': {'lower': [0, 150, 100], 'upper': [10, 255, 255]},
        },
        'offset': [0, 0],
        'safe_zones': [0, 8, 13, 21, 26, 34, 39, 47],
        'start_positions': {
            'blue': 0,
            'yellow': 13,
            'green': 26,
            'red': 39,
        },
    }
    
    def __init__(self, config_dir: Optional[str] = None):
        """
        Initialize configuration manager.
        
        Args:
            config_dir: Configuration directory path. Defaults to ./config
        """
        if config_dir:
            self.config_dir = config_dir
        else:
            # Default to config directory relative to this file
            self.config_dir = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), 
                'config'
            )
        
        self._ensure_config_dir()
        
        self.settings = None
        self.calibration = None
        
        # Load on init
        self.load_settings()
        self.load_calibration()
    
    def _ensure_config_dir(self):
        """Ensure config directory exists."""
        os.makedirs(self.config_dir, exist_ok=True)
        
        # Create default files if they don't exist
        settings_path = os.path.join(self.config_dir, 'settings.yaml')
        calibration_path = os.path.join(self.config_dir, 'calibration.yaml')
        
        if not os.path.exists(settings_path):
            self._save_yaml(settings_path, self.DEFAULT_SETTINGS)
            logger.info(f"Created default settings: {settings_path}")
        
        if not os.path.exists(calibration_path):
            self._save_yaml(calibration_path, self.DEFAULT_CALIBRATION)
            logger.info(f"Created default calibration: {calibration_path}")
    
    def _load_yaml(self, path: str) -> dict:
        """Load YAML file."""
        try:
            with open(path, 'r') as f:
                return yaml.safe_load(f) or {}
        except FileNotFoundError:
            return {}
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML {path}: {e}")
            # Return empty dict - will regenerate on next save
            return {}
        except Exception as e:
            logger.error(f"Unexpected error loading {path}: {e}")
            return {}
    
    def _save_yaml(self, path: str, data: dict) -> bool:
        """Save YAML file."""
        try:
            # Convert tuples to lists for YAML compatibility
            data = self._convert_tuples_to_lists(data)
            
            with open(path, 'w') as f:
                yaml.dump(data, f, default_flow_style=False)
            return True
        except Exception as e:
            logger.error(f"Error saving YAML {path}: {e}")
            return False
    
    def _convert_tuples_to_lists(self, obj):
        """Recursively convert tuples to lists for YAML compatibility."""
        if isinstance(obj, tuple):
            return list(obj)
        elif isinstance(obj, dict):
            return {k: self._convert_tuples_to_lists(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_tuples_to_lists(item) for item in obj]
        return obj
    
    def load_settings(self) -> dict:
        """Load settings from file."""
        settings_path = os.path.join(self.config_dir, 'settings.yaml')
        self.settings = self._load_yaml(settings_path)
        
        # Merge with defaults
        self._merge_with_defaults(self.settings, self.DEFAULT_SETTINGS)
        
        logger.info(f"Loaded settings from {settings_path}")
        return self.settings
    
    def load_calibration(self) -> dict:
        """Load calibration from file."""
        calibration_path = os.path.join(self.config_dir, 'calibration.yaml')
        
        # Try to load, if fails delete corrupted file and use defaults
        try:
            self.calibration = self._load_yaml(calibration_path)
        except Exception as e:
            logger.error(f"Error parsing calibration, regenerating: {e}")
            if os.path.exists(calibration_path):
                os.remove(calibration_path)
            self.calibration = {}
        
        # Merge with defaults
        self._merge_with_defaults(self.calibration, self.DEFAULT_CALIBRATION)
        
        logger.info(f"Loaded calibration from {calibration_path}")
        return self.calibration
        
        # Merge with defaults
        self._merge_with_defaults(self.calibration, self.DEFAULT_CALIBRATION)
        
        logger.info(f"Loaded calibration from {calibration_path}")
        return self.calibration
    
    def save_settings(self) -> bool:
        """Save current settings to file."""
        settings_path = os.path.join(self.config_dir, 'settings.yaml')
        return self._save_yaml(settings_path, self.settings)
    
    def save_calibration(self) -> bool:
        """Save current calibration to file."""
        calibration_path = os.path.join(self.config_dir, 'calibration.yaml')
        return self._save_yaml(calibration_path, self.calibration)
    
    def _merge_with_defaults(self, target: dict, defaults: dict):
        """Merge target dict with defaults (recursive)."""
        for key, value in defaults.items():
            if key not in target:
                target[key] = value
            elif isinstance(value, dict) and isinstance(target[key], dict):
                self._merge_with_defaults(target[key], value)
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get setting value using dot notation.
        
        Args:
            key: Dot-separated key (e.g., 'adb.host')
            default: Default value if key not found
            
        Returns:
            Setting value or default
        """
        if not self.settings:
            return default
        
        keys = key.split('.')
        value = self.settings
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any) -> bool:
        """
        Set setting value using dot notation.
        
        Args:
            key: Dot-separated key (e.g., 'adb.host')
            value: Value to set
            
        Returns:
            True if successful
        """
        if not self.settings:
            self.settings = {}
        
        keys = key.split('.')
        target = self.settings
        
        for k in keys[:-1]:
            if k not in target:
                target[k] = {}
            target = target[k]
        
        target[keys[-1]] = value
        return self.save_settings()
    
    def get_calibration_value(self, key: str, default: Any = None) -> Any:
        """Get calibration value using dot notation."""
        if not self.calibration:
            return default
        
        keys = key.split('.')
        value = self.calibration
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set_calibration_value(self, key: str, value: Any) -> bool:
        """Set calibration value using dot notation."""
        if not self.calibration:
            self.calibration = {}
        
        keys = key.split('.')
        target = self.calibration
        
        for k in keys[:-1]:
            if k not in target:
                target[k] = {}
            target = target[k]
        
        target[keys[-1]] = value
        return self.save_calibration()
    
    def update_calibration(self, updates: dict) -> bool:
        """Update calibration with new values."""
        self._merge_with_defaults(self.calibration, updates)
        return self.save_calibration()
    
    def reset_to_defaults(self, config_type: str = 'both') -> bool:
        """
        Reset configuration to defaults.
        
        Args:
            config_type: 'settings', 'calibration', or 'both'
        """
        success = True
        
        if config_type in ('settings', 'both'):
            settings_path = os.path.join(self.config_dir, 'settings.yaml')
            success = success and self._save_yaml(settings_path, self.DEFAULT_SETTINGS)
            self.settings = self.DEFAULT_SETTINGS.copy()
        
        if config_type in ('calibration', 'both'):
            calibration_path = os.path.join(self.config_dir, 'calibration.yaml')
            success = success and self._save_yaml(calibration_path, self.DEFAULT_CALIBRATION)
            self.calibration = self.DEFAULT_CALIBRATION.copy()
        
        return success
    
    def get_adb_config(self) -> dict:
        """Get ADB configuration."""
        return self.get('adb', {})
    
    def get_overlay_config(self) -> dict:
        """Get overlay configuration."""
        return self.get('overlay', {})
    
    def get_detection_config(self) -> dict:
        """Get detection configuration."""
        return self.get('detection', {})
    
    def get_debug_config(self) -> dict:
        """Get debug configuration."""
        return self.get('debug', {})
    
    def get_hsv_ranges(self) -> dict:
        """Get HSV color ranges from calibration."""
        return self.calibration.get('hsv_ranges', {})
    
    def get_corners(self) -> dict:
        """Get board corners from calibration."""
        return self.calibration.get('corners', {})


# Convenience function
def create_config_manager(config_dir: Optional[str] = None) -> ConfigManager:
    """Create a ConfigManager instance."""
    return ConfigManager(config_dir=config_dir)