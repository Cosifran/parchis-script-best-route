# Parchís Pathfinder Technical Specification

**Project Name:** parchis-pathfinder  
**Version:** 1.0.0  
**Status:** Technical Specification  
**Date:** 2026-04-14

---

## 1. Project Overview

### 1.1 Purpose

The Parchís Pathfinder is an intelligent assistant tool that connects to an Android emulator running a Parchís/Ludo game, automatically detects the game board state using computer vision, calculates optimal moves based on a heuristic scoring system, and displays move recommendations through a transparent X11 overlay.

### 1.2 Scope

The tool operates as a passive advisory system—it observes the game state, provides recommendations, and does not interact with the game directly. Users maintain full control over game execution while receiving AI-assisted move guidance.

### 1.3 Target Users

- Players seeking strategic assistance in Parchís/Ludo games
- Developers building AI assistants for board games
- Hobbyists exploring ADB automation and computer vision integration

---

## 2. Technical Stack

### 2.1 Core Technologies

| Component | Technology | Version |
|-----------|------------|---------|
| Language | Python | 3.10+ |
| Computer Vision | OpenCV (cv2), NumPy | cv2 4.8+, numpy 1.24+ |
| Screenshot Capture | ADB exec-out | Platform tools |
| Overlay Display | X11 + PyGObject + Cairo | GI 3.40+, Cairo 1.16+ |
| Configuration | PyYAML | 6.0+ |
| GUI (Calibration) | Tkinter | Built-in |

### 2.2 System Dependencies

- Android Emulator (localhost:5555)
- ADB server running
- X11 display server
- Linux/Unix environment (overlay designed for X11)

---

## 3. System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Parchís Pathfinder                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐     │
│  │   Config     │    │    ADB       │    │     CV       │     │
│  │  Manager     │    │  Connector   │    │   Detector   │     │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘     │
│         │                   │                   │              │
│         └───────────────────┼───────────────────┘              │
│                             │                                   │
│                       ┌─────┴─────┐                            │
│                       │  Game     │                            │
│                       │  State    │                            │
│                       │  Manager  │                            │
│                       └─────┬─────┘                            │
│                             │                                   │
│         ┌───────────────────┼───────────────────┐              │
│         │                   │                   │              │
│  ┌──────┴───────┐    ┌──────┴───────┐    ┌──────┴───────┐     │
│  │ Pathfinding  │    │   Overlay    │    │ Calibration  │     │
│  │   Engine     │    │   Renderer   │    │    Tool      │     │
│  └──────────────┘    └──────────────┘    └──────────────┘     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. Component Specifications

### 4.1 ADB Connector Module

**Module Path:** `src/adb_connector/`  
**Primary Class:** `ADBConnector`

#### 4.1.1 Responsibilities

- Establish and maintain connection to Android emulator
- Capture screenshots efficiently via streaming (no temp files)
- Retrieve device information (screen resolution, density)
- Perform health checks and auto-reconnection

#### 4.1.2 Connection Management

| Parameter | Default | Configurable |
|-----------|---------|--------------|
| Host | 127.0.0.1 | Yes (settings.yaml) |
| Port | 5555 | Yes (settings.yaml) |
| Connection Timeout | 10 seconds | Yes |
| Retry Attempts | 3 | Yes |
| Retry Delay | 2 seconds | Yes |

#### 4.1.3 Public API

```python
class ADBConnector:
    def connect(self) -> bool:
        """Establish connection to emulator. Returns True on success."""
        
    def disconnect(self) -> None:
        """Close ADB connection cleanly."""
        
    def is_connected(self) -> bool:
        """Check if connection is active."""
        
    def get_screenshot(self) -> np.ndarray:
        """Capture screenshot as NumPy array (BGR format)."""
        
    def get_screen_resolution(self) -> tuple[int, int]:
        """Return (width, height) of device screen."""
        
    def get_screen_density(self) -> int:
        """Return screen density (dpi)."""
        
    def health_check(self) -> bool:
        """Verify connection health. Attempt reconnect if needed."""
```

#### 4.1.4 Screenshot Capture

- Command: `adb exec-out screencap -p`
- Output: Direct to stdout, parsed as image (no temporary files)
- Format: PNG compressed, decoded to NumPy array
- Expected Latency: < 500ms

#### 4.1.5 Error Handling

| Error Type | Handling Strategy |
|------------|-------------------|
| Connection refused | Retry with exponential backoff |
| Device offline | Trigger auto-reconnect |
| Screenshot timeout | Return None, log error |
| Invalid image data | Retry once, then fail |

---

### 4.2 CV Board Detector Module

**Module Path:** `src/cv_detector/`  
**Primary Class:** `BoardDetector`

#### 4.2.1 Responsibilities

- Convert screenshot to NumPy array
- Detect board grid structure
- Identify piece positions for all players
- Detect special zones (safe zones, home bases, goal zones)
- Output structured board state

#### 4.2.2 Color Space Processing

The detector uses HSV color space for robust color thresholding:

```python
# HSV ranges for each player color (configurable via calibration)
PLAYER_COLORS = {
    'red':    {'lower': (0, 100, 100), 'upper': (10, 255, 255)},
    'green':  {'lower': (40, 100, 100), 'upper': (80, 255, 255)},
    'yellow': {'lower': (20, 100, 100), 'upper': (30, 255, 255)},
    'blue':   {'lower': (100, 100, 100), 'upper': (140, 255, 255)},
}
```

#### 4.2.3 Board Grid Detection

The Parchís board consists of:
- 4 home bases (one per player color)
- 4 starting positions (one per player color)
- 52 path squares (13 per color's path)
- 4 safe zones (corridors leading to goal)
- 1 goal area per color (4 squares)

**Grid Coordinate System:**
- Relative coordinates: (0.0, 0.0) to (1.0, 1.0) of captured screen
- Absolute coordinates: Pixel values based on detected resolution

#### 4.2.4 Special Zone Detection

| Zone Type | Detection Method | Visual Marker |
|-----------|------------------|----------------|
| Safe Zone | Distinct color marking (usually star/pattern) | Configurable via calibration |
| Home Base | Large square area in player's color | Color threshold |
| Goal Zone | Distinct color or geometric pattern | Configurable via calibration |

#### 4.2.5 Public API

```python
class BoardDetector:
    def __init__(self, calibration: dict):
        """Initialize with calibration data."""
        
    def detect(self, screenshot: np.ndarray) -> BoardState:
        """Process screenshot and return board state."""
        
    def set_calibration(self, calibration: dict) -> None:
        """Update calibration parameters."""
```

#### 4.2.6 Output: BoardState

```python
@dataclass
class BoardState:
    resolution: tuple[int, int]          # (width, height)
    players: dict[str, PlayerState]      # Per-player piece positions
    timestamp: float                     # Detection timestamp
    confidence: float                    # Detection confidence 0.0-1.0

@dataclass
class PlayerState:
    color: str                           # 'red', 'green', 'yellow', 'blue'
    pieces: list[PiecePosition]          # 4 pieces per player
    base_positions: list[int]            # Indices of pieces in base
    active_positions: list[int]          # Indices of pieces on board
    goal_positions: list[int]            # Indices of pieces in goal

@dataclass
class PiecePosition:
    piece_id: int                        # 0-3 for each player's pieces
    position_type: str                   # 'base', 'board', 'goal', 'unknown'
    board_index: int | None             # Index on path if on board (0-51)
    pixel_position: tuple[int, int]      # (x, y) center of detected piece
    confidence: float                    # Detection confidence
```

#### 4.2.7 Processing Pipeline

1. **Preprocessing:** Resize if needed, apply Gaussian blur
2. **Color Thresholding:** Apply HSV masks for each player color
3. **Contour Detection:** Find connected regions matching piece colors
4. **Centroid Calculation:** Determine piece centers
5. **Position Mapping:** Match detected positions to board grid
6. **State Aggregation:** Compile BoardState from all detections

#### 4.2.8 Error Handling

| Failure Mode | Handling |
|--------------|----------|
| No pieces detected | Return empty player states, confidence = 0.0 |
| Partial detection | Return partial state, confidence = 0.5-0.8 |
| Board not found | Raise `BoardNotFoundException` |
| Invalid calibration | Raise `InvalidCalibrationException` |

---

### 4.3 Pathfinding Engine Module

**Module Path:** `src/pathfinder/`  
**Primary Class:** `Pathfinder`

#### 4.3.1 Responsibilities

- Generate valid moves for each piece based on dice roll
- Apply heuristic scoring to rank moves
- Handle edge cases (no valid moves, multiple optimal moves)
- Output ranked list of recommended moves

#### 4.3.2 Move Generation Rules

**General Parchís Rules:**
- Roll of 6 allows piece to enter board from base OR move 6 squares
- Piece captures opponent if landing on same square
- Blockade (2+ pieces on same square) is impassable
- Safe squares cannot be captured (except by exact landing)
- Exact roll required to enter goal

**Move Generation Logic:**
```python
def generate_moves(player: PlayerState, dice_roll: int) -> list[Move]:
    moves = []
    for piece in player.pieces:
        if piece.position_type == 'base' and dice_roll == 6:
            moves.append(Move(piece, 'enter_board'))
        elif piece.position_type == 'board':
            new_index = piece.board_index + dice_roll
            if new_index <= 51:
                moves.append(Move(piece, new_index))
            elif new_index == 52:  # Exact to goal
                moves.append(Move(piece, 'goal'))
    return moves
```

#### 4.3.3 Heuristic Scoring System

| Score | Condition | Description |
|-------|-----------|-------------|
| +100 | Capture opponent | Landing on square occupied by opponent piece |
| +50 | Safe square | Entering safe corridor or goal zone |
| +40 | Blockade | Forming a 2+ piece blockade |
| +30 | Enter board | Moving from base to board (requires roll 6) |
| +20 | Exact goal | Exact roll to reach goal |
| -30 | Exposed square | Moving to square where opponent can capture |
| -20 | Break blockade | Moving away from existing blockade |

**Additional Rules:**
- Blockades are immovable—cannot move through or land on them
- If all pieces in base and no roll of 6, no moves available
- Multiple pieces on same square form a "stack" (only outer piece vulnerable)

#### 4.3.4 Public API

```python
class Pathfinder:
    def __init__(self, board_state: BoardState):
        """Initialize with current board state."""
        
    def calculate_best_move(self, player_color: str, dice_roll: int) -> list[MoveRecommendation]:
        """Return ranked list of best moves for player with given dice roll."""
        
    def get_valid_moves(self, player_color: str, dice_roll: int) -> list[Move]:
        """Return all valid moves without scoring."""
```

#### 4.3.5 Output: MoveRecommendation

```python
@dataclass
class MoveRecommendation:
    move: Move
    score: float
    reasons: list[str]              # Explanation of score components
    alternative_moves: list[Move]   # Other good options
    
@dataclass
class Move:
    piece_id: int
    from_position: int | str       # Board index or 'base'
    to_position: int | str         # Board index, 'goal', or 'enter'
    move_type: str                  # 'advance', 'enter', 'capture', 'goal'
```

#### 4.3.6 Edge Case Handling

| Scenario | Output |
|----------|--------|
| No valid moves | Return empty list, reason: "No valid moves for current roll" |
| All moves equally scored | Return top 3 moves with same score |
| Multiple optimal moves | Return top 3 ranked by secondary heuristics |
| Piece in base, no 6 | Skip that piece for move generation |

---

### 4.4 Overlay Renderer Module

**Module Path:** `src/overlay/`  
**Primary Class:** `OverlayRenderer`

#### 4.4.1 Responsibilities

- Create transparent X11 window (override-redirect)
- Draw highlight rectangle around recommended move position
- Display move text with semi-transparent background
- Position overlay to match emulator screen coordinates

#### 4.4.2 Window Configuration

| Property | Value |
|----------|-------|
| Window Type | Override-redirect (no decorations) |
| Transparency | Full transparency with per-pixel alpha |
| Position | Matches emulator screen coordinates |
| Stacking | Always on top |
| Input | Pass-through (non-interactive) |

#### 4.4.3 Drawing Specification

**Highlight Rectangle:**
- Color: Bright green (RGB: 0, 255, 0) with 50% opacity
- Border width: 3 pixels
- Corner radius: 8 pixels (if supported by Cairo)
- Animation: Subtle pulse effect (optional, configurable)

**Text Display:**
- Font: Sans-serif, 16pt
- Color: White with dark shadow for readability
- Background: Semi-transparent black (50% opacity)
- Padding: 10px horizontal, 5px vertical
- Position: Below highlight rectangle or top-left corner

**Text Format Examples:**
- "Move RED piece #2 forward 6 spaces"
- "RED: Enter piece #1 from base"
- "Capture! Move BLUE piece #3 to square 12"

#### 4.4.4 Public API

```python
class OverlayRenderer:
    def __init__(self, screen_resolution: tuple[int, int]):
        """Initialize overlay window with screen resolution."""
        
    def show_recommendation(self, recommendation: MoveRecommendation, 
                           pixel_position: tuple[int, int]) -> None:
        """Display move recommendation at specified screen position."""
        
    def update_position(self, x: int, y: int) -> None:
        """Update overlay window position."""
        
    def clear(self) -> None:
        """Clear overlay content."""
        
    def close(self) -> None:
        """Destroy overlay window."""
        
    @property
    def is_visible(self) -> bool:
        """Check if overlay is currently displayed."""
```

#### 4.4.5 Coordinate Mapping

The overlay must position content at exact screen coordinates matching the emulator display:

```
Overlay Window Position: (0, 0) of emulator screen
Content Position: Absolute pixel coordinates from BoardDetector
```

**Offset Handling:**
- If emulator window is offset on screen, apply manual offset from settings
- Offset stored in calibration.yaml: `{overlay_offset_x: 0, overlay_offset_y: 0}`

#### 4.4.6 Error Handling

| Error | Handling |
|-------|----------|
| X11 not available | Log error, disable overlay |
| Window creation failed | Log error, continue without overlay |
| Display permission denied | Log error, suggest xhost configuration |

---

### 4.5 Calibration Tool Module

**Module Path:** `src/calibration/`  
**Primary Class:** `CalibrationTool`

#### 4.5.1 Responsibilities

- Manual board corner selection (4 points: top-left, top-right, bottom-left, bottom-right)
- Color picker for each player color (sample multiple points)
- Test capture and visualize detection results
- Save/load calibration to YAML file

#### 4.5.2 User Interface (Tkinter)

**Main Window Layout:**
```
┌────────────────────────────────────────────┐
│  Parchís Board Calibration                 │
├────────────────────────────────────────────┤
│                                            │
│  [Live Preview Area - 640x480]            │
│                                            │
├────────────────────────────────────────────┤
│  Step 1: Select Board Corners             │
│  [TL] [TR] [BL] [BR]  |  Status: 2/4       │
├────────────────────────────────────────────┤
│  Step 2: Calibrate Colors                  │
│  [RED] [GREEN] [YELLOW] [BLUE] | Status OK │
├────────────────────────────────────────────┤
│  Step 3: Test Detection                    │
│  [Run Test] | Confidence: 87%              │
├────────────────────────────────────────────┤
│  [Save Calibration] [Load] [Reset]         │
└────────────────────────────────────────────┘
```

#### 4.5.3 Calibration Data Structure

```yaml
# calibration.yaml
board_corners:
  top_left: [0.15, 0.20]    # Relative coordinates (0.0-1.0)
  top_right: [0.85, 0.20]
  bottom_left: [0.15, 0.80]
  bottom_right: [0.85, 0.80]

color_ranges:
  red:
    hsv_lower: [0, 100, 100]
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
  - name: "red_corridor"
    board_indices: [0, 8, 13, 21, 26, 34, 39, 47]
  # ... etc

board_grid:
  cell_width: 0.045    # Relative to board width
  cell_height: 0.045   # Relative to board height
```

#### 4.5.4 Public API

```python
class CalibrationTool:
    def start_interactive(self) -> None:
        """Launch Tkinter calibration UI."""
        
    def load_calibration(self, path: str) -> dict:
        """Load calibration from YAML file."""
        
    def save_calibration(self, calibration: dict, path: str) -> None:
        """Save calibration to YAML file."""
        
    def validate_calibration(self, calibration: dict) -> bool:
        """Check calibration has all required fields."""
        
    def auto_detect_corners(self, screenshot: np.ndarray) -> list[tuple[float, float]]:
        """Attempt automatic corner detection (optional enhancement)."""
```

#### 4.5.5 Calibration Workflow

1. **Capture Reference:** User captures screenshot of clean board
2. **Corner Selection:** User clicks 4 corners in order (TL → TR → BL → BR)
3. **Color Sampling:** User clicks multiple points for each player color
4. **Validation:** System displays detected regions for verification
5. **Save:** Calibration saved to `calibration.yaml`

---

### 4.6 Configuration System

**Config Path:** `config/`  
**Format:** YAML via PyYAML

#### 4.6.1 Configuration Files

**settings.yaml** - Runtime configuration:
```yaml
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

**calibration.yaml** - Calibrated values (generated by calibration tool):
```yaml
# See Section 4.5.3 for full structure

version: "1.0"
last_calibrated: "2026-04-14T10:30:00Z"
```

#### 4.6.2 Configuration Loading

```python
class ConfigManager:
    def __init__(self, config_dir: str = "config"):
        """Initialize config manager with config directory."""
        
    def load_settings(self) -> dict:
        """Load settings.yaml with defaults for missing keys."""
        
    def load_calibration(self) -> dict:
        """Load calibration.yaml, raise if not found."""
        
    def save_calibration(self, calibration: dict) -> None:
        """Save calibration to calibration.yaml."""
        
    def get(self, key: str, default: any = None) -> any:
        """Get setting value by dot-notation key (e.g., 'adb.host')."""
```

---

## 5. Screen Resolution Handling

### 5.1 Resolution Detection

The system detects emulator resolution via ADB:
```python
# Via ADB shell dumpsys window
width = get_window_property("DisplayWidth")
height = get_window_property("DisplayHeight")
```

### 5.2 Coordinate Systems

| System | Description | Use Case |
|--------|-------------|----------|
| Relative (0.0-1.0) | Fraction of screen width/height | Board corners, cell positions |
| Absolute (pixels) | Actual screen coordinates | Overlay positioning, detection |

### 5.3 Coordinate Conversion

```python
def relative_to_absolute(relative: tuple[float, float], 
                         resolution: tuple[int, int]) -> tuple[int, int]:
    x = int(relative[0] * resolution[0])
    y = int(relative[1] * resolution[1])
    return (x, y)

def absolute_to_relative(absolute: tuple[int, int], 
                        resolution: tuple[int, int]) -> tuple[float, float]:
    x = absolute[0] / resolution[0]
    y = absolute[1] / resolution[1]
    return (x, y)
```

### 5.4 Manual Offset Adjustment

Users can configure overlay offset in settings.yaml:
```yaml
overlay:
  offset_x: 0      # Pixels to add to x position
  offset_y: 0      # Pixels to add to y position
```

---

## 6. Edge Cases

### 6.1 No Valid Moves

**Condition:** All pieces blocked, in base, or in goal; current dice roll cannot move any piece.

**Handling:**
- Overlay displays: "No valid moves for roll {n}"
- Log: "No valid moves for player {color}, dice={n}"
- Return empty MoveRecommendation list

### 6.2 Multiple Optimal Moves

**Condition:** Two or more moves have identical highest score.

**Handling:**
- Return up to 3 top-scoring moves
- Display: "Multiple optimal moves available"
- Show all alternatives in overlay

### 6.3 Connection Lost

**Condition:** ADB connection drops during operation.

**Handling:**
- Attempt auto-reconnect (up to retry_attempts)
- If reconnect fails, display error in overlay
- Log error with timestamp
- Graceful degradation: continue without updating

### 6.4 Invalid Board State

**Condition:** Unable to parse board (no corners detected, invalid grid).

**Handling:**
- Raise `BoardDetectionException`
- Display: "Unable to detect board - recalibration needed"
- Log confidence score and detection failures

### 6.5 Conflicting Piece Colors

**Condition:** Detected piece matches multiple color ranges.

**Handling:**
- Use largest contour area as tiebreaker
- Log: "Color ambiguity resolved for piece at {position}"
- Set confidence to 0.5 for ambiguous detections

---

## 7. Acceptance Criteria

### 7.1 Connection

| Criterion | Requirement | Test Method |
|-----------|-------------|-------------|
| ADB Connection | Successfully connects to 127.0.0.1:5555 | Unit test with mock emulator |
| Connection Timeout | Completes within 10 seconds | Timing test |
| Auto-Reconnect | Reconnects within 20 seconds of disconnect | Integration test |

### 7.2 Screenshot Capture

| Criterion | Requirement | Test Method |
|-----------|-------------|-------------|
| Capture Latency | < 500ms per capture | Benchmark test |
| Image Format | Returns valid BGR NumPy array | Type and shape verification |
| Resolution Accuracy | Matches emulator resolution exactly | Compare with ADB dumpsys |

### 7.3 Board Detection

| Criterion | Requirement | Test Method |
|-----------|-------------|-------------|
| Position Accuracy | ≥ 90% correct piece positions | Test on 100 sample images |
| Corner Detection | 4 corners within 5px of actual | Manual verification |
| Color Classification | ≥ 95% correct color assignment | Confusion matrix test |
| Confidence Score | Accurate (≥ 0.9 when correct, < 0.7 when wrong) | Correlation test |

### 7.4 Pathfinding

| Criterion | Requirement | Test Method |
|-----------|-------------|-------------|
| Calculation Time | < 1 second per move calculation | Benchmark test |
| Move Validity | 100% of suggested moves are legal | Rule validation test |
| Score Accuracy | Optimal move ranked first (verified manually) | Manual test suite |

### 7.5 Overlay

| Criterion | Requirement | Test Method |
|-----------|-------------|-------------|
| Position Accuracy | Within 10px of target position | Measurement test |
| Visibility | Visible on all standard backgrounds | Visual test |
| Text Clarity | Readable at 1m distance on 1080p | User test |

### 7.6 Calibration Persistence

| Criterion | Requirement | Test Method |
|-----------|-------------|-------------|
| Save/Load | Calibration survives app restart | Integration test |
| Version Compatibility | Old calibrations upgrade gracefully | Migration test |

---

## 8. File Structure

```
parchis-pathfinder/
├── config/
│   ├── settings.yaml          # Default runtime settings
│   └── calibration.yaml       # Calibrated board parameters
├── src/
│   ├── __init__.py
│   ├── main.py                # Entry point
│   ├── config/
│   │   ├── __init__.py
│   │   └── config_manager.py # Configuration loading
│   ├── adb_connector/
│   │   ├── __init__.py
│   │   └── adb_connector.py  # ADB connection and screenshot
│   ├── cv_detector/
│   │   ├── __init__.py
│   │   ├── board_detector.py # Main detection logic
│   │   ├── color_tracker.py  # HSV color utilities
│   │   └── grid_mapper.py     # Board grid mapping
│   ├── pathfinder/
│   │   ├── __init__.py
│   │   ├── pathfinder.py     # Move calculation
│   │   ├── move_generator.py # Valid move generation
│   │   └── heuristics.py     # Scoring system
│   ├── overlay/
│   │   ├── __init__.py
│   │   ├── overlay_renderer.py # X11 overlay
│   │   └── drawing.py        # Cairo drawing utilities
│   └── calibration/
│       ├── __init__.py
│       ├── calibration_tool.py # Tkinter UI
│       └── color_picker.py    # Interactive color sampling
├── tests/
│   ├── __init__.py
│   ├── test_adb_connector.py
│   ├── test_board_detector.py
│   ├── test_pathfinder.py
│   └── test_overlay.py
├── requirements.txt
├── README.md
└── setup.py
```

---

## 9. Dependencies

```
opencv-python>=4.8.0
numpy>=1.24.0
PyYAML>=6.0
pycairo>=1.20.0
PyGObject>=3.40.0
```

---

## 10. Future Enhancements (Out of Scope)

- Multi-window support (multiple emulator instances)
- Real-time game state tracking across turns
- Machine learning for piece classification
- Voice announcement of moves
- Mobile companion app
- Automatic calibration via template matching

---

## Appendix A: Data Flow Diagram

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│    ADB      │────▶│     CV      │────▶│ Pathfinding │
│  Connector  │     │  Detector   │     │   Engine    │
└─────────────┘     └─────────────┘     └─────────────┘
      │                   │                   │
      │ screenshot        │ BoardState        │ MoveRecommendation
      ▼                   ▼                   ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Config    │     │    Config   │     │   Overlay   │
│   Manager   │     │   Manager   │     │  Renderer   │
└─────────────┘     └─────────────┘     └─────────────┘
```

---

## Appendix B: Error Codes

| Code | Meaning | Severity |
|------|---------|----------|
| E001 | ADB connection failed | Error |
| E002 | Screenshot capture timeout | Warning |
| E003 | Board corners not detected | Error |
| E004 | Invalid calibration data | Error |
| E005 | No valid moves for dice roll | Info |
| E006 | X11 overlay creation failed | Warning |
| E007 | Configuration file missing | Error |
| E008 | Color range out of bounds | Warning |

---

*End of Technical Specification*