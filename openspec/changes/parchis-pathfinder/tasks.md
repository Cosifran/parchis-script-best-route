# Tasks: parchis-pathfinder

## Phase 1: Infrastructure & Project Setup

- [ ] 1.1 Create `requirements.txt` with opencv-python>=4.8.0, numpy>=1.24.0, PyYAML>=6.0, pycairo>=1.20.0, PyGObject>=3.40.0
- [ ] 1.2 Create `src/__init__.py` with package version and basic exports
- [ ] 1.3 Create `src/adb_connector/__init__.py` importing ADBConnector
- [ ] 1.4 Create `src/cv_detector/__init__.py` importing BoardDetector
- [ ] 1.5 Create `src/pathfinder/__init__.py` importing PathfinderEngine
- [ ] 1.6 Create `src/overlay/__init__.py` importing OverlayRenderer
- [ ] 1.7 Create `src/calibration/__init__.py` importing CalibrationTool
- [ ] 1.8 Create `config/__init__.py` importing ConfigManager
- [ ] 1.9 Create `tests/__init__.py` test package marker

## Phase 2: ADB Connector Module

- [ ] 2.1 Create `src/adb_connector/connector.py` with ADBConnector class
- [ ] 2.2 Implement `connect()`, `disconnect()`, `is_connected()` methods
- [ ] 2.3 Implement `get_screenshot()` using `adb exec-out screencap -p` returning np.ndarray
- [ ] 2.4 Implement `get_resolution()` via ADB shell dumpsys window
- [ ] 2.5 Implement `health_check()` with auto-reconnect and retry logic (3 attempts, exponential backoff)
- [ ] 2.6 Add error handling for connection refused, timeout, device offline

## Phase 3: CV Board Detector Module

- [ ] 3.1 Create `src/cv_detector/detector.py` with BoardDetector class
- [ ] 3.2 Implement HSV color space conversion (BGR to HSV)
- [ ] 3.3 Implement `detect()` method processing screenshot to BoardState
- [ ] 3.4 Implement color segmentation with configurable HSV ranges per player color
- [ ] 3.5 Implement contour detection using cv2.findContours for piece regions
- [ ] 3.6 Implement board index mapping (68-cell matrix: 0-51 path, 52-55 blue goal, 56-59 yellow goal, 60-63 green goal, 64-67 red goal)
- [ ] 3.7 Create PlayerColor enum with RED, GREEN, YELLOW, BLUE values
- [ ] 3.8 Implement BoardState, PlayerState, PiecePosition dataclasses
- [ ] 3.9 Implement confidence scoring based on detection quality

## Phase 4: Pathfinding Engine Module

- [ ] 4.1 Create `src/pathfinder/engine.py` with PathfinderEngine class
- [ ] 4.2 Implement Move dataclass with piece_id, from_position, to_position, move_type
- [ ] 4.3 Implement MoveRecommendation dataclass with move, score, reasons, alternatives
- [ ] 4.4 Implement `get_valid_moves(player, dice_roll)` generating legal moves
- [ ] 4.5 Implement move generation rules (roll 6 enters board, capture on same square, blockade blocking)
- [ ] 4.6 Implement HeuristicScorer with 7 heuristics: capture (+100), safe zone (+50), blockade (+40), enter board (+30), exact goal (+20), exposed (-30), break blockade (-20)
- [ ] 4.7 Implement `score_move()` returning total score and HeuristicResult breakdown
- [ ] 4.8 Implement `calculate_best_move()` returning ranked list of MoveRecommendation
- [ ] 4.9 Handle edge cases: no valid moves, all pieces in goal, multiple optimal moves

## Phase 5: X11 Overlay Renderer Module

- [ ] 5.1 Create `src/overlay/renderer.py` with OverlayRenderer class
- [ ] 5.2 Implement X11 override-redirect transparent window using PyGObject
- [ ] 5.3 Implement `show_recommendation()` drawing highlight rectangle at pixel position
- [ ] 5.4 Implement Cairo drawing with alpha blending for semi-transparent highlight (green, 50% opacity)
- [ ] 5.5 Implement text rendering with move description (piece, from, to positions)
- [ ] 5.6 Implement `update_position()` for window repositioning
- [ ] 5.7 Implement `clear()` and `close()` for window management
- [ ] 5.8 Handle X11 errors gracefully (disable overlay if unavailable)

## Phase 6: Calibration Tool Module

- [ ] 6.1 Create `src/calibration/tool.py` with CalibrationTool class
- [ ] 6.2 Implement Tkinter-based UI with live preview area
- [ ] 6.3 Implement board corner selection (4 points: TL, TR, BL, BR as relative coordinates)
- [ ] 6.4 Implement color picker for HSV range sampling per player color
- [ ] 6.5 Implement detection test with confidence visualization
- [ ] 6.6 Implement save/load calibration to/from YAML (calibration.yaml)
- [ ] 6.7 Implement validate_calibration() checking required fields

## Phase 7: Configuration Management

- [ ] 7.1 Create `config/manager.py` with ConfigManager class
- [ ] 7.2 Implement load_settings() loading settings.yaml with defaults
- [ ] 7.3 Implement load_calibration() loading calibration.yaml
- [ ] 7.4 Implement save_calibration() persisting calibrated values
- [ ] 7.5 Implement get() method with dot-notation key support (e.g., 'adb.host')
- [ ] 7.6 Create default `config/settings.yaml` with ADB, overlay, detection, debug sections

## Phase 8: Main CLI Entry Point

- [ ] 8.1 Create `main.py` as CLI entry point with argparse
- [ ] 8.2 Implement command: `capture` - capture and save screenshot
- [ ] 8.3 Implement command: `detect` - capture and show board state
- [ ] 8.4 Implement command: `move <color> <roll>` - calculate best move
- [ ] 8.5 Implement command: `overlay` - run real-time overlay display
- [ ] 8.6 Implement command: `calibrate` - launch calibration UI
- [ ] 8.7 Implement main loop with signal handling (SIGINT/SIGTERM cleanup)
- [ ] 8.8 Add --config option for custom config directory
- [ ] 8.9 Add --debug option for debug logging

## Phase 9: Unit Tests for Pathfinding

- [ ] 9.1 Create `tests/test_pathfinder.py` with pytest
- [ ] 9.2 Write test_capture_heuristic: +100 points when landing on opponent piece
- [ ] 9.3 Write test_safe_zone_heuristic: +50 points for moving to safe corridor/goal
- [ ] 9.4 Write test_blockade_heuristic: +40 points when forming 2+ piece stack
- [ ] 9.5 Write test_enter_board_heuristic: +30 points when entering from base (roll 6)
- [ ] 9.6 Write test_exact_goal_heuristic: +20 points for exact roll to reach goal
- [ ] 9.7 Write test_exposed_heuristic: -30 points when moving to exposed square
- [ ] 9.8 Write test_break_blockade_heuristic: -20 points when leaving blockade
- [ ] 9.9 Write test_no_valid_moves when all pieces blocked/in base with no 6
- [ ] 9.10 Write test_move_generation ENTER, ADVANCE, CAPTURE, GOAL move types

## Phase 10: Integration & Verification

- [ ] 10.1 Verify ADB connection to emulator (localhost:5555)
- [ ] 10.2 Verify screenshot capture returns valid BGR NumPy array
- [ ] 10.3 Verify board detection detects all 4 player colors
- [ ] 10.4 Verify pathfinding returns valid legal moves only
- [ ] 10.5 Verify overlay renders at correct screen position
- [ ] 10.6 Verify calibration tool saves/loads correctly
- [ ] 10.7 Verify full pipeline: capture → detect → pathfind → overlay
- [ ] 10.8 Performance test: screenshot to overlay update under 500ms