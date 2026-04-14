"""
Overlay Renderer for Parchís Pathfinding.

Displays move recommendations via transparent X11 overlay.
"""

import logging
from typing import Optional, Tuple
import numpy as np

logger = logging.getLogger(__name__)

# Try to import X11 libraries
try:
    import gi
    gi.require_version('Gtk', '3.0')
    gi.require_version('Gdk', '3.0')
    from gi.repository import Gtk, Gdk, GdkPixbuf
    import cairo
    X11_AVAILABLE = True
except ImportError:
    X11_AVAILABLE = False
    logger.warning("X11/Gtk libraries not available. Overlay will be disabled.")


class OverlayRenderer:
    """
    Renders move recommendations as transparent X11 overlay.
    
    Uses a transparent override-redirect window to display highlights
    without interfering with other applications.
    """
    
    def __init__(self, screen_x: int = 0, screen_y: int = 0,
                 screen_width: int = 1920, screen_height: int = 1080):
        """
        Initialize overlay renderer.
        
        Args:
            screen_x: Screen X offset
            screen_y: Screen Y offset
            screen_width: Screen width
            screen_height: Screen height
        """
        self.screen_x = screen_x
        self.screen_y = screen_y
        self.screen_width = screen_width
        self.screen_height = screen_height
        
        self.window = None
        self.overlay_x = 0
        self.overlay_y = 0
        self.overlay_width = 100
        self.overlay_height = 100
        self.message = ""
        self.visible = False
        
        if not X11_AVAILABLE:
            logger.error("X11 not available. Cannot create overlay.")
            return
        
        self._init_window()
    
    def _init_window(self):
        """Initialize transparent overlay window."""
        try:
            # Create off-screen window
            self.window = Gtk.Window(Gtk.WindowType.TOPLEVEL)
            self.window.set_decorated(False)
            self.window.set_resizable(False)
            self.window.set_skip_taskbar_hint(True)
            self.window.set_skip_pager_hint(True)
            self.window.set_keep_above(True)
            
            # Make window transparent
            screen = self.window.get_screen()
            rgba = screen.get_rgba_visual()
            if rgba:
                self.window.set_visual(rgba)
            
            # Override-redirect for borderless, always-on-top
            # This requires X11 specifics
            try:
                self.window.window.set_override_redirect(True)
            except:
                pass  # May not work on all systems
            
            # Connect draw event
            self.window.connect("draw", self._on_draw)
            
            # Set default size
            self.window.resize(self.overlay_width, self.overlay_height)
            
            logger.info("Overlay window initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize overlay: {e}")
            self.window = None
    
    def _on_draw(self, widget, cr):
        """Handle window redraw."""
        if not self.visible:
            return
        
        # Clear with transparency
        cr.set_source_rgba(0, 0, 0, 0)
        cr.set_operator(cairo.OPERATOR_SOURCE)
        cr.paint()
        
        # Draw highlight rectangle
        # Get window dimensions
        width = widget.get_allocated_width()
        height = widget.get_allocated_height()
        
        # Draw semi-transparent green rectangle
        cr.set_source_rgba(0, 1, 0, 0.3)  # Green, 30% opacity
        cr.set_operator(cairo.OPERATOR_OVER)
        
        # Draw rectangle with padding
        padding = 10
        cr.rectangle(padding, padding, 
                     width - 2*padding, height - 2*padding)
        cr.fill()
        
        # Draw border
        cr.set_source_rgba(0, 1, 0, 0.8)  # Green, 80% opacity
        cr.set_line_width(3)
        cr.rectangle(padding, padding, 
                     width - 2*padding, height - 2*padding)
        cr.stroke()
        
        # Draw message if available
        if self.message:
            # Draw text background
            text_x = padding + 5
            text_y = padding + 5
            
            cr.set_source_rgba(0, 0, 0, 0.7)
            cr.rectangle(text_x - 2, text_y - 2, 
                         width - 2*padding + 4, 20)
            cr.fill()
            
            # Draw text
            cr.set_source_rgba(1, 1, 1, 1)  # White
            cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
            cr.set_font_size(12)
            cr.move_to(text_x, text_y + 12)
            cr.show_text(self.message[:30])  # Truncate if too long
    
    def show_recommendation(self, x: int, y: int, 
                           width: int = 100, height: int = 100,
                           message: str = "") -> None:
        """
        Show move recommendation at specified position.
        
        Args:
            x: X pixel coordinate
            y: Y pixel coordinate
            width: Highlight width
            height: Highlight height
            message: Message to display
        """
        if not X11_AVAILABLE or not self.window:
            logger.debug(f"Overlay (mock): {message} at ({x}, {y})")
            return
        
        self.overlay_x = x
        self.overlay_y = y
        self.overlay_width = width
        self.overlay_height = height
        self.message = message
        
        # Move window to position
        self.window.move(x, y)
        self.window.resize(width, height)
        
        # Show window
        if not self.visible:
            self.window.show_all()
            self.visible = True
        
        # Force redraw
        self.window.queue_draw()
        
        # Process events
        while Gtk.events_pending():
            Gtk.main_iteration()
        
        logger.debug(f"Showed recommendation at ({x}, {y}): {message}")
    
    def update_position(self, x: int, y: int) -> None:
        """Update overlay position."""
        self.overlay_x = x
        self.overlay_y = y
        
        if self.window and self.visible:
            self.window.move(x, y)
            self.window.queue_draw()
    
    def clear(self) -> None:
        """Hide the overlay."""
        if self.window and self.visible:
            self.window.hide()
            self.visible = False
            logger.debug("Overlay cleared")
    
    def close(self) -> None:
        """Close and destroy the overlay."""
        if self.window:
            self.window.destroy()
            self.window = None
            self.visible = False
            logger.info("Overlay closed")
    
    def set_screen_geometry(self, x: int, y: int, 
                            width: int, height: int) -> None:
        """Update screen geometry for positioning."""
        self.screen_x = x
        self.screen_y = y
        self.screen_width = width
        self.screen_height = height
    
    def is_available(self) -> bool:
        """Check if overlay is available."""
        return X11_AVAILABLE and self.window is not None
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


class MockOverlayRenderer:
    """
    Mock overlay for testing or when X11 is not available.
    """
    
    def __init__(self, *args, **kwargs):
        self.visible = False
        self.last_position = (0, 0)
        self.last_message = ""
    
    def show_recommendation(self, x: int, y: int, 
                           width: int = 100, height: int = 100,
                           message: str = "") -> None:
        self.visible = True
        self.last_position = (x, y)
        self.last_message = message
        print(f"[MOCK OVERLAY] {message} at ({x}, {y})")
    
    def update_position(self, x: int, y: int) -> None:
        self.last_position = (x, y)
    
    def clear(self) -> None:
        self.visible = False
        print("[MOCK OVERLAY] cleared")
    
    def close(self) -> None:
        self.visible = False
    
    def set_screen_geometry(self, x: int, y: int, 
                            width: int, height: int) -> None:
        pass
    
    def is_available(self) -> bool:
        return False  # Mock is not "real" X11
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def create_overlay(screen_x: int = 0, screen_y: int = 0,
                   screen_width: int = 1920, screen_height: int = 1080,
                   use_mock: bool = False) -> OverlayRenderer:
    """
    Create an overlay renderer.
    
    Args:
        screen_x: Screen X offset
        screen_y: Screen Y offset
        screen_width: Screen width
        screen_height: Screen height
        use_mock: Force using mock renderer
        
    Returns:
        OverlayRenderer or MockOverlayRenderer
    """
    if use_mock or not X11_AVAILABLE:
        return MockOverlayRenderer()
    
    return OverlayRenderer(screen_x, screen_y, screen_width, screen_height)