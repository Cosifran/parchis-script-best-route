"""
Calibration Tool for Parchís Pathfinding.

Interactive tool for calibrating board detection and overlay positioning.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import numpy as np
import cv2
from typing import Optional, Dict, List, Tuple
import logging
import yaml

logger = logging.getLogger(__name__)


class CalibrationTool:
    """
    Interactive calibration tool using Tkinter.
    
    Allows users to:
    - Select board corners for perspective transform
    - Pick colors for each player
    - Test detection and see results
    - Save/load calibration to YAML
    """
    
    def __init__(self, screenshot: Optional[np.ndarray] = None):
        """
        Initialize calibration tool.
        
        Args:
            screenshot: Initial screenshot for calibration
        """
        self.screenshot = screenshot
        self.root = None
        self.canvas = None
        
        # Calibration data
        self.corners = {
            'top_left': (0.1, 0.1),
            'top_right': (0.9, 0.1),
            'bottom_left': (0.1, 0.9),
            'bottom_right': (0.9, 0.9),
        }
        
        self.hsv_ranges = {
            'blue': {'lower': (100, 150, 50), 'upper': (140, 255, 255)},
            'yellow': {'lower': (20, 150, 150), 'upper': (30, 255, 255)},
            'green': {'lower': (40, 100, 50), 'upper': (80, 255, 255)},
            'red': {'lower': (0, 150, 100), 'upper': (10, 255, 255)},
        }
        
        self.selected_corner = None
        self.selected_color = None
        
        # Current values for color picker
        self.current_hsv = {'h': 0, 's': 0, 'v': 0}
    
    def launch(self) -> Optional[dict]:
        """
        Launch the calibration UI.
        
        Returns:
            Calibration dictionary, or None if cancelled
        """
        self.root = tk.Tk()
        self.root.title("Parchís Pathfinder - Calibration Tool")
        self.root.geometry("1200x800")
        
        # Create main container
        main_container = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # Left panel: Image display
        left_frame = ttk.Frame(main_container, width=800)
        main_container.add(left_frame, weight=3)
        
        # Canvas for image display
        self.canvas = tk.Canvas(left_frame, bg="black")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # Right panel: Controls
        right_frame = ttk.Frame(main_container, width=300)
        main_container.add(right_frame, weight=1)
        
        # Control sections
        self._create_corner_controls(right_frame)
        self._create_color_controls(right_frame)
        self._create_action_buttons(right_frame)
        
        # Bind mouse events
        self.canvas.bind("<Button-1>", self._on_canvas_click)
        
        # If screenshot provided, display it
        if self.screenshot is not None:
            self._display_screenshot()
        
        # Start UI
        self.root.mainloop()
        
        # Return calibration data
        return self.get_calibration()
    
    def _create_corner_controls(self, parent: ttk.Frame):
        """Create corner selection controls."""
        corner_frame = ttk.LabelFrame(parent, text="Board Corners", padding=10)
        corner_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(corner_frame, text="Click 4 corners on the board:").pack(anchor=tk.W)
        
        self.corner_vars = {}
        corners = ['top_left', 'top_right', 'bottom_left', 'bottom_right']
        corner_labels = ['Top-Left', 'Top-Right', 'Bottom-Left', 'Bottom-Right']
        
        for corner, label in zip(corners, corner_labels):
            var = tk.StringVar(value="Not set")
            self.corner_vars[corner] = var
            ttk.Label(corner_frame, text=f"{label}:").pack(anchor=tk.W)
            ttk.Label(corner_frame, textvariable=var, foreground="blue").pack(anchor=tk.W)
        
        ttk.Button(corner_frame, text="Reset Corners", 
                   command=self._reset_corners).pack(pady=5)
    
    def _create_color_controls(self, parent: ttk.Frame):
        """Create color picker controls."""
        color_frame = ttk.LabelFrame(parent, text="Color Ranges (HSV)", padding=10)
        color_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(color_frame, text="Select player color to calibrate:").pack(anchor=tk.W)
        
        self.color_vars = {}
        colors = ['blue', 'yellow', 'green', 'red']
        
        for color in colors:
            var = tk.StringVar(value=f"Set")
            self.color_vars[color] = var
            
            btn = ttk.Button(color_frame, text=f"{color.upper()}", 
                           command=lambda c=color: self._select_color(c))
            btn.pack(fill=tk.X, pady=2)
            
            ttk.Label(color_frame, textvariable=var, 
                     font=("Courier", 9)).pack(anchor=tk.W)
        
        # HSV sliders (use tk.Scale instead of ttk.Scale for label support)
        ttk.Label(color_frame, text="Hue (0-179):").pack(anchor=tk.W)
        self.h_slider = tk.Scale(color_frame, from_=0, to=179, 
                                  orient=tk.HORIZONTAL,
                                  command=self._update_hsv)
        self.h_slider.pack(fill=tk.X, pady=2)
        
        ttk.Label(color_frame, text="Saturation (0-255):").pack(anchor=tk.W)
        self.s_slider = tk.Scale(color_frame, from_=0, to=255, 
                                  orient=tk.HORIZONTAL,
                                  command=self._update_hsv)
        self.s_slider.pack(fill=tk.X, pady=2)
        
        ttk.Label(color_frame, text="Value (0-255):").pack(anchor=tk.W)
        self.v_slider = tk.Scale(color_frame, from_=0, to=255, 
                                  orient=tk.HORIZONTAL,
                                  command=self._update_hsv)
        self.v_slider.pack(fill=tk.X, pady=2)
        
        self.hsv_label = ttk.Label(color_frame, text="HSV: (0, 0, 0)")
        self.hsv_label.pack(pady=5)
        
        # Set button
        ttk.Button(color_frame, text="Set Range", 
                  command=self._set_hsv_range).pack(pady=5)
    
    def _create_action_buttons(self, parent: ttk.Frame):
        """Create action buttons."""
        action_frame = ttk.Frame(parent, padding=10)
        action_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        ttk.Button(action_frame, text="Load Screenshot", 
                  command=self._load_screenshot).pack(fill=tk.X, pady=5)
        
        ttk.Button(action_frame, text="Test Detection", 
                  command=self._test_detection).pack(fill=tk.X, pady=5)
        
        ttk.Button(action_frame, text="Save Calibration", 
                  command=self._save_calibration).pack(fill=tk.X, pady=5)
        
        ttk.Button(action_frame, text="Load Calibration", 
                  command=self._load_calibration).pack(fill=tk.X, pady=5)
        
        ttk.Separator(action_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
        
        ttk.Button(action_frame, text="Apply & Close", 
                  command=self._apply_and_close).pack(fill=tk.X, pady=5)
        
        ttk.Button(action_frame, text="Cancel", 
                  command=self._cancel).pack(fill=tk.X, pady=5)
    
    def _on_canvas_click(self, event):
        """Handle canvas click for corner selection."""
        if self.screenshot is None:
            return
        
        # Get canvas dimensions
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        # Calculate relative position
        rel_x = event.x / canvas_width
        rel_y = event.y / canvas_height
        
        if self.selected_corner:
            # Set corner position
            self.corners[self.selected_corner] = (rel_x, rel_y)
            self.corner_vars[self.selected_corner].set(
                f"({rel_x:.2f}, {rel_y:.2f})"
            )
            self.selected_corner = None
            
            # Redraw
            self._display_screenshot()
            
            messagebox.showinfo("Corner Set", 
                               f"Corner set to ({rel_x:.2f}, {rel_y:.2f})")
    
    def _select_color(self, color: str):
        """Select a color for calibration."""
        self.selected_color = color
        
        # Update display
        for c in ['blue', 'yellow', 'green', 'red']:
            self.color_vars[c].set("Set" if c == color else "")
        
        # Set slider values to current range
        lower = self.hsv_ranges[color]['lower']
        upper = self.hsv_ranges[color]['upper']
        
        # Use middle of range
        self.h_slider.set((lower[0] + upper[0]) // 2)
        self.s_slider.set((lower[1] + upper[1]) // 2)
        self.v_slider.set((lower[2] + upper[2]) // 2)
        
        messagebox.showinfo("Color Selected", 
                           f"Adjust sliders to set {color.upper()} range")
    
    def _update_hsv(self, _=None):
        """Update HSV display."""
        h = int(self.h_slider.get())
        s = int(self.s_slider.get())
        v = int(self.v_slider.get())
        
        self.current_hsv = {'h': h, 's': s, 'v': v}
        self.hsv_label.config(text=f"HSV: ({h}, {s}, {v})")
    
    def _set_hsv_range(self):
        """Set HSV range for selected color."""
        if not self.selected_color:
            messagebox.showwarning("No Color", "Select a color first")
            return
        
        h = int(self.h_slider.get())
        s = int(self.s_slider.get())
        v = int(self.v_slider.get())
        
        # Create range around current value
        h_margin = 15 if h > 10 else h
        s_margin = 50
        v_margin = 50
        
        lower = (max(0, h - h_margin), max(0, s - s_margin), max(0, v - v_margin))
        upper = (min(179, h + h_margin), min(255, s + s_margin), min(255, v + v_margin))
        
        self.hsv_ranges[self.selected_color] = {
            'lower': lower,
            'upper': upper
        }
        
        self.color_vars[self.selected_color].set(f"({lower[0]}-{upper[0]}, {lower[1]}-{upper[1]}, {lower[2]}-{upper[2]})")
        
        messagebox.showinfo("Range Set", 
                           f"{self.selected_color.upper()} range updated")
    
    def _display_screenshot(self):
        """Display screenshot on canvas with corner markers."""
        if self.screenshot is None:
            return
        
        try:
            # Convert BGR to RGB for display
            img_rgb = cv2.cvtColor(self.screenshot, cv2.COLOR_BGR2RGB)
            
            # Convert to PhotoImage
            from PIL import Image, ImageTk
            
            # Force update to get canvas dimensions
            self.root.update()
            
            # Resize to fit canvas
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
            
            # If canvas not yet rendered, use default
            if canvas_width <= 1:
                canvas_width = 800
            if canvas_height <= 1:
                canvas_height = 600
            
            img_height, img_width = img_rgb.shape[:2]
            
            # Validate image dimensions
            if img_width <= 0 or img_height <= 0:
                print("Error: Invalid image dimensions")
                return
            
            scale = min(canvas_width / img_width, canvas_height / img_height)
            
            # Ensure scale is valid
            if scale <= 0 or not (0 < scale < 1000):
                scale = 1.0
            
            new_width = max(1, int(img_width * scale))
            new_height = max(1, int(img_height * scale))
            
            img_resized = cv2.resize(img_rgb, (new_width, new_height))
            
            self.photo = ImageTk.PhotoImage(Image.fromarray(img_resized))
            
            # Display
            self.canvas.delete("all")
            self.canvas.configure(width=new_width, height=new_height)
            self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo)
            
            # Draw corner markers
            for corner, (rx, ry) in self.corners.items():
                x = rx * new_width
                y = ry * new_height
                
                color = "yellow" if corner in ['top_left', 'bottom_right'] else "cyan"
                self.canvas.create_oval(x-10, y-10, x+10, y+10, outline=color, width=2)
                self.canvas.create_text(x, y-15, text=corner.replace('_', ' '), fill=color)
                
        except Exception as e:
            print(f"Error displaying screenshot: {e}")
    
    def _load_screenshot(self):
        """Load a screenshot file."""
        filename = filedialog.askopenfilename(
            title="Select Screenshot",
            filetypes=[("Images", "*.png *.jpg *.jpeg"), ("All", "*.*")]
        )
        
        if filename:
            self.screenshot = cv2.imread(filename)
            self._display_screenshot()
            messagebox.showinfo("Loaded", f"Loaded: {filename}")
    
    def _test_detection(self):
        """Test detection with current calibration."""
        if self.screenshot is None:
            messagebox.showwarning("No Image", "Load a screenshot first")
            return
        
        messagebox.showinfo("Test", "Detection test would run here.\n"
                          "This requires connecting to CV detector.")
    
    def _save_calibration(self):
        """Save calibration to file."""
        filename = filedialog.asksaveasfilename(
            title="Save Calibration",
            defaultextension=".yaml",
            filetypes=[("YAML", "*.yaml"), ("All", "*.*")]
        )
        
        if filename:
            calibration = self.get_calibration()
            with open(filename, 'w') as f:
                yaml.dump(calibration, f)
            messagebox.showinfo("Saved", f"Calibration saved to: {filename}")
    
    def _load_calibration(self):
        """Load calibration from file."""
        filename = filedialog.askopenfilename(
            title="Load Calibration",
            filetypes=[("YAML", "*.yaml"), ("All", "*.*")]
        )
        
        if filename:
            with open(filename, 'r') as f:
                calibration = yaml.safe_load(f)
            
            self.corners = calibration.get('corners', self.corners)
            self.hsv_ranges = calibration.get('hsv_ranges', self.hsv_ranges)
            
            # Update UI
            for corner, (rx, ry) in self.corners.items():
                self.corner_vars[corner].set(f"({rx:.2f}, {ry:.2f})")
            
            for color, range_dict in self.hsv_ranges.items():
                lower = range_dict['lower']
                upper = range_dict['upper']
                self.color_vars[color].set(f"({lower[0]}-{upper[0]}, {lower[1]}-{upper[1]}, {lower[2]}-{upper[2]})")
            
            if self.screenshot:
                self._display_screenshot()
            
            messagebox.showinfo("Loaded", f"Calibration loaded from: {filename}")
    
    def _apply_and_close(self):
        """Apply calibration and close."""
        self.calibration_applied = True
        self.root.quit()
    
    def _cancel(self):
        """Cancel calibration."""
        self.calibration_applied = False
        self.root.quit()
    
    def _reset_corners(self):
        """Reset corner positions."""
        self.corners = {
            'top_left': (0.1, 0.1),
            'top_right': (0.9, 0.1),
            'bottom_left': (0.1, 0.9),
            'bottom_right': (0.9, 0.9),
        }
        
        for corner, var in self.corner_vars.items():
            rx, ry = self.corners[corner]
            var.set(f"({rx:.2f}, {ry:.2f})")
        
        if self.screenshot:
            self._display_screenshot()
    
    def get_calibration(self) -> dict:
        """Get current calibration data."""
        return {
            'corners': self.corners,
            'hsv_ranges': self.hsv_ranges,
            'offset': (0, 0),
        }
    
    def set_screenshot(self, screenshot: np.ndarray):
        """Set screenshot for calibration."""
        self.screenshot = screenshot


def launch_calibration(screenshot: Optional[np.ndarray] = None) -> Optional[dict]:
    """
    Launch the calibration tool.
    
    Args:
        screenshot: Initial screenshot
        
    Returns:
        Calibration dictionary or None
    """
    tool = CalibrationTool(screenshot=screenshot)
    return tool.launch()