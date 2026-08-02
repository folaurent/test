"""Kill switch global. Un flag fichier + un endpoint /panic Telegram.

Quand activé : tous les agents refusent d'exécuter, le bus continue à tracer
mais aucune action externe n'est faite.
"""
from __future__ import annotations

from pathlib import Path

_PANIC_FILE = Path("data/.panic")


class KillSwitchTriggered(RuntimeError):
    pass


class KillSwitch:
    def __init__(self, path: Path | None = None) -> None:
        self._path = path or _PANIC_FILE

    def engaged(self) -> bool:
        return self._path.exists()

    def engage(self, reason: str = "manual") -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(reason, encoding="utf-8")

    def release(self) -> None:
        if self._path.exists():
            self._path.unlink()

    def assert_ok(self) -> None:
        if self.engaged():
            raise KillSwitchTriggered(
                f"kill switch engaged: {self._path.read_text(encoding='utf-8')}"
            )
