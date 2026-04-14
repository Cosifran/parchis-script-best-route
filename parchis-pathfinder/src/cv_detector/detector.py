"""
Board Detector for Parchís Pathfinding.

Handles computer vision detection of board state and pieces.
"""

import cv2
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class PlayerColor(Enum):
    """Parchís player colors."""
    BLUE = "blue"
    YELLOW = "yellow"
    GREEN = "green"
    RED = "red"


@dataclass
class PiecePosition:
    """Represents a piece position on the board."""
    player: PlayerColor
    piece_id: int  # 0-3 for each player's pieces
    position: int  # Board index (0-67)
    in_base: bool = False
    in_goal: bool = False
    confidence: float = 1.0


@dataclass
class PlayerState:
    """State of all pieces for one player."""
    color: PlayerColor
    pieces: List[PiecePosition] = field(default_factory=list)
    
    def get_active_pieces(self) -> List[PiecePosition]:
        """Get pieces that are on the board (not in base)."""
        return [p for p in self.pieces if not p.in_base]
    
    def get_pieces_in_base(self) -> List[PiecePosition]:
        """Get pieces still in base."""
        return [p for p in self.pieces if p.in_base]
    
    def get_pieces_in_goal(self) -> List[PiecePosition]:
        """Get pieces that have reached the goal."""
        return [p for p in self.pieces if p.in_goal]


@dataclass
class BoardState:
    """Complete state of the Parchís board."""
    width: int
    height: int
    players: Dict[PlayerColor, PlayerState] = field(default_factory=dict)
    confidence: float = 0.0
    calibration_offset: Tuple[int, int] = (0, 0)
    
    def get_player(self, color: PlayerColor) -> PlayerState:
        """Get state for a specific player."""
        return self.players.get(color)
    
    def get_all_pieces(self) -> List[PiecePosition]:
        """Get all pieces on the board."""
        all_pieces = []
        for player_state in self.players.values():
            all_pieces.extend(player_state.pieces)
        return all_pieces


class BoardDetector:
    """
    Detects Parchís board state using computer vision.
    
    Uses HSV color segmentation to identify pieces and their positions.
    """
    
    # Default HSV ranges for each player color (can be calibrated)
    DEFAULT_HSV_RANGES = {
        PlayerColor.BLUE: {
            'lower': (100, 150, 50),
            'upper': (140, 255, 255)
        },
        PlayerColor.YELLOW: {
            'lower': (20, 150, 150),
            'upper': (30, 255, 255)
        },
        PlayerColor.GREEN: {
            'lower': (40, 100, 50),
            'upper': (80, 255, 255)
        },
        PlayerColor.RED: {
            'lower': (0, 150, 100),
            'upper': (10, 255, 255)
        },
    }
    
    # Board configuration
    # Board has 68 positions: 52 path squares + 16 goal squares (4 per player)
    # Path: 0-51 (circular track)
    # Goals: 52-55 (blue), 56-59 (yellow), 60-63 (green), 64-67 (red)
    
    def __init__(self, hsv_ranges: Optional[Dict[PlayerColor, dict]] = None,
                 calibration: Optional[dict] = None):
        """
        Initialize board detector.
        
        Args:
            hsv_ranges: Custom HSV ranges for color detection
            calibration: Calibration data with board corners and offsets
        """
        # If hsv_ranges uses string keys, convert to PlayerColor keys
        if hsv_ranges and hsv_ranges:
            first_key = list(hsv_ranges.keys())[0]
            if isinstance(first_key, str):
                hsv_ranges = self._convert_string_keys_to_enum(hsv_ranges)
        
        self.hsv_ranges = hsv_ranges or self.DEFAULT_HSV_RANGES
        self.calibration = calibration or {}
        
        # Board mapping: relative positions (0.0-1.0) for each cell
        self._init_board_mapping()
    
    def _convert_string_keys_to_enum(self, hsv_ranges: dict) -> Dict[PlayerColor, dict]:
        """Convert string keys to PlayerColor enum keys."""
        result = {}
        for key, value in hsv_ranges.items():
            try:
                color = PlayerColor(key)
                result[color] = value
            except ValueError:
                # Skip unknown colors
                pass
        return result
    
    def _init_board_mapping(self):
        """Initialize board position mapping."""
        # Define relative positions for each cell on the board
        # This is a simplified mapping - calibration will adjust it
        self.board_positions = []
        
        # For now, we'll use a grid-based approach that can be calibrated
        pass
    
    def detect(self, screenshot: np.ndarray, 
               dice_value: Optional[int] = None) -> BoardState:
        """
        Detect board state from screenshot.
        
        Args:
            screenshot: Screenshot from emulator (BGR format)
            dice_value: Current dice roll (optional, for context)
            
        Returns:
            Detected BoardState
        """
        height, width = screenshot.shape[:2]
        
        # Create default player states
        players = {
            PlayerColor.BLUE: PlayerState(color=PlayerColor.BLUE),
            PlayerColor.YELLOW: PlayerState(color=PlayerColor.YELLOW),
            PlayerColor.GREEN: PlayerState(color=PlayerColor.GREEN),
            PlayerColor.RED: PlayerState(color=PlayerColor.RED),
        }
        
        # Apply color segmentation for each player
        detected_pieces = []
        
        for color, hsv_range in self.hsv_ranges.items():
            pieces = self._detect_color_pieces(
                screenshot, color, hsv_range, width, height
            )
            detected_pieces.extend(pieces)
            players[color].pieces = pieces
        
        # Calculate confidence based on detection quality
        confidence = self._calculate_confidence(detected_pieces, players)
        
        # Get calibration offset if available
        offset = self.calibration.get('offset', (0, 0))
        
        return BoardState(
            width=width,
            height=height,
            players=players,
            confidence=confidence,
            calibration_offset=offset
        )
    
    def _detect_color_pieces(self, screenshot: np.ndarray, 
                           color: PlayerColor, 
                           hsv_range: dict,
                           img_width: int, 
                           img_height: int) -> List[PiecePosition]:
        """
        Detect pieces of a specific color using HSV thresholding.
        
        Args:
            screenshot: Input image
            color: Player color to detect
            hsv_range: HSV lower and upper bounds
            img_width: Image width
            img_height: Image height
            
        Returns:
            List of detected PiecePosition objects
        """
        # Convert to HSV
        hsv = cv2.cvtColor(screenshot, cv2.COLOR_BGR2HSV)
        
        # Apply color threshold
        lower = np.array(hsv_range['lower'])
        upper = np.array(hsv_range['upper'])
        mask = cv2.inRange(hsv, lower, upper)
        
        # Apply morphological operations to clean up
        kernel = np.ones((3, 3), np.uint8)
        mask = cv2.erode(mask, kernel, iterations=1)
        mask = cv2.dilate(mask, kernel, iterations=2)
        
        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, 
                                       cv2.CHAIN_APPROX_SIMPLE)
        
        pieces = []
        for idx, contour in enumerate(contours):
            # Filter by area to remove noise
            area = cv2.contourArea(contour)
            if area < 500:  # Minimum area threshold
                continue
            
            # Get centroid
            M = cv2.moments(contour)
            if M["m00"] == 0:
                continue
            cx = int(M["m10"] / M["m00"])
            cy = int(M["m01"] / M["m00"])
            
            # Map to board position
            position = self._map_to_board_position(
                cx, cy, img_width, img_height
            )
            
            # Determine if piece is in base or goal
            in_base = position is None or position < 0
            in_goal = position is not None and position >= 52
            
            piece = PiecePosition(
                player=color,
                piece_id=idx,
                position=position if position is not None else -1,
                in_base=in_base,
                in_goal=in_goal,
                confidence=min(1.0, area / 5000)  # Confidence based on area
            )
            pieces.append(piece)
        
        return pieces
    
    def _map_to_board_position(self, x: int, y: int, 
                               img_width: int, img_height: int) -> Optional[int]:
        """
        Map pixel coordinates to board position.
        
        Args:
            x: X pixel coordinate
            y: Y pixel coordinate
            img_width: Image width
            img_height: Image height
            
        Returns:
            Board position index (0-67) or None if not on path
        """
        # Use calibration if available
        corners = self.calibration.get('corners', {})
        
        if not corners:
            # Fallback: simple grid-based mapping
            # This is a simplified version - calibration will improve accuracy
            return self._simple_position_mapping(x, y, img_width, img_height)
        
        # Use calibrated corners for mapping
        return self._calibrated_position_mapping(x, y, corners, img_width, img_height)
    
    def _simple_position_mapping(self, x: int, y: int,
                                img_width: int, img_height: int) -> Optional[int]:
        """Simple position mapping without calibration."""
        # Normalize coordinates
        nx = x / img_width
        ny = y / img_height
        
        # Parchís board has specific zones
        # This is a placeholder - calibration tool will provide proper mapping
        # For now, return a rough estimate based on board quadrants
        
        # Define approximate zones (simplified)
        if nx < 0.25 and ny < 0.25:
            # Top-left: Blue base/corner
            return -1  # In base
        elif nx > 0.75 and ny < 0.25:
            # Top-right: Yellow base
            return -1
        elif nx < 0.25 and ny > 0.75:
            # Bottom-left: Green base
            return -1
        elif nx > 0.75 and ny > 0.75:
            # Bottom-right: Red base
            return -1
        else:
            # On the path - simplified mapping
            # This needs calibration for accurate results
            return int((nx + ny) * 25) % 52  # Rough approximation
    
    def _calibrated_position_mapping(self, x: int, y: int,
                                     corners: dict,
                                     img_width: int, img_height: int) -> Optional[int]:
        """Position mapping using calibrated corners."""
        # This would use perspective transform with the calibrated corners
        # Placeholder implementation
        return self._simple_position_mapping(x, y, img_width, img_height)
    
    def _calculate_confidence(self, pieces: List[PiecePosition],
                             players: Dict[PlayerColor, PlayerState]) -> float:
        """Calculate detection confidence score."""
        if not players:
            return 0.0
        
        total_pieces = sum(len(p.pieces) for p in players.values())
        
        if total_pieces == 0:
            return 0.0
        
        # Confidence based on expected pieces vs detected
        # Expected: 4 pieces per player = 16 total
        expected = 16
        if total_pieces < expected:
            return max(0.0, total_pieces / expected)
        
        return 1.0
    
    def update_calibration(self, calibration: dict) -> None:
        """Update detection calibration."""
        self.calibration = calibration
        
        # Update HSV ranges if provided
        if 'hsv_ranges' in calibration:
            self.hsv_ranges = calibration['hsv_ranges']
    
    def get_safe_zones(self) -> List[int]:
        """Get list of safe zone positions on the board."""
        # Safe zones: start positions (after leaving base)
        # and marked safe squares in the path
        return [0, 8, 13, 21, 26, 34, 39, 47]  # Approximate - needs calibration
    
    def get_goal_zone(self, color: PlayerColor) -> List[int]:
        """Get goal zone positions for a specific color."""
        goal_ranges = {
            PlayerColor.BLUE: range(52, 56),
            PlayerColor.YELLOW: range(56, 60),
            PlayerColor.GREEN: range(60, 64),
            PlayerColor.RED: range(64, 68),
        }
        return list(goal_ranges.get(color, []))


# Helper functions for color conversion and processing
def enhance_image_for_detection(image: np.ndarray) -> np.ndarray:
    """Apply preprocessing to enhance piece detection."""
    # Apply CLAHE for better color contrast
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    
    # Apply to each channel
    result = np.zeros_like(image)
    for i in range(image.shape[2]):
        result[:, :, i] = clahe.apply(image[:, :, i])
    
    return result