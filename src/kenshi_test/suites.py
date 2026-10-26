"""Suites depend on the adapter contract, never on concrete adapter implementations."""

from collections.abc import Callable
from dataclasses import asdict
from pathlib import Path

from .adapters.base import Deadline, GameAdapter
from .errors import AdapterError, TestFailure
from .models import RunReport, Screenshot


def armor_steps(
    adapter: GameAdapter, deadline: Deadline, poll_interval: float,
    directory: Path, report: RunReport,
) -> list[tuple[str, Callable[[], dict]]]:
    def launch() -> dict:
        adapter.launch(deadline)
        return {"simulated": adapter.simulated}

    def ready() -> dict:
        while True:
            state = adapter.get_state(deadline)
            if not state.running:
                raise AdapterError("Session stopped while waiting for ready state")
            if state.phase == "ready":
                return asdict(state)
            deadline.sleep(poll_interval)

    def inventory() -> dict:
        adapter.press_key("I", deadline)
        state = adapter.get_state(deadline)
        if not state.inventory_open:
            raise TestFailure("Inventory did not open after input")
        return asdict(state)

    def equip() -> dict:
        adapter.press_key("E", deadline)
        state = adapter.get_state(deadline)
        if not state.armor_equipped:
            raise TestFailure("Armor was not equipped after input")
        return asdict(state)

    def capture() -> dict:
        shot = adapter.screenshot(directory / "armor", deadline)
        report.artifacts.append(Screenshot(
            path=Path(shot.path).relative_to(directory).as_posix(),
            simulated=shot.simulated, media_type=shot.media_type,
        ))
        return {"simulated": shot.simulated}

    return [
        ("launch", launch), ("wait_ready", ready), ("open_inventory", inventory),
        ("equip_armor", equip), ("screenshot", capture),
    ]
