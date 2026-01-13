"""
Dragonchess (Threes) - Game Logic

Core game state and logic for the dice game.
"""
import random
from dataclasses import dataclass, field


@dataclass
class PlayerState:
    """State for a single player in the game."""
    kept_dice: list[int] = field(default_factory=list)
    current_roll: list[int] = field(default_factory=list)
    rolls_used: int = 0
    finished: bool = False

    def calculate_score(self) -> int:
        """Calculate score from kept dice. 3s count as 0."""
        return sum(0 if d == 3 else d for d in self.kept_dice)

    def dice_remaining(self) -> int:
        """Number of dice left to keep (not yet set aside)."""
        return 5 - len(self.kept_dice)

    def rolls_remaining(self) -> int:
        """Number of rolls left for this player."""
        return 5 - self.rolls_used


class DragonchessGame:
    """Main game state and logic."""

    def __init__(self, player1_id: int, player2_id: int, game_name: str = "Dragonchess"):
        self.players = [player1_id, player2_id]
        self.current_player_idx = 0
        self.player_states: dict[int, PlayerState] = {
            player1_id: PlayerState(),
            player2_id: PlayerState()
        }
        self.finished = False
        self.winner: int | None = None
        self.loser: int | None = None
        self.is_tie = False
        self.moon_shot = False
        self.game_name = game_name  # "Dragonchess" or "Threes"

    @property
    def current_player(self) -> int:
        """Get the current player's ID."""
        return self.players[self.current_player_idx]

    @property
    def current_state(self) -> PlayerState:
        """Get the current player's state."""
        return self.player_states[self.current_player]

    def roll_dice(self) -> list[int]:
        """Roll dice for the current player. Returns the rolled values."""
        state = self.current_state
        if state.finished or state.rolls_remaining() <= 0:
            return []

        num_dice = state.dice_remaining()
        if num_dice <= 0:
            return []

        state.current_roll = [random.randint(1, 6) for _ in range(num_dice)]
        state.rolls_used += 1

        # Check for moon shot (6-6-6-6-6 on first roll with all 5 dice)
        if (len(state.current_roll) == 5 and
                all(d == 6 for d in state.current_roll) and
                len(state.kept_dice) == 0):
            self.moon_shot = True
            state.kept_dice = state.current_roll.copy()
            state.current_roll = []
            state.finished = True
            self._end_game_moon_shot()

        return state.current_roll

    def keep_dice(self, indices: list[int]) -> bool:
        """
        Keep dice at the specified indices (0-based) from current_roll.
        Returns True if successful, False if invalid.

        After keeping dice, the turn passes to the other player.
        A player is "finished" when they have kept all 5 dice OR used all 5 rolls.
        """
        state = self.current_state
        if not state.current_roll:
            return False

        # Validate indices
        if not indices:
            return False
        if any(i < 0 or i >= len(state.current_roll) for i in indices):
            return False

        # Move selected dice to kept
        kept_values = [state.current_roll[i] for i in sorted(indices)]
        state.kept_dice.extend(kept_values)

        # Clear current roll
        state.current_roll = []

        # Check if this player is now finished (all dice kept OR out of rolls)
        if state.dice_remaining() == 0 or state.rolls_remaining() == 0:
            state.finished = True

        # Check if game is over (both players finished)
        self._check_game_end()

        # If game not over, switch to next player (skip if they're already finished)
        if not self.finished:
            self._switch_to_next_active_player()

        return True

    def _switch_to_next_active_player(self) -> None:
        """Switch to the next player who hasn't finished."""
        # Try the other player
        other_idx = 1 - self.current_player_idx
        other_player = self.players[other_idx]

        if not self.player_states[other_player].finished:
            self.current_player_idx = other_idx
        # If other player is finished, stay on current player (they must still have moves)

    def _check_game_end(self) -> None:
        """Check if the game has ended and determine winner."""
        if all(ps.finished for ps in self.player_states.values()):
            self.finished = True
            self._determine_winner()

    def _end_game_moon_shot(self) -> None:
        """End the game immediately due to moon shot."""
        self.finished = True
        self.winner = self.current_player
        self.loser = self.players[1 - self.current_player_idx]

    def _determine_winner(self) -> None:
        """Determine the winner based on scores."""
        p1, p2 = self.players
        s1 = self.player_states[p1].calculate_score()
        s2 = self.player_states[p2].calculate_score()

        if s1 < s2:
            self.winner = p1
            self.loser = p2
        elif s2 < s1:
            self.winner = p2
            self.loser = p1
        else:
            self.is_tie = True
            self.winner = None
            self.loser = None

    def switch_player(self) -> None:
        """Switch to the next player."""
        self.current_player_idx = 1 - self.current_player_idx

    def get_score(self, player_id: int) -> int:
        """Get the score for a player."""
        return self.player_states[player_id].calculate_score()

    def get_kept_dice(self, player_id: int) -> list[int]:
        """Get the kept dice for a player."""
        return self.player_states[player_id].kept_dice.copy()

    def is_player_finished(self, player_id: int) -> bool:
        """Check if a player has finished their turn."""
        return self.player_states[player_id].finished

    def get_bot_keep_indices(self) -> list[int]:
        """Return indices of dice to keep using optimal strategy.

        Strategy: Keep 3s first (worth 0), then lowest value die.
        Always keeps at least one die.
        """
        current_roll = self.current_state.current_roll
        if not current_roll:
            return []

        # Find indices of all 3s (worth 0 points - best to keep)
        three_indices = [i for i, val in enumerate(current_roll) if val == 3]
        if three_indices:
            return three_indices

        # No 3s - keep the single lowest die
        min_val = min(current_roll)
        for i, val in enumerate(current_roll):
            if val == min_val:
                return [i]

        return [0]  # Fallback - shouldn't reach here
