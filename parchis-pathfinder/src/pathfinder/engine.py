"""
Pathfinding Engine for Parchís Pathfinding.

Calculates optimal moves using heuristic scoring.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Set
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class MoveType(Enum):
    """Types of moves in Parchís."""
    ENTER = "enter"  # Enter board from base (roll 6)
    ADVANCE = "advance"  # Move forward on path
    CAPTURE = "capture"  # Capture opponent piece
    GOAL = "goal"  # Reach goal
    BLOCK = "block"  # Form or stay in blockade


@dataclass
class Move:
    """Represents a legal move in Parchís."""
    player: str  # Color name
    piece_id: int  # Which piece (0-3)
    from_position: int  # Current position (-1 for base, 52-67 for goal)
    to_position: int  # Target position
    move_type: MoveType
    dice_roll: int  # Dice value used for this move
    
    def __str__(self):
        return f"Move {self.player}[{self.piece_id}]: {self.from_position} -> {self.to_position} ({self.move_type.value})"


@dataclass
class HeuristicResult:
    """Breakdown of heuristic scores for a move."""
    capture: int = 0
    safe_zone: int = 0
    blockade: int = 0
    enter_board: int = 0
    exact_goal: int = 0
    exposed: int = 0
    break_blockade: int = 0
    
    def total(self) -> int:
        """Calculate total score."""
        return (self.capture + self.safe_zone + self.blockade + 
                self.enter_board + self.exact_goal + self.exposed + 
                self.break_blockade)


@dataclass
class MoveRecommendation:
    """A recommended move with score and reasoning."""
    move: Move
    score: int
    heuristic_result: HeuristicResult
    alternatives: List['MoveRecommendation'] = field(default_factory=list)
    
    def __str__(self):
        return f"{self.move} (score: {self.score})"


class PathfinderEngine:
    """
    Calculates optimal moves using heuristic scoring.
    
    Scoring system:
    - +100: Capture opponent piece
    - +50: Enter safe square (corridor or goal)
    - +40: Form blockade (2+ pieces on same square)
    - +30: Enter board from base (requires roll 6)
    - +20: Exact roll to reach goal
    - -30: Move to exposed square (opponent can capture)
    - -20: Break existing blockade
    """
    
    # Heuristic score values
    SCORE_CAPTURE = 100
    SCORE_SAFE_ZONE = 50
    SCORE_BLOCKADE = 40
    SCORE_ENTER_BOARD = 30
    SCORE_EXACT_GOAL = 20
    SCORE_EXPOSED = -30
    SCORE_BREAK_BLOCKADE = -20
    
    # Board configuration
    PATH_LENGTH = 52  # Main circular path
    GOAL_LENGTH = 4   # Steps into goal
    
    # Player starting positions on the path (where they enter from base)
    # These are approximate and depend on the specific Parchís variant
    START_POSITIONS = {
        'blue': 0,
        'yellow': 13,
        'green': 26,
        'red': 39,
    }
    
    # Goal position ranges
    GOAL_RANGES = {
        'blue': range(52, 56),
        'yellow': range(56, 60),
        'green': range(60, 64),
        'red': range(64, 68),
    }
    
    # Safe zone positions (positions where opponent can't capture)
    # These are approximate and should be calibrated
    SAFE_ZONES = {0, 8, 13, 21, 26, 34, 39, 47}
    
    def __init__(self, calibration: Optional[dict] = None):
        """
        Initialize pathfinding engine.
        
        Args:
            calibration: Calibration data with custom positions
        """
        self.calibration = calibration or {}
        
        # Override defaults with calibration if available
        if 'start_positions' in calibration:
            self.START_POSITIONS.update(calibration['start_positions'])
        if 'safe_zones' in calibration:
            self.SAFE_ZONES = set(calibration['safe_zones'])
        if 'goal_ranges' in calibration:
            self.GOAL_RANGES.update(calibration['goal_ranges'])
    
    def calculate_best_move(self, board_state, player: str, 
                           dice_roll: int) -> Optional[MoveRecommendation]:
        """
        Calculate the best move for a player given the current board state.
        
        Args:
            board_state: Current BoardState
            player: Player color ('blue', 'yellow', 'green', 'red')
            dice_roll: Current dice roll value
            
        Returns:
            MoveRecommendation with the best move, or None if no valid moves
        """
        # Generate all valid moves
        valid_moves = self.get_valid_moves(board_state, player, dice_roll)
        
        if not valid_moves:
            return None
        
        # Score each move
        scored_moves = []
        for move in valid_moves:
            score, heuristic_result = self.score_move(
                move, board_state, player
            )
            scored_moves.append(MoveRecommendation(
                move=move,
                score=score,
                heuristic_result=heuristic_result
            ))
        
        # Sort by score (highest first)
        scored_moves.sort(key=lambda x: x.score, reverse=True)
        
        # Set alternatives (top 3)
        if len(scored_moves) > 1:
            for rec in scored_moves[:3]:
                rec.alternatives = scored_moves[:3]
        
        return scored_moves[0]
    
    def get_valid_moves(self, board_state, player: str, 
                        dice_roll: int) -> List[Move]:
        """
        Generate all valid moves for a player given the dice roll.
        
        Args:
            board_state: Current BoardState
            player: Player color
            dice_roll: Dice roll value (1-6)
            
        Returns:
            List of valid Move objects
        """
        valid_moves = []
        
        # Get player's pieces
        player_state = board_state.get_player(player)
        if not player_state:
            return []
        
        pieces = player_state.pieces
        
        for piece in pieces:
            move = self._try_move(piece, dice_roll, board_state, player)
            if move:
                valid_moves.append(move)
        
        return valid_moves
    
    def _try_move(self, piece, dice_roll: int, board_state, 
                  player: str) -> Optional[Move]:
        """Try to make a move with the given dice roll."""
        from_pos = piece.position
        
        # Determine target position based on piece state
        if piece.in_base:
            # Need roll 6 to enter
            if dice_roll == 6:
                return Move(
                    player=player,
                    piece_id=piece.piece_id,
                    from_position=-1,
                    to_position=self.START_POSITIONS.get(player, 0),
                    move_type=MoveType.ENTER,
                    dice_roll=dice_roll
                )
            return None
        
        if piece.in_goal:
            # Already in goal, can't move
            return None
        
        # Calculate new position
        new_pos = from_pos + dice_roll
        
        # Check if piece reaches goal
        goal_start = 52 + list(self.GOAL_RANGES[player])[0] - 52
        if from_pos < 52 and new_pos >= 52:
            # Entering goal zone
            goal_pos = new_pos - 52  # Relative to goal start
            if goal_pos < 4:
                # Exact roll to goal?
                exact = goal_pos == 3
                return Move(
                    player=player,
                    piece_id=piece.piece_id,
                    from_position=from_pos,
                    to_position=52 + list(self.GOAL_RANGES[player])[0] + goal_pos,
                    move_type=MoveType.GOAL,
                    dice_roll=dice_roll
                )
            # Can't overshoot goal
            return None
        
        # Check for capture on the path
        # (This is handled in scoring, not here)
        
        # Normal advance
        if new_pos < 52:
            # Wrap around the circular path
            new_pos = new_pos % 52
            
            # Check if landing on own piece (blockade - allowed)
            # or if it's a valid position
            return Move(
                player=player,
                piece_id=piece.piece_id,
                from_position=from_pos,
                to_position=new_pos,
                move_type=MoveType.ADVANCE,
                dice_roll=dice_roll
            )
        
        return None
    
    def score_move(self, move: Move, board_state, 
                   player: str) -> tuple[int, HeuristicResult]:
        """
        Score a move using heuristic evaluation.
        
        Args:
            move: The move to score
            board_state: Current board state
            player: Current player color
            
        Returns:
            Tuple of (total_score, HeuristicResult)
        """
        result = HeuristicResult()
        
        # 1. Check for capture (+100)
        if self._is_capture(move, board_state, player):
            result.capture = self.SCORE_CAPTURE
        
        # 2. Check for safe zone (+50)
        if self._is_safe_zone(move, player):
            result.safe_zone = self.SCORE_SAFE_ZONE
        
        # 3. Check for forming blockade (+40)
        if self._forms_blockade(move, board_state, player):
            result.blockade = self.SCORE_BLOCKADE
        
        # 4. Check for entering board (+30)
        if move.move_type == MoveType.ENTER:
            result.enter_board = self.SCORE_ENTER_BOARD
        
        # 5. Check for exact goal (+20)
        if move.move_type == MoveType.GOAL:
            # Check if exact roll
            from_pos = move.from_position
            to_pos = move.to_position
            if from_pos < 52 and to_pos >= 52:
                goal_pos = to_pos - 52
                if goal_pos == 3:  # Exact roll to reach goal
                    result.exact_goal = self.SCORE_EXACT_GOAL
        
        # 6. Check if moving to exposed square (-30)
        if self._is_exposed(move, board_state, player):
            result.exposed = self.SCORE_EXPOSED
        
        # 7. Check if breaking blockade (-20)
        if self._breaks_blockade(move, board_state, player):
            result.break_blockade = self.SCORE_BREAK_BLOCKADE
        
        return result.total(), result
    
    def _is_capture(self, move: Move, board_state, player: str) -> bool:
        """Check if the move captures an opponent piece."""
        # Capture happens when landing on opponent's position
        target_pos = move.to_position
        
        # Check all other players' pieces
        for other_player in ['blue', 'yellow', 'green', 'red']:
            if other_player == player:
                continue
            
            other_state = board_state.get_player(other_player)
            if not other_state:
                continue
            
            for piece in other_state.pieces:
                if piece.position == target_pos and not piece.in_base and not piece.in_goal:
                    return True
        
        return False
    
    def _is_safe_zone(self, move: Move, player: str) -> bool:
        """Check if move goes to a safe zone."""
        target = move.to_position
        
        # Safe zones on the path
        if target in self.SAFE_ZONES:
            return True
        
        # Goal zones are safe
        if move.move_type == MoveType.GOAL:
            return True
        
        return False
    
    def _forms_blockade(self, move: Move, board_state, player: str) -> bool:
        """Check if move forms a blockade (2+ pieces on same square)."""
        target = move.to_position
        
        # Count pieces at target position (including the moving piece)
        count = 1  # The moving piece
        
        player_state = board_state.get_player(player)
        if not player_state:
            return False
        
        for piece in player_state.pieces:
            if piece.piece_id != move.piece_id and piece.position == target:
                count += 1
        
        return count >= 2
    
    def _is_exposed(self, move: Move, board_state, player: str) -> bool:
        """Check if move goes to a square exposed to opponent capture."""
        target = move.to_position
        
        # Safe zones are never exposed
        if self._is_safe_zone(move, player):
            return False
        
        # Goal is safe
        if move.move_type == MoveType.GOAL:
            return False
        
        # Check if any opponent can capture this position
        for other_player in ['blue', 'yellow', 'green', 'red']:
            if other_player == player:
                continue
            
            # Check if opponent can land here with any roll
            if self._can_opponent_reach(board_state, other_player, target):
                return True
        
        return False
    
    def _can_opponent_reach(self, board_state, opponent: str, 
                           target: int) -> bool:
        """Check if opponent can reach a position with any roll."""
        opponent_state = board_state.get_player(opponent)
        if not opponent_state:
            return False
        
        for piece in opponent_state.pieces:
            if piece.in_base:
                # Can enter with roll 6, then would need additional rolls
                # For simplicity, assume they could reach many positions
                continue
            
            if piece.in_goal:
                continue
            
            # Check if any roll can reach the target
            for roll in range(1, 7):
                new_pos = piece.position + roll
                
                # Handle path wrapping
                if new_pos < 52:
                    new_pos = new_pos % 52
                
                if new_pos == target:
                    return True
        
        return False
    
    def _breaks_blockade(self, move: Move, board_state, player: str) -> bool:
        """Check if move breaks an existing blockade."""
        # A blockade is 2+ pieces on same square
        from_pos = move.from_position
        
        # Count pieces at current position
        player_state = board_state.get_player(player)
        if not player_state:
            return False
        
        count = sum(1 for p in player_state.pieces 
                   if p.position == from_pos and not p.in_base and not p.in_goal)
        
        # If there were 2+ pieces and we're moving one, we break the blockade
        return count >= 2
    
    def get_move_description(self, recommendation: MoveRecommendation) -> str:
        """Get human-readable description of a move."""
        move = recommendation.move
        
        # Build description
        piece_names = {0: "1st", 1: "2nd", 2: "3rd", 3: "4th"}
        
        desc = f"{move.player.upper()} {piece_names.get(move.piece_id, str(move.piece_id))} piece: "
        
        if move.move_type == MoveType.ENTER:
            desc += "Enter board from base"
        elif move.move_type == MoveType.GOAL:
            desc += f"Move to goal ({move.dice_roll} spaces)"
        elif move.move_type == MoveType.CAPTURE:
            desc += f"CAPTURE opponent ({move.dice_roll} spaces)"
        else:
            desc += f"Move {move.dice_roll} spaces forward"
        
        desc += f" [Score: {recommendation.score}]"
        
        return desc


# Convenience function
def create_pathfinder(calibration: Optional[dict] = None) -> PathfinderEngine:
    """Create a configured PathfinderEngine instance."""
    return PathfinderEngine(calibration=calibration)