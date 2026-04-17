"""Format rapport Telegram — imposé par le cahier des charges.

Utilisé par Builder, Jarvis, Reflector pour tout jalon livré.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class MilestoneReport:
    milestone: str
    validated: list[str] = field(default_factory=list)  # 🟢
    delivered: list[str] = field(default_factory=list)  # 📦
    tests_passed: int = 0
    tests_total: int = 0
    evals_passed: int = 0
    evals_total: int = 0
    cost_real_eur: float = 0.0
    cost_estimated_eur: float = 0.0
    metric_label: str = ""
    metric_value: str = ""
    next_milestone: str = ""
    needs_from_user: list[str] = field(default_factory=list)  # ❓


def _bullet(items: list[str], empty: str = "—") -> str:
    if not items:
        return empty
    return "\n".join(f"  • {it}" for it in items)


def format_report(r: MilestoneReport) -> str:
    need = _bullet(r.needs_from_user, "rien")
    return (
        f"*Jalon* {r.milestone}\n\n"
        f"🟢 validé :\n{_bullet(r.validated)}\n\n"
        f"📦 livré :\n{_bullet(r.delivered)}\n\n"
        f"🧪 tests+evals : "
        f"{r.tests_passed}/{r.tests_total} tests, "
        f"{r.evals_passed}/{r.evals_total} evals\n"
        f"💶 coût réel : {r.cost_real_eur:.2f} € vs estimé {r.cost_estimated_eur:.2f} €\n"
        f"📈 métrique : {r.metric_label} {r.metric_value}".rstrip() + "\n"
        f"⏭️ prochain : {r.next_milestone or '—'}\n"
        f"❓ besoin de toi :\n{need}\n"
    )
