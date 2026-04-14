# Design: parchis-pathfinder

## Technical Approach

The Parchís Pathfinder implements a three-stage pipeline: (1) capture the game screen via ADB, (2) detect board state using OpenCV color segmentation, (3) calculate optimal moves with heuristic scoring and render recommendations via X11 overlay. The system uses relative coordinates (0.0-1.0) for board-agnostic calibration and absolute pixels for screen-accurate overlay positioning.

## Architecture Decisions

### Decision: Camera-Based Screen Capture via ADB exec-out

**Choice**: Use `adb exec-out screencap -p` for screenshot capture, piping directly to stdout without intermediate files.

**Alternatives considered**:
- `adb shell screencap /sdcard/screen.png && adb pull` - Requires file cleanup, slower
- `ddms` screen recording - Higher latency, unnecessary complexity
- VNC server on emulator - Adds dependency, security concerns

**Rationale**: The `exec-out` method streams image data directly without touching the device filesystem, providing the lowest latency (<500ms target) and cleanest workflow. No temp files means no cleanup needed.

### Decision: HS VColor Space for Piece Detection

**Choice**: Convert captured BGR image to HSV color space for threshold-based color segmentation.

**Alternatives considered**:
- RGB thresholding - Sensitive to lighting variations
- YCrCb color space - Less intuitive for color tweaking
- LAB color space - Good but less common for OpenCV tutorials

**Rationale**: HSV separates hue (color type) from saturation/value (intensity), making it easier to define color ranges that are robust to lighting variations. The calibration tool can adjust just the hue range without worrying about brightness.

### Decision: Override-Redirect X11 Window for Overlay

**Choice**: Create an override-redirect transparent window using PyGObject and Cairo.

**Alternatives considered**:
- PyQt5/PySide - Larger dependency, overkill for simple overlay
- Xlib directly - More complex API than Cairo
- Composite Manager (ARGB visuals) - Requires desktop environment support

**Rationale**: Override-redirect windows have no decorations and can be positioned anywhere on screen. Cairo provides easy drawing primitives for rectangles and text with alpha blending. This approach works on any X11 environment without requiring a full desktop compositor.

### Decision: Relative Coordinates for Board Calibration

**Choice**: Store board corners and cell positions as relative coordinates (0.0-1.0), converted to absolute pixels at runtime.

**Alternatives considered**:
- Absolute pixel coordinates - Break when resolution changes
- Percentage-based with fixed aspect ratio - Complex calculation
- Template matching for corners - Brittle, depends on board art

**Rationale**: Different emulators have different resolutions. Relative coordinates store the calibration once and adapt to the current emulator resolution at runtime. The resolution is queried from ADB on startup.

### Decision: Enum-Based Player Colors

**Choice**: Use an enum for player colors: RED, GREEN, YELLOW, BLUE.

**Alternatives considered**:
- String literals ("red", "green") - Prone to typos
- Integer constants - Hard to read in debug output

**Rationale**: Enum provides IDE autocomplete, prevent invalid values, and makes the code self-documenting.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                        parchis-pathfinder Architecture                              │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│   Android Emulator                    Host Linux Machine                          │
│   (localhost:5555)                                                                    │
│         │                                                                         │
│         │ adb exec-out screencap -p                                                 │
│         ▼                                                                         │
│  ┌──────────────┐                                                               │
│  │ Framebuffer │────────────────────────────────────────┐                        │
│  └──────────────┘                                        │                        │
│                                                          ▼                        │
│  ┌──────────────────────────────────────────────────────────────────────┐        │
│  │                    ADBConnector                              │        │
│  │  ┌──────────────────────────────────────────────┐   │        │
│  │  │ connect() → is_connected() → disconnect()    │   │        │
│  │  │ get_screenshot() → np.ndarray (BGR)          │   │        │
│  │  │ get_resolution() → (width, height)           │   │        │
│  │  │ health_check() → bool                      │   │        │
│  │  └──────────────────────────────────────────────┘   │        │
│  └──────────────────────────────────────────────────────────────────────┘        │
│                                     │                                           │
│                                     │ screenshot: np.ndarray                    │
│                                     ▼                                           │
│  ┌──────────────────────────────────────────────────────────────────────┐        │
│  │                    BoardDetector                             │        │
│  │  ┌──────────────────────────────────────────────┐   │        │
│  │  │ detect(screenshot) → BoardState              │   │        │
│  │  │   • preprocess() → blur, resize            │   │        │
│  │  │   • color_segmentation() → HSV masks       │   │        │
│  │  │   • find_contours() → piece regions      │   │        │
│  │  │   • map_to_grid() → board positions      │   │        │
│  │  │   • build_matrix() → BoardState         │   │        │
│  │  └──────────────────────────────────────────────┘   │        │
│  └──────────���───────────────────────────────────────────────────────────┘        │
│                                     │                                           │
│                                     │ board_state: BoardState                    │
│                                     ▼                                           │
│  ┌──────────────────────────────────────────────────────────────────────┐        │
│  │                    PathfinderEngine                           │        │
│  │  ┌──────────────────────────────────────────────┐   │        │
│  │  │ calculate_best_move(board_state, color, roll)   │   │        │
│  │  │   • generate_moves() → list[Move]            │   │        │
│  │  │   • score_move() → heuristic total         │   │        │
│  │  │   • rank_moves() → sorted recommendations  │   │        │
│  │  └──────────────────────────────────────────────┘   │        │
│  │                                                              │        │
│  │  Heuristic Scorer:                                                         │
│  │  ┌──────────────────────────────────────────────┐                       │        │
│  │  │ +100 capture | +50 safe | +40 blockade      │                       │        │
│  │  │ +30 enter | +20 goal | -30 exposed       │                       │        │
│  │  │ -20 break_blockade                        │                       │        │
│  │  └──────────────────────────────────────────────┘                       │        │
│  └──────────────────────────────────────────────────────────────────────┘        │
│                                     │                                           │
│                                     │ recommendations: list[MoveRecommendation]          │
│                                     ▼                                           │
│  ┌──────────────────────────────────────────────────────────────────────┐        │
│  │                    OverlayRenderer                            │        │
│  │  ┌──────────────────────────────────────────────┐   │        │
│  │  │ show_recommendation()                       │   │        │
│  │  │   • create_window() → X11 override-redirect│   │        │
│  │  │   • draw_highlight(position, color)        │   │        │
│  │  │   • draw_text(message) → cairo            │   │        │
│  │  │   • apply_alpha_blend()                   │   │        │
│  │  └──────────────────────────────────────────────┘   │        │
│  └────────────────────────────────────────────��─��───────────────────────┘        │
│                                     │                                           │
│                                     │ Transparent overlay window               │
│                                     ▼                                           │
│                      ┌─────────────────────────┐                                   │
│                      │   X11 Display Server   │◀── Emulator overlay              │
│                      │   (transparent window)  │     positioned at (0,0)           │
│                      └─────────────────────────┘                                   │
│                                                                                 │
│  ┌──────────────────────────────────────────────────────────────────────┐        │
│  │                    ConfigManager                              │        │
│  │  ┌──────────────────────────────────────────────┐   │        │
│  │  │ settings.yaml ← Runtime settings                │   │        │
│  │  │ calibration.yaml ← Calibrated values          │   │        │
│  │  │ load() / save() / get()                   │   │        │
│  │  └──────────────────────────────────────────────┘   │        │
│  └──────────────────────────────────────────────────────────────────────┘        │
│                                                                                 │
���─────────────────────────────────────────────────────────────────────────────────────┘
```

## Data Flow

```
Screenshot Capture                    Board Detection                    Move Calculation                    Overlay Display
───────────────                      ───────────────                  ────────────────                   ──────────────

   ADB exec-out              ┌─────► HSV Conversion      ┌─────► Piece Classification  ┌─────► Move Generation    ┌─────► Highlight Rect
   ─────────────────►           │     (BGR→HSV)             │    (color-based)             │   (legal moves only)    │
   np.ndarray                │                           │                            │                         │
   (BGR, HWC)             │                           │                            │                         │
                          │                           │                            │                         │
                          ▼                           ▼                            ▼                         ▼
                    Color Masks              Contour Detection         Board Matrix              Score Heuristics           X11 Window
                    (4 player              (findContours)           (68 cells)              (7 rules)              (Cairo rendering)
                    colors)
                          │                           │                            │                         │
                          │                           │                            │                         │
                          ▼                           ▼                            ▼                         ▼
                    Binary masks           Position Mapping            Player State             Ranked Moves               Semi-transparent
                    for each               to board                 (pieces in               by score                 text + rect
                    player                 indices                  base/board/goal)          (descending)
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `src/__init__.py` | Create | Package marker |
| `src/main.py` | Create | Entry point, main loop, signal handling |
| `src/config/__init__.py` | Create | Config package marker |
| `src/config/config_manager.py` | Create | YAML config loading/saving |
| `src/config/settings.py` | Create | Settings dataclass with defaults |
| `src/adb_connector/__init__.py` | Create | ADB package marker |
| `src/adb_connector/adb_connector.py` | Create | Connection, screenshot, device info |
| `src/cv_detector/__init__.py` | Create | CV detector package marker |
| `src/cv_detector/board_detector.py` | Create | Main detection pipeline |
| `src/cv_detector/color_tracker.py` | Create | HSV color utilities |
| `src/cv_detector/grid_mapper.py` | Create | Pixel to board index mapping |
| `src/pathfinder/__init__.py` | Create | Pathfinding package marker |
| `src/pathfinder/pathfinder_engine.py` | Create | Move calculation |
| `src/pathfinder/move_generator.py` | Create | Valid move generation |
| `src/pathfinder/heuristics.py` | Create | Scoring rules |
| `src/overlay/__init__.py` | Create | Overlay package marker |
| `src/overlay/overlay_renderer.py` | Create | X11 window and drawing |
| `src/overlay/drawing.py` | Create | Cairo drawing utilities |
| `src/calibration/__init__.py` | Create | Calibration package marker |
| `src/calibration/calibration_tool.py` | Create | Tkinter UI for calibration |
| `src/calibration/color_picker.py` | Create | Interactive color sampling |
| `src/state/__init__.py` | Create | State package marker |
| `src/state/models.py` | Create | BoardState, Move, Piece dataclasses |
| `config/settings.yaml` | Create | Default runtime settings |
| `config/calibration.yaml` | Create | Calibrated values (generated) |
| `tests/__init__.py` | Create | Test package marker |
| `tests/test_heuristics.py` | Create | Unit tests for scoring |
| `tests/test_move_generator.py` | Create | Unit tests for move generation |
| `tests/test_board_detector.py` | Create | Unit tests for detection |
| `tests/conftest.py` | Create | Shared fixtures and mocks |
| `tests/fixtures/` | Create | Sample screenshots |
| `requirements.txt` | Create | Python dependencies |

## Interfaces / Contracts

### ADBConnector Interface

```python
# src/adb_connector/adb_connector.py
from dataclasses import dataclass
from typing import Protocol
import numpy as np


class ADBConnector:
    """Manages connection to Android emulator via ADB."""
    
    def __init__(self, host: str = "127.0.0.1", port: int = 5555, timeout: int = 10) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout
        self._connected = False
    
    def connect(self) -> bool:
        """Establish connection to emulator.
        
        Returns:
            True if connection successful, False otherwise.
        """
    
    def disconnect(self) -> None:
        """Close ADB connection cleanly."""
    
    def is_connected(self) -> bool:
        """Check if connection is active.
        
        Returns:
            True if connected, False otherwise.
        """
    
    def get_screenshot(self) -> np.ndarray | None:
        """Capture screenshot as NumPy array.
        
        Returns:
            Image in BGR format (H, W, 3), or None on failure.
        """
    
    def get_screen_resolution(self) -> tuple[int, int] | None:
        """Get device screen resolution.
        
        Returns:
            (width, height) in pixels, or None if unavailable.
        """
    
    def health_check(self) -> bool:
        """Verify connection health, attempt reconnect if needed.
        
        Returns:
            True if healthy or reconnected, False otherwise.
        """
```

### BoardDetector Interface

```python
# src/cv_detector/board_detector.py
from dataclasses import dataclass
from enum import Enum
import numpy as np


class PlayerColor(Enum):
    RED = "red"
    GREEN = "green"
    YELLOW = "yellow"
    BLUE = "blue"


@dataclass
class CalibrationData:
    """Calibration parameters for a specific emulator."""
    board_corners: dict[str, tuple[float, float]]  # relative (0.0-1.0) coordinates
    color_ranges: dict[PlayerColor, tuple[tuple[int, int, int], tuple[int, int, int]]]  # HSV lower, upper
    safe_zones: dict[PlayerColor, list[int]]  # board indices
    goal_zone: dict[PlayerColor, list[int]]  # goal indices


@dataclass
class PiecePosition:
    """A piece's position on the board."""
    piece_id: int  # 0-3 for each player
    player: PlayerColor
    position_type: str  # 'base', 'board', 'goal'
    board_index: int | None  # 0-51 for path, None for base/goal
    pixel_position: tuple[int, int]  # center (x, y)
    confidence: float  # 0.0-1.0


@dataclass
class PlayerState:
    """State of all pieces for one player."""
    color: PlayerColor
    pieces: list[PiecePosition]
    
    def get_pieces_in_base(self) -> list[PiecePosition]:
        """Return pieces still in base."""
    
    def get_pieces_on_board(self) -> list[PiecePosition]:
        """Return pieces on the path."""
    
    def get_pieces_in_goal(self) -> list[PiecePosition]:
        """Return pieces that reached goal."""
    
    def get_piece_by_id(self, piece_id: int) -> PiecePosition | None:
        """Get piece by ID."""


@dataclass
class BoardState:
    """Complete state of the Parchís board."""
    resolution: tuple[int, int]  # (width, height)
    players: dict[PlayerColor, PlayerState]
    timestamp: float  # Unix timestamp of capture
    confidence: float  # Overall detection confidence
    
    def get_player(self, color: PlayerColor) -> PlayerState:
        """Get state for a specific player."""
    
    def is_occupied(self, player: PlayerColor, board_index: int) -> bool:
        """Check if a board position is occupied by any piece."""
    
    def get_occupant(self, board_index: int) -> tuple[PlayerColor, int] | None:
        """Get (player, piece_id) at position, or None if empty."""
```

### Board Matrix Representation

The board is represented as a 68-cell matrix (indices 0-67):

```
    ╔═══════════════════════════════════════════╗
    ║  BASE  ║  CORRIDOR (52 cells)  ║  GOAL  ║
    ╠═══════╬═══════════════════════════╬═══════╣
    ║ 16-19 ║  0-51 (clockwise)     ║ 64-67 ║  RED
    ╠═══════╬═══════════════════════════╬═══════╣
    ║ 20-23 ║  (see path below)      ║ 60-63 ║ GREEN
    ╠═══════╬═══════════════════════════╬═══════╣
    ║ 24-27 ║  (clockwise path)      ║ 56-59 ║ YELLOW
    ║ 12-15 ║                      ║ 52-55 ║ BLUE
    ╚═══════╩═══════════════════════════╩═══════╝

Path indices by player (13 each, after exiting base):
- RED:    0-12  (exits base at board_index 0)
- GREEN:  13-25  (exits base at board_index 13)
- YELLOW: 26-38  (exits base at board_index 26)
- BLUE:   39-51  (exits base at board_index 39)

Base indices: 16-19 (RED), 20-23 (GREEN), 24-27 (YELLOW), 28-31 (BLUE)
Goal indices: 64-67 (RED), 60-63 (GREEN), 56-59 (YELLOW), 52-55 (BLUE)
```

```python
# Mapping: board_index (0-51 for path) → pixel coordinates
# Derived from board_corners calibration at runtime

BOARD_MATRIX_SHAPE = (1, 68)  # Single row, 68 columns

# Each cell contains:
# - 0: Empty
# - 1-4: Player piece ID + 1 (e.g., 1 = piece 0 of current player)
# - 5+: Stacked pieces (bitmask)
```

### PathfinderEngine Interface

```python
# src/pathfinder/pathfinder_engine.py
from dataclasses import dataclass
from typing import TypedDict
import numpy as np


class MoveType(Enum):
    ENTER = "enter"           # Enter board from base (roll 6 only)
    ADVANCE = "advance"      # Move forward on path
    CAPTURE = "capture"     # Capture opponent piece
    GOAL = "goal"          # Enter goal zone


@dataclass
class Move:
    """A single legal move."""
    piece_id: int
    from_position: int | str  # board_index or 'base'
    to_position: int | str    # board_index, 'goal', or 'enter'
    move_type: MoveType


@dataclass  
class MoveRecommendation:
    """A recommended move with scoring details."""
    move: Move
    score: float
    reasons: list[str]  # Explanation: "Captures opponent", "Enters safe zone", etc.
    alternative_moves: list[Move]  # Other good options if any


class HeuristicResult(TypedDict):
    """Breakdown of heuristic scores."""
    capture: int          # +100 if captures
    safe_zone: int        # +50 if enters safe/corridor/goal
    blockade: int        # +40 if forms 2+ stack
    enter_board: int      # +30 if entering from base
    exact_goal: int       # +20 if exact roll to goal
    exposed: int         # -30 if can be captured
    break_blockade: int  # -20 if breaks existing blockade


class PathfinderEngine:
    """Calculates optimal moves for Parchís."""
    
    def __init__(self, board_state: BoardState) -> None:
        self.board_state = board_state
    
    def generate_moves(self, player: PlayerColor, dice_roll: int) -> list[Move]:
        """Generate all legal moves for given roll.
        
        Args:
            player: The player color to generate moves for
            dice_roll: The dice roll value (1-6)
            
        Returns:
            List of all legal moves for this roll.
        """
    
    def score_move(self, move: Move, player: PlayerColor) -> tuple[float, HeuristicResult]:
        """Score a single move.
        
        Args:
            move: The move to score
            player: The player making the move
            
        Returns:
            Tuple of (total_score, breakdown).
        """
    
    def calculate_best_move(
        self, player: PlayerColor, dice_roll: int
    ) -> list[MoveRecommendation]:
        """Calculate best moves for player with given roll.
        
        Args:
            player: The player color
            dice_roll: The dice roll value (1-6)
            
        Returns:
            Ranked list of best moves (descending by score).
        """
    
    def get_valid_moves(
        self, player: PlayerColor, dice_roll: int
    ) -> list[Move]:
        """Get valid moves without scoring.
        
        Args:
            player: The player color
            dice_roll: The dice roll value
            
        Returns:
            List of all valid (legal) moves.
        """
```

### OverlayRenderer Interface

```python
# src/overlay/overlay_renderer.py
from dataclasses import dataclass


@dataclass
class OverlayConfig:
    """Configuration for overlay rendering."""
    enabled: bool = True
    opacity: float = 0.7
    highlight_color: tuple[int, int, int] = (0, 255, 0)  # RGB
    text_size: int = 16
    show_alternatives: bool = True
    max_alternatives: int = 3
    offset_x: int = 0  # Manual position offset
    offset_y: int = 0


class OverlayRenderer:
    """Renders move recommendations on X11 overlay."""
    
    def __init__(
        self,
        screen_resolution: tuple[int, int],
        config: OverlayConfig | None = None
    ) -> None:
        self.resolution = screen_resolution
        self.config = config or OverlayConfig()
        self._window = None
        self._visible = False
    
    def show_recommendation(
        self,
        recommendation: MoveRecommendation,
        pixel_position: tuple[int, int]
    ) -> None:
        """Display move recommendation at screen position.
        
        Args:
            recommendation: The move recommendation to display
            pixel_position: (x, y) on screen to highlight
        """
    
    def show_alternatives(
        self,
        recommendations: list[MoveRecommendation]
    ) -> None:
        """Display multiple move alternatives.
        
        Args:
            recommendations: List of ranked recommendations
        """
    
    def update_position(self, x: int, y: int) -> None:
        """Update overlay window position.
        
        Args:
            x, y: New window position
        """
    
    def clear(self) -> None:
        """Clear overlay content."""
    
    def close(self) -> None:
        """Destroy overlay window."""
    
    @property
    def is_visible(self) -> bool:
        """Check if overlay is displayed."""
```

### Calibration Data Format

```yaml
# config/calibration.yaml
version: "1.0"
last_calibrated: "2026-04-14T10:30:00Z"

board_corners:
  top_left: [0.15, 0.20]      # relative (x, y) 0.0-1.0
  top_right: [0.85, 0.20]
  bottom_left: [0.15, 0.80]
  bottom_right: [0.85, 0.80]

color_ranges:
  red:
    hsv_lower: [0, 100, 100]    # HSV values
    hsv_upper: [10, 255, 255]
  green:
    hsv_lower: [40, 100, 100]
    hsv_upper: [80, 255, 255]
  yellow:
    hsv_lower: [20, 100, 100]
    hsv_upper: [30, 255, 255]
  blue:
    hsv_lower: [100, 100, 100]
    hsv_upper: [140, 255, 255]

safe_zones:
  red: [0, 8, 13, 21, 26, 34, 39, 47]
  green: [13, 21, 26, 34, 39, 47, 0, 8]
  yellow: [26, 34, 39, 47, 0, 8, 13, 21]
  blue: [39, 47, 0, 8, 13, 21, 26, 34]

goal_indices:
  red: [64, 65, 66, 67]
  green: [60, 61, 62, 63]
  yellow: [56, 57, 58, 59]
  blue: [52, 53, 54, 55]
```

### Settings Data Format

```yaml
# config/settings.yaml
adb:
  host: "127.0.0.1"
  port: 5555
  connection_timeout: 10
  retry_attempts: 3
  retry_delay: 2

overlay:
  enabled: true
  opacity: 0.7
  highlight_color: [0, 255, 0]
  text_size: 16
  show_alternatives: true
  max_alternatives: 3
  offset_x: 0
  offset_y: 0

detection:
  confidence_threshold: 0.7
  min_piece_area: 500
  max_piece_area: 5000

debug:
  enabled: false
  save_screenshots: false
  log_level: "INFO"
  screenshot_dir: "./debug/screenshots"
```

## Error Handling Strategy

### Connection Timeouts

| Error | Detection | Recovery |
|-------|-----------|----------|
| ADB connection refused | `connect()` returns False | Retry with exponential backoff (3 attempts, 2s delay) |
| Screenshot timeout > 1s | Timeout in `get_screenshot()` | Log warning, return None, increment failure counter |
| Device went offline | `health_check()` fails | Attempt `adb reconnect`, then `adb connect` |

```python
def get_screenshot_with_retry(self, max_attempts: int = 3) -> np.ndarray | None:
    """Get screenshot with retry logic."""
    for attempt in range(max_attempts):
        try:
            image = self._exec_out_screencap()
            if image is not None:
                return image
        except subprocess.TimeoutExpired:
            self._logger.warning(f"Screenshot timeout (attempt {attempt + 1}/{max_attempts})")
        except Exception as e:
            self._logger.error(f"Screenshot error: {e}")
    
    self._logger.error("All screenshot attempts failed")
    return None
```

### Invalid Detection Results

| Error | Detection | Recovery |
|-------|-----------|----------|
| No corners detected | `board_corners` all None | Raise `BoardDetectionException`, prompt recalibration |
| Low confidence < 0.5 | Confidence below threshold | Log warning, return partial state, show in overlay |
| No pieces detected at all | All `PlayerState.pieces` empty | Log error, return empty board |
| Invalid color range | HSV values out of bounds | Clamp to valid range, warn |

```python
def detect_with_validation(self, screenshot: np.ndarray) -> BoardState:
    """Detect board with validation."""
    result = self._detect_board(screenshot)
    
    # Validate corners
    if not self._corners_valid(result):
        raise BoardDetectionException(
            "Board corners not detected. Please recalibrate."
        )
    
    # Validate confidence
    if result.confidence < self.min_confidence:
        self._logger.warning(
            f"Low detection confidence: {result.confidence:.2f}"
        )
    
    # Validate piece count
    total_pieces = sum(
        len(ps.pieces) 
        for ps in result.players.values()
    )
    if total_pieces == 0:
        self._logger.error("No pieces detected on board")
    elif total_pieces < 16:  # Expected: 4 players * 4 pieces
        self._logger.warning(f"Only {total_pieces}/16 pieces detected")
    
    return result
```

### Overlay Positioning Failures

| Error | Detection | Recovery |
|-------|-----------|----------|
| X11 not available | `ImportError` for GObject | Log error, disable overlay, continue |
| Window creation failed | `create_window()` returns None | Log error, disable overlay |
| Permission denied | X11 error (BadAccess) | Log error with xhost suggestion |
| Position outside screen | Coordinates > resolution | Clamp to screen bounds |

```python
def __init__(self, resolution: tuple[int, int], config: OverlayConfig | None = None):
    self.resolution = resolution
    self.config = config or OverlayConfig()
    
    try:
        self._display = Xlib.display.Display()
        self._screen = self._display.screen()
        self._window = None
    except ImportError as e:
        self._logger.error(f"X11 not available: {e}. Overlay disabled.")
        self._display = None
    
def _validate_position(self, x: int, y: int) -> tuple[int, int]:
    """Clamp position to valid screen bounds."""
    width, height = self.resolution
    return (
        max(0, min(x, width - 1)),
        max(0, min(y, height - 1))
    )
```

### Edge Case Handling

| Scenario | Detection | Handling |
|----------|-----------|----------|
| No valid moves | `generate_moves()` returns empty | Display "No valid moves for roll {n}" in overlay |
| All pieces in goal | All `pieces_in_goal()` full | Display "All pieces in goal!" in overlay |
| Multiple optimal moves | Top N scores equal | Show top 3 alternatives in overlay |
| Disconnected during detection | `ADBConnector` not connected | Attempt reconnect, then fail gracefully |

```python
def calculate_best_move(self, player: PlayerColor, dice_roll: int) -> list[MoveRecommendation]:
    """Calculate best moves with edge case handling."""
    moves = self.generate_moves(player, dice_roll)
    
    if not moves:
        return []  # No valid moves
    
    if all(pieces.get_pieces_in_goal() for pieces in self.board_state.players[player]):
        # All pieces in goal - game winning position
        pass
    
    # Score and rank moves
    scored = []
    for move in moves:
        score, breakdown = self.score_move(move, player)
        scored.append((move, score, breakdown))
    
    # Sort by score descending
    scored.sort(key=lambda x: x[1], reverse=True)
    
    # Return recommendations
    return self._build_recommendations(scored)
```

## Testing Strategy

### Unit Tests for Pathfinding Heuristics

```python
# tests/test_heuristics.py
import pytest
from src.pathfinder.heuristics import HeuristicScorer


class TestHeuristicScorer:
    """Unit tests for heuristic scoring."""
    
    @pytest.mark.parametrize("roll,expected_score", [
        # Capture: +100
        (6, 100),  # Land on opponent = capture
    ])
    def test_capture_score(self, roll, expected_score):
        """Test capture scoring."""
        scorer = HeuristicScorer()
        board_state = self._create_board_with_opponent_at(12)
        
        move = Move(
            piece_id=0,
            from_position=6,
            to_position=12,
            move_type=MoveType.CAPTURE
        )
        
        score, _ = scorer.score(move, PlayerColor.RED, board_state)
        
        assert score == expected_score
    
    @pytest.mark.parametrize("roll,safe_zone,expected_score", [
        # Safe zone: +50
        (3, True, 50),
        (6, True, 50),
    ])
    def test_safe_zone_score(self, roll, safe_zone, expected_score):
        """Test safe zone scoring."""
        scorer = HeuristicScorer()
        
        move = Move(
            piece_id=0,
            from_position=0,
            to_position=3,
            move_type=MoveType.ADVANCE
        )
        
        score, _ = scorer.score(move, PlayerColor.RED, self._create_board(safe_zone))
        
        assert score == expected_score
    
    @pytest.mark.parametrize("piece_count,expected_score", [
        # Blockade: +40 for 2+ pieces
        (2, 40),
        (3, 40),
        (1, 0),  # Single piece = no blockade
    ])
    def test_blockade_score(self, piece_count, expected_score):
        """Test blockade scoring."""
        scorer = HeuristicScorer()
        
        move = Move(
            piece_id=0,
            from_position=5,
            to_position=8,
            move_type=MoveType.ADVANCE
        )
        
        board_state = self._create_board_with_stack(piece_count, to_position=8)
        score, _ = scorer.score(move, PlayerColor.RED, board_state)
        
        assert score == expected_score
    
    # Enter board: +30
    # Exact goal: +20
    # Exposed: -30
    # Break blockade: -20
```

### Mock ADB Responses for Testing

```python
# tests/conftest.py
import pytest
import numpy as np
from unittest.mock import Mock, patch


@pytest.fixture
def mock_screenshot_clean() -> np.ndarray:
    """Clean board screenshot for testing."""
    # Generate synthetic board image
    return np.zeros((1080, 1920, 3), dtype=np.uint8)


@pytest.fixture
def mock_screenshot_with_pieces() -> np.ndarray:
    """Screenshot with some pieces placed."""
    image = np.zeros((1080, 1920, 3), dtype=np.uint8)
    # Add red pieces (simulated)
    image[100:120, 100:120] = [0, 0, 255]  # BGR
    return image


@pytest.fixture
def mock_adb_connector():
    """Mock ADB connector."""
    with patch('src.adb_connector.adb_connector.subprocess') as mock:
        mock.return_value = Mock(
            returncode=0,
            communicate=Mock(return_value=(b'\x89PNG\r\n', b''))
        )
        yield mock


@pytest.fixture
def mock_display():
    """Mock X11 display."""
    with patch('src.overlay.overlay_renderer.Xlib') as mock:
        mock_display = Mock()
        mock_display.screen.return_value = Mock(
            root=Mock(),
            width_in_pixels=1920,
            height_in_pixels=1080
        )
        yield mock_display
```

### Integration Test Plan

```python
# tests/test_integration.py
import pytest
from src.adb_connector import ADBConnector
from src.cv_detector import BoardDetector
from src.pathfinder import PathfinderEngine
from src.overlay import OverlayRenderer


@pytest.mark.integration
class TestFullPipeline:
    """Integration tests for full detection-to-overlay pipeline."""
    
    def test_full_pipeline_with_mock(self):
        """Test complete pipeline with mocked components."""
        # 1. Capture screenshot (mocked)
        screenshot = get_mock_screenshot()
        
        # 2. Detect board
        detector = BoardDetector(calibration=get_test_calibration())
        board_state = detector.detect(screenshot)
        
        # 3. Calculate move
        pathfinder = PathfinderEngine(board_state)
        recommendations = pathfinder.calculate_best_move(
            PlayerColor.RED,
            dice_roll=6
        )
        
        # 4. Verify output
        assert len(recommendations) > 0
        assert recommendations[0].score > 0
    
    @pytest.mark.slow
    def test_full_pipeline_real_adb(self):
        """Test with real ADB connection (requires emulator running)."""
        connector = ADBConnector(host="127.0.0.1", port=5555)
        
        if not connector.connect():
            pytest.skip("ADB not available")
        
        screenshot = connector.get_screenshot()
        assert screenshot is not None
        assert screenshot.shape[2] == 3  # BGR
        
        detector = BoardDetector(calibration=load_calibration())
        board_state = detector.detect(screenshot)
        
        assert board_state.confidence > 0.5
        
        # Clean up
        connector.disconnect()
```

### Test Coverage Targets

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | Pathfinding heuristics | Parametrized tests with known board states |
| Unit | Color thresholding | Synthetic HSV images with known colors |
| Unit | Move generation | Test all rule combinations |
| Unit | Config loading/saving | Round-trip YAML tests |
| Integration | ADB → CV → Pathfinding | Mock ADB, real pipeline |
| Integration | Full pipeline | If emulator available |
| Integration | Overlay positioning | Mock X11, verify coordinates |

## Migration / Rollback

No migration required. This is a new project with no existing data to migrate.

Rollback procedure:
1. Delete `config/calibration.yaml` to force recalibration
2. Comment out overlay import to disable display
3. Kill any running X11 overlay processes: `pkill -f parchis-pathfinder`
4. Disconnect ADB: `adb disconnect 127.0.0.1:5555`

## Open Questions

- [ ] Should the overlay auto-hide when no valid moves are available? Current: Display "No valid moves" message.
- [ ] What is the minimum acceptable confidence threshold? Current: 0.7, but this may need adjustment based on testing.
- [ ] Should the tool automatically track dice rolls (via OCR) or require manual input? Current: Manual input via CLI argument.
- [ ] How to handle pieces stacked on the same square? Current: Treat as single position with stack count.
- [ ] Should we support multiple emulators? Current: No, single emulator only as per proposal.

## Next Steps

Ready for task breakdown (sdd-tasks). The implementation will be grouped into phases:
1. Infrastructure (ADB connector, config manager)
2. CV detection (board detector, color utilities)
3. Pathfinding (move generator, heuristics)
4. Overlay (renderer, drawing)
5. Integration and testing