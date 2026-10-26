from pathlib import Path

from ..errors import FeatureUnavailable, GameMissing
from ..models import GameState, Screenshot
from .base import Deadline, GameAdapter


class KenshiAdapter(GameAdapter):
    """Explicit phase-two boundary. Does not launch, control, or capture a real game."""

    name = "kenshi"
    simulated = False

    def __init__(self, executable: Path | None):
        self.executable = executable

    def launch(self, deadline: Deadline) -> None:
        deadline.remaining()
        if self.executable is None or not self.executable.is_file():
            raise GameMissing("Configure game.executable to an existing Kenshi executable")
        self._unavailable("launch")

    def press_key(self, key: str, deadline: Deadline) -> None:
        deadline.remaining()
        self._unavailable("input")

    def get_state(self, deadline: Deadline) -> GameState:
        deadline.remaining()
        self._unavailable("state observation")

    def screenshot(self, destination: Path, deadline: Deadline) -> Screenshot:
        deadline.remaining()
        self._unavailable("real screenshot capture")

    def stop(self, deadline: Deadline) -> None:
        # Phase one can never own a process, so cleanup is safely a no-op.
        deadline.remaining()

    @staticmethod
    def _unavailable(operation: str) -> None:
        raise FeatureUnavailable(
            f"Real Kenshi {operation} is NOT IMPLEMENTED. See docs/real-adapter.md"
        )
