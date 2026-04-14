# Proposal: parchis-pathfinder

## Intent

Create a Linux tool that connects via ADB to an Android emulator running Parchís, uses computer vision (OpenCV) to detect the board state and game pieces, calculates the optimal move using a scoring heuristic system, and displays the recommended move via a transparent Linux overlay.

This project addresses the need for automated move recommendations in Parchís (a popular board game similar to Ludo) by combining real-time screen capture with intelligent move calculation and non-intrusive UI feedback.

## Scope

### In Scope

1. **ADB Connection Module**
   - Connect to Android emulator on localhost:5555
   - Screenshot capture via `adb exec-out screencap -p` (no intermediate file storage)
   - Connection validation and reconnection logic

2. **Computer Vision Detection**
   - OpenCV-based board detection with color segmentation
   - Identify 4 player colors (red, green, yellow, blue)
   - Detect safe squares (different color marking)
   - Detect home/base areas
   - Detect goal zone
   - Board state representation as NumPy matrix

3. **Move Scoring System**
   - +100 points: Capture opponent piece
   - +50 points: Enter safe square (goal or corridor)
   - -30 points: Move to a square exposed to opponent
   - Additional heuristics: blocking, forming blockade (2 pieces), exact roll to reach goal, entering the board

4. **X11 Overlay Window**
   - Transparent overlay using PyGObject/Cairo
   - Override-redirect window for always-on-top display
   - Highlight recommended move position
   - Visual indicators for piece movement direction

5. **Calibration Tool**
   - Manual color calibration for board detection
   - Position alignment for overlay with emulator window
   - Interactive UI for adjusting detection parameters

6. **Configuration Persistence**
   - Configuration file for storing calibration settings
   - Emulator connection settings
   - User preferences

### Out of Scope

- Multi-emulator support (single emulator only)
- Network-connected emulator support (localhost only)
- Touch automation to execute moves (display only)
- Sound notifications
- Machine learning-based move prediction (heuristic only)
- Game state history and analytics
- Automated testing infrastructure

## Approach

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      parchis-pathfinder                      │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ ADB Manager │─▶│ CV Detector │─▶│   Move Calculator   │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
│         │                │                    │              │
│         ▼                ▼                    ▼              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │  Capture   │  │   Board    │  │  Score Evaluator   │  │
│  │  Service   │  │   Parser   │  │     (Heuristics)   │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
│                                                  │            │
│                              ┌───────────────────┘            │
│                              ▼                                │
│                     ┌─────────────────┐                       │
│                     │  X11 Overlay    │◀── Display             │
│                     │  Renderer      │    Recommended         │
│                     └─────────────────┘    Move                │
└─────────────────────────────────────────────────────────────┘
```

### Detection Pipeline

1. **Screenshot Capture**: Pull frame buffer via ADB exec-out
2. **Preprocessing**: Apply color space conversion (BGR to HSV)
3. **Color Segmentation**: Define HSV ranges for each player color
4. **Contour Detection**: Find connected regions for pieces
5. **Board Parsing**: Map detected pieces to board coordinates
6. **State Matrix**: Build NumPy matrix representation

### Move Calculation Pipeline

1. **Generate Moves**: Enumerate all legal moves for current player
2. **Score Each Move**: Apply heuristic scoring system
3. **Select Best**: Choose move with highest score
4. **Overlay Update**: Render recommended move on X11 overlay

### Key Technical Decisions

- **Language**: Python 3.x
- **Computer Vision**: OpenCV + NumPy
- **Screenshot**: ADB exec-out (no intermediate file storage)
- **Overlay**: X11 with PyGObject/Cairo (override-redirect window for transparency)
- **State Management**: NumPy matrix representing the board (68 squares + home areas)

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `src/adb/manager.py` | New | ADB connection and screenshot capture |
| `src/cv/detector.py` | New | OpenCV board and piece detection |
| `src/cv/calibrator.py` | New | Interactive calibration UI |
| `src/pathfinder/calculator.py` | New | Move scoring algorithm |
| `src/pathfinder/heuristics.py` | New | Heuristic scoring functions |
| `src/overlay/renderer.py` | New | X11 overlay rendering |
| `src/overlay/window.py` | New | Transparent window management |
| `src/config/settings.py` | New | Configuration management |
| `src/state/board.py` | New | Board state representation |
| `src/state/parser.py` | New | CV output to board state |
| `tests/` | New | Unit and integration tests |
| `config/default.yaml` | New | Default configuration file |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Color calibration mismatch between emulator instances | High | Provide robust calibration UI; allow per-session adjustment; save multiple profiles |
| Screenshot latency causing outdated board state | Medium | Implement frame timestamp tracking; add latency indicator in overlay; allow manual refresh |
| Overlay misalignment with emulator window | Medium | Provide coordinate calibration tool; support window position detection |
| ADB connection drops | Low | Implement auto-reconnect logic with exponential backoff |
| Performance issues with continuous capture | Low | Use threading for non-blocking capture; limit frame rate to 2-5 FPS |
| Color detection false positives | Medium | Add confidence threshold; allow manual override of detections |

## Rollback Plan

1. **Configuration Rollback**: Delete or reset `config/user_settings.yaml` to defaults
2. **Module Disable**: Comment out import statements in `src/main.py` to disable components
3. **Overlay Kill**: Ensure X11 overlay terminates on SIGINT/SIGTERM
4. **ADB Cleanup**: Run `adb disconnect` on exit to clean up emulator connection
5. **Verification**: Run `pkill -f parchis-pathfinder` to ensure all processes terminated

## Dependencies

- **Python 3.8+** with packages: opencv-python, numpy, pygobject, cairo, pyyaml
- **ADB**: Android Debug Bridge (system package)
- **X11**: X Window System with development libraries
- **Android Emulator**: Running on localhost:5555 with Parchís game installed

## Success Criteria

- [ ] ADB successfully connects to emulator and captures screenshots
- [ ] CV detection correctly identifies all 4 player colors on calibrated board
- [ ] Move calculator applies all 6 heuristic rules correctly
- [ ] X11 overlay displays transparent window over emulator
- [ ] Overlay highlights recommended move position accurately
- [ ] Calibration tool allows manual adjustment of color ranges
- [ ] Configuration persists across application restarts
- [ ] Application handles ADB disconnection gracefully
- [ ] No memory leaks during continuous operation (1+ hour test)
- [ ] Response time from screenshot to overlay update under 500ms

## Deliverables Summary

1. **Python Application**: Modular architecture with separated concerns
2. **Calibration Tool**: Interactive UI for color and position adjustment
3. **Real-time Overlay**: X11 transparent window showing optimal move
4. **Configuration File**: YAML-based settings persistence