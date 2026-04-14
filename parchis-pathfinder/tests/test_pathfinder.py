"""
Unit tests for Parchís Pathfinding heuristic scoring.

Tests all 7 heuristics with known board states.
"""

import pytest
from src.pathfinder import (
    PathfinderEngine, Move, MoveType, 
    MoveRecommendation, HeuristicResult
)
from src.cv_detector import BoardState, PlayerState, PlayerColor, PiecePosition


class TestHeuristicCapture:
    """Test capture heuristic (+100 points)."""
    
    def test_capture_heuristic(self):
        """+100 points when landing on opponent piece."""
        engine = PathfinderEngine()
        
        # Create board state with opponent piece at position 5
        board_state = self._create_test_board({
            'blue': [PiecePosition(PlayerColor.BLUE, 0, 5, False, False, 1.0)],
            'yellow': [PiecePosition(PlayerColor.YELLOW, 0, 5, False, False, 1.0)],
            'green': [],
            'red': [],
        })
        
        # Move blue piece to position 5 (where yellow is)
        move = Move('blue', 0, 3, 5, MoveType.CAPTURE, 2)
        
        score, result = engine.score_move(move, board_state, 'blue')
        
        assert result.capture == 100, f"Expected +100, got {result.capture}"
        assert score >= 100, f"Total score should include +100"


class TestHeuristicSafeZone:
    """Test safe zone heuristic (+50 points)."""
    
    def test_safe_zone_heuristic(self):
        """+50 points for moving to safe corridor/goal."""
        engine = PathfinderEngine()
        
        # Create empty board
        board_state = self._create_test_board({
            'blue': [PiecePosition(PlayerColor.BLUE, 0, 3, False, False, 1.0)],
            'yellow': [],
            'green': [],
            'red': [],
        })
        
        # Move to safe zone (position 8 is safe)
        move = Move('blue', 0, 3, 8, MoveType.ADVANCE, 5)
        
        score, result = engine.score_move(move, board_state, 'blue')
        
        assert result.safe_zone == 50, f"Expected +50, got {result.safe_zone}"
    
    def test_goal_is_safe(self):
        """Goal zone is also safe."""
        engine = PathfinderEngine()
        
        board_state = self._create_test_board({
            'blue': [PiecePosition(PlayerColor.BLUE, 0, 50, False, False, 1.0)],
            'yellow': [],
            'green': [],
            'red': [],
        })
        
        # Move to goal
        move = Move('blue', 0, 50, 53, MoveType.GOAL, 3)
        
        score, result = engine.score_move(move, board_state, 'blue')
        
        assert result.safe_zone == 50, f"Goal should give +50 safe zone"


class TestHeuristicBlockade:
    """Test blockade heuristic (+40 points)."""
    
    def test_blockade_heuristic(self):
        """+40 points when forming 2+ piece stack."""
        engine = PathfinderEngine()
        
        # Create board with two pieces at position 10
        board_state = self._create_test_board({
            'blue': [
                PiecePosition(PlayerColor.BLUE, 0, 8, False, False, 1.0),
                PiecePosition(PlayerColor.BLUE, 1, 10, False, False, 1.0),
            ],
            'yellow': [],
            'green': [],
            'red': [],
        })
        
        # Move piece from 8 to 10 (forms blockade with piece 1)
        move = Move('blue', 0, 8, 10, MoveType.ADVANCE, 2)
        
        score, result = engine.score_move(move, board_state, 'blue')
        
        assert result.blockade == 40, f"Expected +40, got {result.blockade}"


class TestHeuristicEnterBoard:
    """Test enter board heuristic (+30 points)."""
    
    def test_enter_board_heuristic(self):
        """+30 points when entering from base (roll 6)."""
        engine = PathfinderEngine()
        
        board_state = self._create_test_board({
            'blue': [PiecePosition(PlayerColor.BLUE, 0, -1, True, False, 1.0)],
            'yellow': [],
            'green': [],
            'red': [],
        })
        
        # Enter board from base
        move = Move('blue', 0, -1, 0, MoveType.ENTER, 6)
        
        score, result = engine.score_move(move, board_state, 'blue')
        
        assert result.enter_board == 30, f"Expected +30, got {result.enter_board}"


class TestHeuristicExactGoal:
    """Test exact goal heuristic (+20 points)."""
    
    def test_exact_goal_heuristic(self):
        """+20 points for exact roll to reach goal."""
        engine = PathfinderEngine()
        
        board_state = self._create_test_board({
            'blue': [PiecePosition(PlayerColor.BLUE, 0, 50, False, False, 1.0)],
            'yellow': [],
            'green': [],
            'red': [],
        })
        
        # Exact roll to reach goal (position 53 is 3 steps into blue goal)
        move = Move('blue', 0, 50, 53, MoveType.GOAL, 3)
        
        score, result = engine.score_move(move, board_state, 'blue')
        
        assert result.exact_goal == 20, f"Expected +20, got {result.exact_goal}"


class TestHeuristicExposed:
    """Test exposed square heuristic (-30 points)."""
    
    def test_exposed_heuristic(self):
        """-30 points when moving to exposed square."""
        engine = PathfinderEngine()
        
        # Yellow piece at position 7, can move to 9 with roll 2
        board_state = self._create_test_board({
            'blue': [PiecePosition(PlayerColor.BLUE, 0, 9, False, False, 1.0)],
            'yellow': [PiecePosition(PlayerColor.YELLOW, 0, 7, False, False, 1.0)],
            'green': [],
            'red': [],
        })
        
        # Move blue piece to 9 (yellow can capture with roll 2)
        move = Move('blue', 0, 5, 9, MoveType.ADVANCE, 4)
        
        score, result = engine.score_move(move, board_state, 'blue')
        
        assert result.exposed == -30, f"Expected -30, got {result.exposed}"
        assert score < 0, "Score should be negative due to exposure"


class TestHeuristicBreakBlockade:
    """Test break blockade heuristic (-20 points)."""
    
    def test_break_blockade_heuristic(self):
        """-20 points when leaving blockade."""
        engine = PathfinderEngine()
        
        # Two blue pieces at position 10
        board_state = self._create_test_board({
            'blue': [
                PiecePosition(PlayerColor.BLUE, 0, 10, False, False, 1.0),
                PiecePosition(PlayerColor.BLUE, 1, 10, False, False, 1.0),
            ],
            'yellow': [],
            'green': [],
            'red': [],
        })
        
        # Move one piece away from the blockade
        move = Move('blue', 0, 10, 12, MoveType.ADVANCE, 2)
        
        score, result = engine.score_move(move, board_state, 'blue')
        
        assert result.break_blockade == -20, f"Expected -20, got {result.break_blockade}"


class TestNoValidMoves:
    """Test edge case: no valid moves."""
    
    def test_no_valid_moves(self):
        """Handle when all pieces blocked/in base with no 6."""
        engine = PathfinderEngine()
        
        # All pieces in base, no roll 6
        board_state = self._create_test_board({
            'blue': [
                PiecePosition(PlayerColor.BLUE, 0, -1, True, False, 1.0),
                PiecePosition(PlayerColor.BLUE, 1, -1, True, False, 1.0),
                PiecePosition(PlayerColor.BLUE, 2, -1, True, False, 1.0),
                PiecePosition(PlayerColor.BLUE, 3, -1, True, False, 1.0),
            ],
            'yellow': [],
            'green': [],
            'red': [],
        })
        
        moves = engine.get_valid_moves(board_state, 'blue', 3)  # Not a 6
        
        assert len(moves) == 0, "No moves should be valid when pieces in base without roll 6"


class TestMoveGeneration:
    """Test move generation."""
    
    def test_enter_move_type(self):
        """ENTER move type when entering from base with 6."""
        engine = PathfinderEngine()
        
        board_state = self._create_test_board({
            'blue': [PiecePosition(PlayerColor.BLUE, 0, -1, True, False, 1.0)],
            'yellow': [],
            'green': [],
            'red': [],
        })
        
        moves = engine.get_valid_moves(board_state, 'blue', 6)
        
        assert len(moves) == 1, "Should have 1 valid move"
        assert moves[0].move_type == MoveType.ENTER, "Move type should be ENTER"
    
    def test_advance_move_type(self):
        """ADVANCE move type for normal movement."""
        engine = PathfinderEngine()
        
        board_state = self._create_test_board({
            'blue': [PiecePosition(PlayerColor.BLUE, 0, 5, False, False, 1.0)],
            'yellow': [],
            'green': [],
            'red': [],
        })
        
        moves = engine.get_valid_moves(board_state, 'blue', 3)
        
        assert len(moves) == 1, "Should have 1 valid move"
        assert moves[0].move_type == MoveType.ADVANCE, "Move type should be ADVANCE"
        assert moves[0].to_position == 8, "Should move 3 spaces forward"
    
    def test_goal_move_type(self):
        """GOAL move type when reaching goal."""
        engine = PathfinderEngine()
        
        board_state = self._create_test_board({
            'blue': [PiecePosition(PlayerColor.BLUE, 0, 50, False, False, 1.0)],
            'yellow': [],
            'green': [],
            'red': [],
        })
        
        moves = engine.get_valid_moves(board_state, 'blue', 3)
        
        # Should have move to goal (exact roll)
        goal_moves = [m for m in moves if m.move_type == MoveType.GOAL]
        assert len(goal_moves) > 0, "Should have goal move with exact roll"


# Helper function to create test board state
def _create_test_board(player_pieces: dict) -> BoardState:
    """Create a BoardState for testing."""
    players = {}
    
    for color_name, pieces in player_pieces.items():
        color = PlayerColor(color_name)
        players[color] = PlayerState(color=color, pieces=pieces)
    
    return BoardState(
        width=1080,
        height=1920,
        players=players,
        confidence=1.0
    )


# Alias for use in tests
TestHeuristicCapture._create_test_board = staticmethod(_create_test_board)
TestHeuristicSafeZone._create_test_board = staticmethod(_create_test_board)
TestHeuristicBlockade._create_test_board = staticmethod(_create_test_board)
TestHeuristicEnterBoard._create_test_board = staticmethod(_create_test_board)
TestHeuristicExactGoal._create_test_board = staticmethod(_create_test_board)
TestHeuristicExposed._create_test_board = staticmethod(_create_test_board)
TestHeuristicBreakBlockade._create_test_board = staticmethod(_create_test_board)
TestNoValidMoves._create_test_board = staticmethod(_create_test_board)
TestMoveGeneration._create_test_board = staticmethod(_create_test_board)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])