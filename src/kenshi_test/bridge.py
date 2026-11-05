"""Bounded file RPC to the in-game KenshiLua agent (no desktop input)."""

import json
import math
import os
import time
from pathlib import Path
from uuid import uuid4

from .adapters.base import Deadline
from .errors import AdapterError, ConfigError

ACTIONS = {
    "status",
    "gait",
    "move",
    "halt",
    "sheathe",
    "release",
    "new_test",
    "replace_test",
    "finish_editor",
    "profile_editor",
    "capture",
    "pause",
    "resume",
    "camera",
    "overlays",
    "close_overlay",
    "nearby",
    "autosave",
    "spar",
    "end_spar",
    "wear",
    "sources",
    "mounts",
    "motion_trace",
    "weapon",
    "visibility",
    "service",
    "opponent",
    "energy",
    "pose_capture",
    "craft",
    "power",
    "melee_capture",
    "lifecycle",
    "stage2_region",
    "stage2_team",
}


class LuaBridge:
    def __init__(self, root: Path):
        self.root = root

    def call(self, command: str, deadline: Deadline, **parameters) -> dict:
        if command not in ACTIONS:
            raise ConfigError(f"Unsupported bridge command: {command}")
        config = json.loads((self.root / "bridge-config.json").read_text("utf-8"))
        token = config["token"]
        if len(token) != 64 or any(c not in "0123456789abcdef" for c in token):
            raise ConfigError("Invalid local bridge token")
        identifier = uuid4().hex
        fields = {
            "protocol": 1,
            "id": identifier,
            "token": token,
            "command": command,
            "expires": int(time.time() + min(deadline.remaining(), 30)),
        }
        if command != "status":
            fields["session"] = self.call("status", deadline)["session"]
        for key, value in parameters.items():
            if isinstance(value, float) and not math.isfinite(value):
                raise ConfigError(f"Non-finite bridge argument: {key}")
            fields[key] = value
        for key, value in fields.items():
            if any(char in str(value) for char in "\r\n="):
                raise ConfigError(f"Invalid bridge argument: {key}")
        # Exclusive lock prevents clients overwriting each other's outstanding request.
        lock = self.root / "client.lock"
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError as exc:
            raise AdapterError(
                f"Bridge already in use; inspect stale lock if needed: {lock}"
            ) from exc
        try:
            with os.fdopen(fd, "w") as stream:
                stream.write(f"pid={os.getpid()}\nid={identifier}\n")
            temporary = self.root / f"request-{identifier}.tmp"
            try:
                temporary.write_text(
                    "\n".join(f"{k}={v}" for k, v in fields.items()) + "\n", encoding="utf-8"
                )
                os.replace(temporary, self.root / "request.ini")
            finally:
                temporary.unlink(missing_ok=True)
            while True:
                deadline.remaining()
                try:
                    response = json.loads((self.root / "response.json").read_text("utf-8"))
                except (FileNotFoundError, json.JSONDecodeError):
                    response = None
                if response and response.get("id") == identifier:
                    if response.get("protocol") != 1 or response.get("simulated") is not False:
                        raise AdapterError("Not a real protocol-1 in-game response")
                    if not response.get("ok"):
                        raise AdapterError(str(response.get("error", "In-game request failed")))
                    return response
                deadline.sleep(0.05)
        finally:
            lock.unlink(missing_ok=True)


def validate_control(
    command: str, owner: str | None, gait: str, dx: float, dz: float, duration: float
) -> dict:
    if command in {
        "status",
        "new_test",
        "finish_editor",
        "capture",
        "pause",
        "resume",
        "overlays",
        "close_overlay",
        "autosave",
    }:
        return {}
    if not owner or len(owner) > 160 or any(c not in "0123456789-" for c in owner):
        raise ConfigError("Control requires the exact numeric owner handle from live status")
    if not all(math.isfinite(v) for v in (dx, dz, duration)):
        raise ConfigError("Movement arguments must be finite")
    if not 1 <= duration <= 30 or dx * dx + dz * dz > 64 * 64:
        raise ConfigError("Lease must be 1..30 seconds; move radius cannot exceed 64 game units")
    return {
        "owner": owner,
        "mode": {"walk": 0, "jog": 1, "run": 2}[gait],
        "dx": dx,
        "dz": dz,
        "duration": duration,
    }
