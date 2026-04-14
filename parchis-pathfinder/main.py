#!/usr/bin/env python3
"""
Parchís Pathfinding Tool - Main CLI

A tool that calculates optimal moves in Parchís using computer vision
and heuristic scoring, with overlay display on Linux.
"""

import argparse
import sys
import os
import logging
import signal
import time
from typing import Optional

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.adb_connector import ADBConnector
from src.adb_connector.connector import ADBConnectionError
from src.cv_detector import BoardDetector, BoardState
from src.pathfinder import PathfinderEngine, MoveRecommendation
from src.overlay import create_overlay
from src.calibration import CalibrationTool
from config.manager import ConfigManager


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ParchisPathfinder:
    """Main application class for Parchís Pathfinding."""
    
    def __init__(self, config_dir: Optional[str] = None, debug: bool = False):
        """Initialize the application."""
        self.config = ConfigManager(config_dir)
        self.adb: Optional[ADBConnector] = None
        self.detector: Optional[BoardDetector] = None
        self.pathfinder: Optional[PathfinderEngine] = None
        self.overlay = None
        
        # Update logging level
        if debug or self.config.get('debug.enabled', False):
            logging.getLogger().setLevel(logging.DEBUG)
    
    def connect(self) -> bool:
        """Connect to the emulator via ADB."""
        try:
            host = self.config.get('adb.host', '127.0.0.1')
            port = self.config.get('adb.port', 5555)
            
            self.adb = ADBConnector(host=host, port=port)
            self.adb.connect()
            
            logger.info(f"Connected to emulator at {host}:{port}")
            return True
            
        except ADBConnectionError as e:
            logger.error(f"Connection failed: {e}")
            return False
    
    def initialize_components(self):
        """Initialize detection and pathfinding components."""
        # Get calibration
        calibration = self.config.calibration
        
        # Initialize detector with calibration
        hsv_ranges = self.config.get_hsv_ranges()
        self.detector = BoardDetector(hsv_ranges=hsv_ranges, calibration=calibration)
        
        # Initialize pathfinder with calibration
        self.pathfinder = PathfinderEngine(calibration=calibration)
        
        # Initialize overlay
        overlay_enabled = self.config.get('overlay.enabled', True)
        if overlay_enabled:
            self.overlay = create_overlay()
            if not self.overlay.is_available():
                logger.warning("Overlay not available, running in text-only mode")
        
        logger.info("Components initialized")
    
    def capture_screenshot(self, save_path: Optional[str] = None):
        """Capture a screenshot from the emulator."""
        if not self.adb or not self.adb.is_connected():
            logger.error("Not connected to emulator")
            return None
        
        try:
            screenshot = self.adb.get_screenshot()
            
            if save_path:
                import cv2
                cv2.imwrite(save_path, screenshot)
                logger.info(f"Screenshot saved to {save_path}")
            
            return screenshot
            
        except ADBConnectionError as e:
            logger.error(f"Screenshot capture failed: {e}")
            return None
    
    def detect_board(self, screenshot=None) -> Optional[BoardState]:
        """Detect board state from screenshot."""
        if screenshot is None:
            screenshot = self.capture_screenshot()
        
        if screenshot is None:
            logger.error("No screenshot available")
            return None
        
        if not self.detector:
            self.initialize_components()
        
        board_state = self.detector.detect(screenshot)
        logger.info(f"Board detected with confidence: {board_state.confidence:.2f}")
        
        return board_state
    
    def calculate_move(self, player: str, dice_roll: int, 
                       board_state: Optional[BoardState] = None) -> Optional[MoveRecommendation]:
        """Calculate the best move for a player."""
        if board_state is None:
            board_state = self.detect_board()
        
        if board_state is None:
            logger.error("No board state available")
            return None
        
        if not self.pathfinder:
            self.initialize_components()
        
        recommendation = self.pathfinder.calculate_best_move(
            board_state, player.lower(), dice_roll
        )
        
        if recommendation:
            desc = self.pathfinder.get_move_description(recommendation)
            logger.info(f"Best move: {desc}")
        else:
            logger.info("No valid moves available")
        
        return recommendation
    
    def show_overlay(self, recommendation: MoveRecommendation, 
                     x: int = 0, y: int = 0):
        """Show recommendation in overlay."""
        if not self.overlay:
            logger.warning("Overlay not available")
            return
        
        message = self.pathfinder.get_move_description(recommendation)
        self.overlay.show_recommendation(x, y, message=message)
    
    def run_realtime(self, player: str, delay: float = 2.0):
        """Run in real-time mode, calculating moves continuously."""
        logger.info(f"Starting real-time mode for {player} (Ctrl+C to stop)")
        
        try:
            while True:
                # Capture and detect
                screenshot = self.capture_screenshot()
                if screenshot is None:
                    logger.error("Failed to capture screenshot")
                    time.sleep(delay)
                    continue
                
                board_state = self.detect_board(screenshot)
                
                # Get dice roll (would need manual input or OCR)
                # For now, use a placeholder
                logger.info("Enter dice roll (1-6): ", end="")
                dice_input = input().strip()
                
                try:
                    dice_roll = int(dice_input)
                    if dice_input not in '123456':
                        continue
                except ValueError:
                    continue
                
                # Calculate and show move
                recommendation = self.pathfinder.calculate_best_move(
                    board_state, player.lower(), dice_roll
                )
                
                if recommendation:
                    # Show overlay (position would need to be calculated from board state)
                    message = self.pathfinder.get_move_description(recommendation)
                    logger.info(f"RECOMMENDED: {message}")
                    
                    # For now, show at center of screen
                    if self.overlay:
                        self.overlay.show_recommendation(
                            500, 300, message=message
                        )
                else:
                    logger.info("No valid moves")
                    if self.overlay:
                        self.overlay.show_recommendation(
                            500, 300, message="No valid moves"
                        )
                
                time.sleep(delay)
                
        except KeyboardInterrupt:
            logger.info("Stopping real-time mode")
            if self.overlay:
                self.overlay.clear()
    
    def calibrate(self, screenshot=None):
        """Launch calibration tool."""
        if screenshot is None:
            screenshot = self.capture_screenshot()
        
        tool = CalibrationTool(screenshot=screenshot)
        calibration = tool.launch()
        
        if calibration:
            self.config.update_calibration(calibration)
            logger.info("Calibration updated")
    
    def cleanup(self):
        """Clean up resources."""
        if self.adb:
            self.adb.disconnect()
        
        if self.overlay:
            self.overlay.close()
        
        logger.info("Cleanup complete")


def create_parser() -> argparse.ArgumentParser:
    """Create command line argument parser."""
    parser = argparse.ArgumentParser(
        description='Parchís Pathfinding Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s capture                    Capture a screenshot
  %(prog)s detect                     Detect board state
  %(prog)s move blue 6                Calculate best move for blue with dice 6
  %(prog)s overlay                    Run real-time overlay
  %(prog)s calibrate                  Launch calibration tool
        """
    )
    
    parser.add_argument(
        '--config', '-c',
        default=None,
        help='Configuration directory path'
    )
    
    parser.add_argument(
        '--debug', '-d',
        action='store_true',
        help='Enable debug logging'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # capture command
    subparsers.add_parser('capture', help='Capture screenshot from emulator')
    
    # detect command
    subparsers.add_parser('detect', help='Detect board state from screenshot')
    
    # move command
    move_parser = subparsers.add_parser('move', help='Calculate best move')
    move_parser.add_argument('player', choices=['blue', 'yellow', 'green', 'red'],
                           help='Player color')
    move_parser.add_argument('roll', type=int, help='Dice roll value (1-6)')
    
    # overlay command
    overlay_parser = subparsers.add_parser('overlay', help='Run real-time overlay')
    overlay_parser.add_argument('player', choices=['blue', 'yellow', 'green', 'red'],
                              help='Player color')
    overlay_parser.add_argument('--delay', type=float, default=2.0,
                              help='Delay between updates (seconds)')
    
    # calibrate command
    subparsers.add_parser('calibrate', help='Launch calibration tool')
    
    return parser


def main():
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Create application
    app = ParchisPathfinder(
        config_dir=args.config,
        debug=args.debug
    )
    
    # Set up signal handlers
    def signal_handler(sig, frame):
        logger.info("Interrupted, cleaning up...")
        app.cleanup()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Execute command
    try:
        if args.command == 'capture':
            if not app.connect():
                return 1
            app.initialize_components()
            screenshot = app.capture_screenshot('screenshot.png')
            if screenshot:
                print(f"Screenshot captured: {screenshot.shape}")
                return 0
            return 1
        
        elif args.command == 'detect':
            if not app.connect():
                return 1
            app.initialize_components()
            board_state = app.detect_board()
            if board_state:
                print(f"Board detected:")
                print(f"  Confidence: {board_state.confidence:.2f}")
                for color, state in board_state.players.items():
                    active = len(state.get_active_pieces())
                    in_base = len(state.get_pieces_in_base())
                    in_goal = len(state.get_pieces_in_goal())
                    print(f"  {color.value}: {active} active, {in_base} base, {in_goal} goal")
                return 0
            return 1
        
        elif args.command == 'move':
            if not app.connect():
                return 1
            app.initialize_components()
            recommendation = app.calculate_move(args.player, args.roll)
            if recommendation:
                desc = app.pathfinder.get_move_description(recommendation)
                print(f"RECOMMENDED: {desc}")
                return 0
            print("No valid moves available")
            return 1
        
        elif args.command == 'overlay':
            if not app.connect():
                return 1
            app.initialize_components()
            app.run_realtime(args.player, args.delay)
            return 0
        
        elif args.command == 'calibrate':
            if not app.connect():
                return 1
            app.initialize_components()
            app.calibrate()
            return 0
    
    finally:
        app.cleanup()
    
    return 0


if __name__ == '__main__':
    sys.exit(main())