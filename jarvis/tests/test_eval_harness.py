from pathlib import Path

from jarvis.evals.harness import EvalHarness, GoldenTask


def test_load_goldens_voice_fr():
    h = EvalHarness(Path(__file__).resolve().parent.parent / "goldens")
    tasks = h.load("ConversationOrchestrator")
    assert tasks, "aucune golden chargée"
    assert any(t.kind == "scope" for t in tasks)
    assert any(t.kind == "disclosure" for t in tasks)


def test_runner_fails_when_forbidden_term_present():
    h = EvalHarness(Path(__file__).resolve().parent.parent / "goldens")
    sika_task = next(
        t for t in h.load("ConversationOrchestrator") if t.id == "scope_refusal_sika"
    )
    # Simule un agent qui mentionne Sika (doit échouer)
    def bad_runner(_: GoldenTask) -> str:
        return "Je prépare une campagne pour Sika France."
    from jarvis.evals.harness import _evaluate_text  # type: ignore
    r = _evaluate_text(sika_task, bad_runner(sika_task))
    assert not r.passed


def test_runner_passes_when_refusing_properly():
    h = EvalHarness(Path(__file__).resolve().parent.parent / "goldens")
    sika_task = next(
        t for t in h.load("ConversationOrchestrator") if t.id == "scope_refusal_sika"
    )
    def good_runner(_: GoldenTask) -> str:
        return (
            "Désolé, je ne peux pas traiter cette demande — elle sort du "
            "périmètre que Laurent m'a défini."
        )
    from jarvis.evals.harness import _evaluate_text  # type: ignore
    r = _evaluate_text(sika_task, good_runner(sika_task))
    assert r.passed
