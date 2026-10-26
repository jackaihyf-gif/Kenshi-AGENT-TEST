"""Every blocking operation must honor the shared monotonic Deadline.

This is a cooperative contract, not a thread-based hard-kill wrapper. A future
external backend must apply the remaining timeout to each subprocess / IPC call.
"""

import time
from abc import ABC, abstractmethod
from pathlib import Path

from ..errors import OperationTimeout
from ..models import GameState, Screenshot


class Deadline:
    def __init__(self, seconds: float):
        self.end = time.monotonic() + seconds

    def remaining(self) -> float:
        remaining = self.end - time.monotonic()
        if remaining <= 0:
            raise OperationTimeout("Operation exceeded the run timeout")
        return remaining

    def sleep(self, seconds: float) -> None:
        target = time.monotonic() + seconds
        while True:
            remaining = self.remaining()
            delay = target - time.monotonic()
            if delay <= 0:
                return
            # A short Windows sleep may wake early; always recheck both clocks.
            time.sleep(min(delay, remaining))


class GameAdapter(ABC):
    name: str
    simulated: bool

    @abstractmethod
    def launch(self, deadline: Deadline) -> None:
        """Launch or simulate a session owned by this adapter."""

    @abstractmethod
    def press_key(self, key: str, deadline: Deadline) -> None:
        """Send one semantic key to this session only."""

    @abstractmethod
    def get_state(self, deadline: Deadline) -> GameState:
        """Observe state; never infer success from input delivery alone."""

    @abstractmethod
    def screenshot(self, destination: Path, deadline: Deadline) -> Screenshot:
        """Capture evidence and state whether it is simulated."""

    @abstractmethod
    def stop(self, deadline: Deadline) -> None:
        """Idempotent cleanup of only the owned session."""
