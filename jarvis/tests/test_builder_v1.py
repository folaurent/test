"""Builder v1 — exécution disque."""
from pathlib import Path

import pytest
import yaml

from jarvis.agents.builder import Builder
from jarvis.core.config import Settings
from jarvis.core.scope import ScopeFilter


@pytest.fixture
def builder(tmp_path) -> Builder:
    # Copie minimale de la structure pour laisser Builder écrire.
    (tmp_path / "jarvis/agents/specialists").mkdir(parents=True)
    (tmp_path / "config/agents").mkdir(parents=True)
    (tmp_path / "goldens").mkdir(parents=True)
    return Builder(ScopeFilter.from_settings(Settings()), root=tmp_path)


def test_execute_writes_charter_skeleton_and_goldens(builder, tmp_path):
    plan = builder.draft_plan("Attaque l'Italie")
    report = builder.execute(plan)
    assert report["status"] == "executed"
    # 2 agents (Prospection-IT + Conversation-IT) × 3 fichiers = 6 paths.
    assert len(report["written"]) == 6

    charter = tmp_path / "config/agents/prospection_it.yml"
    assert charter.exists()
    data = yaml.safe_load(charter.read_text(encoding="utf-8"))
    assert data["name"] == "Prospection-IT"
    assert data["zone"] == "IT"
    assert data["autonomy"] == 1   # PROPOSE par défaut
    assert data["probation_until"] > 0

    spec = tmp_path / "jarvis/agents/specialists/prospection_it.py"
    assert spec.exists()
    content = spec.read_text(encoding="utf-8")
    assert "class ProspectionIt" in content
    assert "AgentBase" in content

    goldens = tmp_path / "goldens/prospection_it.yml"
    data = yaml.safe_load(goldens.read_text(encoding="utf-8"))
    ids = [g["id"] for g in data["goldens"]]
    assert "prospection_it_scope_sika" in ids
    assert "prospection_it_scope_parex" in ids
    assert "prospection_it_disclosure" in ids


def test_execute_refuses_scope_violation(builder):
    # Le plan sera bloqué dès le parse_intent.
    with pytest.raises(Exception):
        builder.draft_plan("crée un agent pour Sika France")


def test_execute_new_dev_agent(builder, tmp_path):
    plan = builder.draft_plan("crée un agent dev pour auto-tester le pipeline")
    report = builder.execute(plan)
    assert report["status"] == "executed"
    dev_charter = tmp_path / "config/agents/dev.yml"
    assert dev_charter.exists()
