"""
ADB Connector for Parchís Pathfinding.

Handles connection to Android emulator via ADB and screenshot capture.
"""

import subprocess
import time
import numpy as np
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class ADBConnectionError(Exception):
    """Raised when ADB connection fails."""
    pass


class ADBConnector:
    """
    Manages ADB connection to Android emulator.
    
    Default connection: 127.0.0.1:5555 (localhost:5555)
    """
    
    def __init__(self, host: str = "127.0.0.1", port: int = 5555):
        """
        Initialize ADB connector.
        
        Args:
            host: Emulator host address
            port: Emulator ADB port
        """
        self.host = host
        self.port = port
        self._connected = False
        self._device_serial = f"{host}:{port}"
    
    def connect(self, retry: int = 3, delay: float = 1.0) -> bool:
        """
        Connect to the emulator via ADB.
        
        Args:
            retry: Number of connection attempts
            delay: Delay between retries (seconds)
            
        Returns:
            True if connected successfully
            
        Raises:
            ADBConnectionError: If connection fails after all retries
        """
        for attempt in range(retry):
            try:
                # Check if adb is available
                result = subprocess.run(
                    ["adb", "version"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode != 0:
                    raise ADBConnectionError("ADB not found in system")
                
                # Connect to emulator
                result = subprocess.run(
                    ["adb", "connect", self._device_serial],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode == 0 and "connected" in result.stdout.lower():
                    self._connected = True
                    logger.info(f"Connected to {self._device_serial}")
                    return True
                    
            except subprocess.TimeoutExpired:
                logger.warning(f"ADB connect attempt {attempt + 1} timed out")
            except FileNotFoundError:
                raise ADBConnectionError("ADB command not found. Install Android SDK platform-tools.")
            
            if attempt < retry - 1:
                time.sleep(delay)
                delay *= 2  # Exponential backoff
        
        raise ADBConnectionError(f"Failed to connect to {self._device_serial} after {retry} attempts")
    
    def disconnect(self) -> None:
        """Disconnect from the emulator."""
        try:
            subprocess.run(
                ["adb", "-s", self._device_serial, "disconnect"],
                capture_output=True,
                timeout=5
            )
        except Exception as e:
            logger.warning(f"Error disconnecting: {e}")
        finally:
            self._connected = False
    
    def is_connected(self) -> bool:
        """Check if currently connected to emulator."""
        if not self._connected:
            return False
        
        # Verify connection is still alive
        try:
            result = subprocess.run(
                ["adb", "-s", self._device_serial, "get-state"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0 and "device" in result.stdout.lower()
        except Exception:
            self._connected = False
            return False
    
    def get_screenshot(self) -> np.ndarray:
        """
        Capture screenshot from emulator.
        
        Returns:
            Screenshot as NumPy array (BGR format)
            
        Raises:
            ADBConnectionError: If not connected or capture fails
        """
        if not self.is_connected():
            raise ADBConnectionError("Not connected to emulator")
        
        try:
            # Use exec-out for streaming capture (faster, no temp files)
            process = subprocess.Popen(
                ["adb", "-s", self._device_serial, "exec-out", "screencap", "-p"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            stdout, stderr = process.communicate(timeout=10)
            
            if process.returncode != 0:
                raise ADBConnectionError(f"Screenshot failed: {stderr.decode()}")
            
            # Decode PNG from memory
            import io
            from PIL import Image
            
            image = Image.open(io.BytesIO(stdout))
            
            # Convert to BGR NumPy array (OpenCV format)
            screenshot = np.array(image)
            
            # Handle RGBA to BGR conversion if needed
            if screenshot.shape[2] == 4:
                screenshot = cv2.cvtColor(screenshot, cv2.COLOR_RGBA2BGR)
            elif screenshot.shape[2] == 3:
                screenshot = cv2.cvtColor(screenshot, cv2.COLOR_RGB2BGR)
            
            logger.debug(f"Screenshot captured: {screenshot.shape}")
            return screenshot
            
        except subprocess.TimeoutExpired:
            raise ADBConnectionError("Screenshot capture timed out")
        except Exception as e:
            raise ADBConnectionError(f"Screenshot capture failed: {e}")
    
    def get_resolution(self) -> Tuple[int, int]:
        """
        Get emulator screen resolution.
        
        Returns:
            Tuple of (width, height) in pixels
            
        Raises:
            ADBConnectionError: If not connected or retrieval fails
        """
        if not self.is_connected():
            raise ADBConnectionError("Not connected to emulator")
        
        try:
            result = subprocess.run(
                ["adb", "-s", self._device_serial, "shell", "dumpsys", "window", "windows"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            # Parse resolution from output
            for line in result.stdout.split('\n'):
                if "mSurface" in line and "BufferQueue" in line:
                    # Try to extract dimensions
                    import re
                    match = re.search(r'(\d+)x(\d+)', line)
                    if match:
                        return (int(match.group(1)), int(match.group(2)))
            
            # Fallback: use wm size
            result = subprocess.run(
                ["adb", "-s", self._device_serial, "shell", "wm", "size"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            match = re.search(r'(\d+)x(\d+)', result.stdout)
            if match:
                return (int(match.group(1)), int(match.group(2)))
                
            raise ADBConnectionError("Could not determine screen resolution")
            
        except Exception as e:
            raise ADBConnectionError(f"Failed to get resolution: {e}")
    
    def health_check(self) -> bool:
        """
        Perform health check on connection.
        
        Returns:
            True if connection is healthy
        """
        return self.is_connected()
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()


# Import cv2 at module level for color conversion
import cv2