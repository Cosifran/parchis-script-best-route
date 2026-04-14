# Exploration: Parchís Pathfinding Tool Technical Analysis

## Overview

This document provides a comprehensive technical analysis for building a Parchís (Ludo-style board game) pathfinding tool that operates on Android through an emulator. The tool combines computer vision (OpenCV) for board state detection, ADB for screenshot capture and interaction, and a Linux overlay window for visual feedback.

---

## 1. OpenCV for Board Game Detection

### Current State

Computer vision for board game detection is a well-established domain with proven techniques. For Parchís/Ludo detection, the challenge is detecting a cross-shaped board with colored squares and pieces. The key techniques are:

- **Contour detection**: Using `cv2.findContours()` to identify board boundaries and individual squares
- **Color thresholding**: Using HSV color space for robust color detection (handles lighting variations better than RGB)
- **Grid detection**: Hough Line Transform (`cv2.HoughLines()`) to detect board grid structure
- **Template matching**: `cv2.matchTemplate()` for identifying specific piece types
- **Perspective transform**: `cv2.getPerspectiveTransform()` to straighten warped board views

### Approaches

| Approach | Technique | Complexity | Accuracy | Notes |
|----------|-----------|------------|----------|-------|
| Color-based detection | HSV thresholding + contour filtering | Low | High for clear pieces | Best for controlled lighting |
| Grid-based detection | Corner detection + grid extrapolation | Medium | Medium | Works for perspective distortion |
| Template matching | Pre-defined piece templates + matchTemplate | Medium | High | Requires template images |
| Hybrid | Color + grid + template combination | High | Very High | Most robust for real-world use |

### Key Implementation Strategy

For Parchís specifically:

1. **Board localization**: Find the cross-shaped board using color segmentation (each arm has distinct color)
2. **Grid extraction**: Map 52 outer track squares + 4 home bases + home columns
3. **Piece detection**: Detect pieces via color histogram in each grid cell
4. **State parsing**: Map detected colors to board state matrix

**Recommended approach**: Hybrid color-based detection with predefined board geometry
- Use color thresholds to isolate the 4 player zones
- Apply perspective transform to normalize board orientation
- Use known grid dimensions (15×15 cross pattern) to index cells
- Detect pieces by dominant color in each cell region

**Technical challenges**:
- Lighting variations on Android screen: Mitigate with automatic white balance / exposure compensation
- Screen rotation: Fix via screenshot orientation metadata or rotation detection
- Emulator vs real device: Both produce stable screenshots but differ in color calibration
- Performance: Target <100ms per frame for interactive response

---

## 2. ADB Screenshot and Interaction

### Current State

ADB (Android Debug Bridge) provides robust screenshot capture and input simulation for Android devices and emulators. For Linux hosts, the workflow is well-documented:

**Screenshot capture**:
```bash
# Method 1: Direct to file (slower)
adb shell screencap -p /sdcard/screen.png && adb pull /sdcard/screen.png

# Method 2: Streaming via stdout (faster)
adb exec-out screencap -p > screenshot.png

# Method 3: To clipboard on Linux
adb exec-out screencap -p | xclip -t image/png
```

**Input interaction**:
```bash
# Tap at coordinates
adb shell input tap <x> <y>

# Swipe gesture
adb shell input swipe <x1> <y1> <x2> <y2> <duration_ms>

# Text input
adb shell input text "text"

# Key events
adb shell input keyevent <KEYCODE>
```

### Key Technical Details

- **Performance**: `exec-out` streams directly, avoiding SD card I/O — critical for real-time detection
- **Coordinate system**: Uses display resolution; ensure emulator window size matches logical density
- **Touch precision**: On high-DPI displays, coordinates map 1:1 to logical pixels
- **Screencap binary**: Available on all modern Android (4.0+); no root required

**Recommended approach**: Use `exec-out` streaming for minimal latency
- Combine with subprocess piping to avoid intermediate storage
- Parse PNG directly into OpenCV: `cv2.imdecode(np.frombuffer(data, dtype=np.uint8), 1)`

**Technical challenges**:
- Multiple devices: Use `-s <serial>` to target specific device/emulator
- Latency: Minimize by avoiding file I/O; target <200ms total cycle
- Screen capture restrictions: Some apps (banking, DRM) enable FLAG_SECURE; Parchís game apps likely allow it
-Orientation handling: Some emulators capture rotated; detect via screenshot metadata or Exif

---

## 3. Linux Overlay Window

### Current State

Creating a transparent overlay window on Linux requires either X11 or Wayland support. For a pathfinding tool, the overlay should highlight predicted moves, show crosshair selection, or draw move paths over the emulator window.

### Approaches

| Approach | Protocol | Transparency | Click-Through | Complexity | Compatibility |
|----------|----------|-------------|---------------|------------|---------------|
| X11 override-redirect | X11 | Yes (alpha channel) | Yes (input shape) | Medium | Wide (all X11) |
| Wayland layer-shell | Wayland | Yes | Yes | Medium | Compositor-specific |
| bbox-overlay (Python) | X11/Tkinter | Yes | Yes | Low | X11 only |
| wayscriber | Wayland | Yes | Yes (with config) | Low | Wayland compositors |
| GTK overlay | X11/GTK | Yes | Yes | Medium | Wide |

### Recommended Approach

**For X11**: Use Python with PyGObject + Cairo for a lightweight overlay
- Create window with `override_redirect=True` for no window decorations
- Set `WindowTransparentForInput` hint for click-through
- Use RGBA colormap for transparency
- Position over emulator via window geometry matching

**For Wayland**: Use existing tools (wayscriber) or bind to layer-shell protocol
- Layer-shell provides proper always-on-top with compositor support
- Hyprland, Sway, KDE Wayland support layer-shell natively

**Python implementation sketch (X11)**:
```python
import cairo
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk

class Overlay(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self)
        self.set_decorated(False)
        self.set_override_redirect(True)
        self.set_keep_above(True)
        self.set_app_paintable(True)
        # For click-through, use input shape:
        self.input_shape_combine_region(cairo.Region(cairo.RectangleInt(0, 0, 0, 0)))

win = Overlay()
win.fullscreen()
```

**Technical challenges**:
- Compositor interference: X11 compositors (picom, compton) may conflict; test overlay vs composite manager
- Monitor coordinates: Must match emulator window position; use `xdotool` or `wmctrl` to query geometry
- Refresh sync: Overlay updates should not cause full-screen redraw; use damage tracking
- DPI scaling: Handle HiDPI displays (scale coordinates by gdk_scale_factor)

---

## 4. Parchís/Ludo Game Mechanics

### Game Overview

Parchís (known as Ludo in English, Parcheesi in the US) is a 2–4 player racing board game where each player moves 4 tokens from their home base, around the board, into the center home.

### Board Layout

The board is a 15×15 cross pattern with:

- **4 home bases**: Colored corners (Red, Blue, Yellow, Green) — 6×6 squares each
- **Main track**: 52 squares forming a cross pattern (outer track)
- **4 entry squares**: First square after each home base
- **4 home columns**: 6 colored squares leading to center
- **Home triangle**: Center area where winning tokens go

### Game Rules

| Rule | Parchís (Spain) | Ludo (Standard) | Notes |
|------|-----------------|----------------|-------|
| Start requirement | Roll 6 to exit base | Roll 6 to exit base | Universal |
| Extra turn | Roll 6 grants extra turn | Roll 6 grants extra turn | Universal |
| Three 6s in row | Allowed, 3 extra turns | Lose turn (some variants) | Parchís more lenient |
| Capture | Landing on opponent sends to base | Landing on opponent sends to base | Universal |
| Safe squares | Star-marked squares | Globe/star squares | Some variants differ |
| Blockades | Two same-color tokens block passage | Blockade blocks opponents | Universal |
| Entering home column | After full circuit | After full circuit | Universal |
| Winning | Exact roll to enter center | Exact roll to enter center | Universal |

### Key Pathfinding Considerations

**Board path representation**:
- Outer track: 52 squares indexed 0–51 (cyclical)
- Each player's entry point differs: Red enters at square 0, others offset by 13
- Home column: 6 squares leading to center (distinct from main track)

**Safe squares** (by position in track):
- Typically 8 safe squares per color (pre-entry and some mid-track positions)
- Star or globe symbols indicate safety from capture
- Starting squares (entry points) are safe

**Movement logic**:
- Tokens in base: Require 6 to move to entry square
- Tokens on track: Move clockwise by die roll
- Entering home: After completing 57-space circuit (52 track + 5 to center column entry + 6 home = 57)
- Exact roll required to enter final center

**Strategic implications for pathfinding**:
- Prioritize 6s to bring tokens out early
- Target opponent tokens near base (easier to recapture after sending back)
- Avoid unsafe squares when opponent has tokens nearby
- Blockade formation (2 tokens) blocks opponents unconditionally

---

## 5. Project Integration Summary

### Recommended Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Linux Host     │     │  ADB Bridge     │     │  Android Emulator│
│                 │     │                 │     │                 │
│ ┌─────────────┐ │────▶│  exec-out       │────▶│  ┌───────────┐  │
│ │Screenshot  │ │     │  screencap -p   │     │  │ Parchís   │  │
│ │Capture     │ │     │                 │     │  │ Game      │  │
│ └─────────────┘ │     └─────────────────┘     │  └───────────┘  │
│        │         │                               └─────────────────┘
│        ▼         │
│ ┌─────────────┐ │
│ │OpenCV      │ │
│ │Detection   │ │     ┌─────────────────┐
│ │- Board     │ │     │  Input Command │
│ │- Pieces    │ │◀────│  adb shell     │
│ │- State     │ │     │  input tap/swipe│
│ └─────────────┘ │     └─────────────────┘
│        │         │
│        ▼         │
│ ┌─────────────┐ │
│ │Pathfinding  │ │     ┌─────────────────┐
│ │- Move calc │ │     │  Overlay Window │
│ │- Strategy  │ │◀────│  (X11/Wayland)  │
│ └─────────────┘ │     │  - Highlights   │
│        │         │     │  - Crosshair   │
│        ▼         │     └─────────────────┘
│ ┌──��─��────────┐ │
│ │Action      │ │
│ │Execution   │ │
│ └─────────────┘ │
└─────────────────┘
```

### Key Libraries

| Component | Library | Package |
|-----------|---------|---------|
| Computer Vision | OpenCV | `opencv-python` or `opencv-python-headless` |
| Image processing | NumPy | `numpy` |
| ADB wrapper | subprocess (native) | Built-in |
| Overlay (X11) | PyGObject + Cairo | `python3-gi`, `python3-cairo` |
| Overlay (Wayland) | wayscriber or custom | External |
| Coordinate matching | Pillow | `pillow` |

### Technical Challenges and Mitigations

| Challenge | Risk Level | Mitigation |
|-----------|-----------|------------|
| Screen capture latency | Medium | Use `exec-out` streaming; parallelize capture/processing |
| Color detection accuracy | Medium | Calibrate HSV thresholds per emulator; use adaptive threshold |
| Overlay alignment | Medium | Query emulator window geometry; implement manual calibration UI |
| Emulator window resize | Low | Implement window geometry polling; prompt user on mismatch |
| FLAG_SECURE capture block | Low | Most game apps don't enable it; verify with test app |
| Wayland vs X11 compatibility | Medium | Detect session type; provide fallback for both |

### Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Game UI changes breaking detection | Medium | High | Version detection; configurable thresholds |
| Overlay doesn't track emulator window | Medium | Medium | Pin coordinates; auto-reposition on focus change |
| ADB connection instability | Low | Medium | Auto-reconnect loop; timeout handling |
| Performance too slow for real-time | Medium | Medium | Optimize detection to <100ms; use async pipeline |
| Cross-platform ( Wayland vs X11) | Low | Low | Dual implementation; detect session at startup |

### Feasibility Assessment

**Overall feasibility: HIGH**

This is a well-scoped project with:

- Established, proven technologies for each component
- Clear separation of concerns (capture → detect → pathfind → overlay → actuate)
- Active open-source tools for overlay display (wayscriber, bbox-overlay)
- No root required; works with standard Android emulator

**Recommended implementation order**:

1. **Phase 1**: ADB screenshot capture → verify connectivity
2. **Phase 2**: OpenCV board detection → extract state matrix
3. **Phase 3**: Basic pathfinding → suggest legal moves
4. **Phase 4**: Overlay window → highlight suggestions
5. **Phase 5**: Input integration → tap to move

---

## 6. Next Steps

To proceed from exploration to implementation:

1. **Verify ADB connectivity**: Confirm emulator is detected and `screencap` works
2. **Collect test images**: Capture 10+ screenshots of Parchís game in various states
3. **Create detection prototype**: Test HSV color thresholds on captured images
4. **Define board geometry**: Map screenshot pixels to board coordinates empirically
5. **Test overlay positioning**: Verify overlay tracks emulator window correctly

**Clarifying questions for user**:

- Is this tool for a specific Parchís app (e.g., Parchís VIP, Ludo Star), or should it adapt to multiple apps?
- Should the tool provide suggested moves, or fully automate gameplay?
- Is there a preference between X11 and Wayland for the overlay?

---

## References

- OpenCV color detection: `cv2.cvtColor()`, HSV threshold ranges
- ADB screencap: Official Android documentation
- X11 overlay: Cairo + XCreateWindow with override_redirect
- Wayland overlay: layer-shell protocol via wayscriber/koverlay
- Parchís rules: Standard international Ludo rules with Spanish variations