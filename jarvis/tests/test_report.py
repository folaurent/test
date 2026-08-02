from jarvis.telegram_bot.report import MilestoneReport, format_report


def test_report_all_sections_present():
    r = MilestoneReport(
        milestone="Phase 1 — Jalon 1.1",
        validated=["scope filter", "voice lint"],
        delivered=["socle jarvis/"],
        tests_passed=35,
        tests_total=35,
        evals_passed=5,
        evals_total=5,
        cost_real_eur=0.0,
        cost_estimated_eur=0.0,
        metric_label="infra:",
        metric_value="0€",
        next_milestone="Jalon 1.2",
        needs_from_user=["TELEGRAM_BOT_TOKEN", "SUPABASE_URL", "ANTHROPIC_API_KEY"],
    )
    out = format_report(r)
    for marker in ("🟢", "📦", "🧪", "💶", "📈", "⏭️", "❓"):
        assert marker in out
    assert "Jalon 1.1" in out
    assert "TELEGRAM_BOT_TOKEN" in out
