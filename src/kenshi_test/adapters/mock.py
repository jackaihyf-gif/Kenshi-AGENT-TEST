import time
from dataclasses import asdict, replace
from html import escape
from pathlib import Path

from ..config import MockConfig
from ..errors import AdapterError, GameMissing
from ..models import GameState, Screenshot
from .base import Deadline, GameAdapter


class MockAdapter(GameAdapter):
    """Deterministic in-memory armor scenario; never opens a process or sends OS input."""

    name = "mock"
    simulated = True

    def __init__(self, config: MockConfig | None = None):
        self.config = config or MockConfig()
        self.state = GameState()
        self.ready_at = 0.0

    def launch(self, deadline: Deadline) -> None:
        deadline.remaining()
        if self.state.running:
            raise AdapterError("Mock session is already running")
        if self.config.scenario == "missing":
            raise GameMissing("Simulated missing game; no real installation was inspected")
        deadline.sleep(self.config.launch_delay)
        self.state = GameState(running=True, phase="loading")
        self.ready_at = time.monotonic() + self.config.load_delay

    def get_state(self, deadline: Deadline) -> GameState:
        deadline.remaining()
        if (self.state.running and self.state.phase == "loading"
                and self.config.scenario != "timeout" and time.monotonic() >= self.ready_at):
            self.state = replace(self.state, phase="ready")
        return self.state

    def press_key(self, key: str, deadline: Deadline) -> None:
        state = self.get_state(deadline)
        if not state.running or state.phase != "ready":
            raise AdapterError("Mock input requires a running, ready session")
        if self.config.scenario == "crash":
            self.state = replace(state, running=False, phase="crashed")
            raise AdapterError("Simulated game crash during input")
        key = key.upper()
        if key not in {"I", "E", "ESC"}:
            raise AdapterError(f"Unsupported mock key: {key}")
        self.state = replace(state, keys=(*state.keys, key))
        if key == "I":
            self.state = replace(self.state, inventory_open=not state.inventory_open)
        elif key == "E":
            if not state.inventory_open:
                raise AdapterError("Open the simulated inventory before equipping armor")
            self.state = replace(self.state, armor_equipped=self.config.scenario != "failure")
        else:
            self.state = replace(self.state, inventory_open=False)

    def screenshot(self, destination: Path, deadline: Deadline) -> Screenshot:
        state = self.get_state(deadline)
        if not state.running:
            raise AdapterError("Cannot capture a stopped mock session")
        if self.config.scenario == "screenshot-error":
            raise AdapterError("Simulated screenshot failure")
        destination = destination.with_suffix(".svg")
        destination.parent.mkdir(parents=True, exist_ok=True)
        rows = "\n".join(
            f'<text x="32" y="{160 + i * 30}">{escape(str(k))}: {escape(str(v))}</text>'
            for i, (k, v) in enumerate(asdict(state).items())
        )
        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="960" height="480"
 viewBox="0 0 960 480" role="img" aria-label="MOCK SIMULATED FRAME - NOT KENSHI">
<title>MOCK / SIMULATED FRAME - NOT KENSHI</title>
<metadata>simulated=true; game_verified=false; adapter=mock</metadata>
<rect width="960" height="480" fill="#171c28"/>
<g fill="#ffffff" font-family="monospace" font-size="20">
<text x="32" y="54" fill="#ffd66b" font-size="30">MOCK / SIMULATED FRAME</text>
<text x="32" y="94">NOT KENSHI - NO REAL GAME WAS LAUNCHED</text>
{rows}
<text x="32" y="440" fill="#ffd66b">Synthetic test evidence only</text>
</g></svg>'''
        destination.write_text(svg, encoding="utf-8")
        deadline.remaining()
        return Screenshot(path=str(destination), simulated=True)

    def stop(self, deadline: Deadline) -> None:
        deadline.remaining()
        self.state = GameState()
