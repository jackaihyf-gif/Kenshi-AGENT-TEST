from pathlib import Path

from ..errors import FeatureUnavailable, GameMissing
from ..models import GameState, Screenshot
from .base import Deadline, GameAdapter


class KenshiAdapter(GameAdapter):
    """Attach to a running game using an opt-in, authenticated KenshiLua bridge."""

    name = "kenshi"
    simulated = False

    def __init__(self, executable: Path | None, bridge_dir: Path | None = None):
        self.executable = executable
        self.bridge_dir = bridge_dir
        self.observation = None

    def _status(self, deadline: Deadline) -> dict:
        from ..bridge import LuaBridge

        if self.bridge_dir is None:
            self._unavailable("state observation; configure game.bridge_dir for Lua RPC")
        self.observation = LuaBridge(self.bridge_dir).call("status", deadline)["state"]
        return self.observation

    def launch(self, deadline: Deadline) -> None:
        deadline.remaining()
        if self.executable is None or not self.executable.is_file():
            raise GameMissing("Configure game.executable to an existing Kenshi executable")
        if self.bridge_dir is None:
            self._unavailable("launch")
        self._status(deadline)  # Attach only; do not own/terminate an existing game process.

    def press_key(self, key: str, deadline: Deadline) -> None:
        deadline.remaining()
        self._unavailable("I/E keyboard simulation; use the live semantic CLI commands")

    def get_state(self, deadline: Deadline) -> GameState:
        deadline.remaining()
        state = self._status(deadline)
        return GameState(running=True, phase=state["phase"], armor_equipped=any(
            row.get("upper") == "650-JACK_T60_WearLab.mod"
            for row in state["characters"].values()
        ))

    def screenshot(self, destination: Path, deadline: Deadline) -> Screenshot:
        deadline.remaining()
        self._unavailable("real screenshot capture")

    def stop(self, deadline: Deadline) -> None:
        # Attach-only adapter never owns or terminates the user's game process.
        deadline.remaining()

    @staticmethod
    def _unavailable(operation: str) -> None:
        raise FeatureUnavailable(
            f"Real Kenshi {operation} is NOT IMPLEMENTED. See docs/real-adapter.md"
        )
