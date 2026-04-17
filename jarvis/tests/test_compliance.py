from jarvis.compliance.checks import ComplianceAgent


def test_all_green_campaign_fr_passes():
    a = ComplianceAgent()
    campaign = {
        "legal_basis": "legitimate_interests",
        "art30_id": "camp_1",
        "opt_out_link": True,
        "sender_identity": True,
        "frequency_cap": True,
        "send_hours_local": True,
        "dpa_providers": True,
        "fr_lcen": True,
        "fr_b2b_legitimate": True,
    }
    r = a.run("FR", campaign)
    assert r.all_green


def test_missing_dpa_blocks():
    a = ComplianceAgent()
    r = a.run("FR", {"legal_basis": "legitimate_interests"})
    assert not r.all_green
    blockers = a.blocker_reasons(r)
    assert "dpa_providers" in blockers
    assert "opt_out_link" in blockers


def test_dach_requires_impressum():
    a = ComplianceAgent()
    r = a.run("DACH", {"legal_basis": "legitimate_interests", "dpa_providers": True})
    blockers = a.blocker_reasons(r)
    assert "dach_impressum" in blockers
    assert "dach_b2b_check" in blockers


def test_ca_requires_opt_in():
    a = ComplianceAgent()
    r = a.run("CA", {"legal_basis": "consent"})
    blockers = a.blocker_reasons(r)
    assert "ca_casl" in blockers  # consent opt-in explicite à cocher


def test_us_requires_can_spam_state_check():
    a = ComplianceAgent()
    r = a.run("US", {"legal_basis": "legitimate_interests"})
    blockers = a.blocker_reasons(r)
    assert "us_can_spam" in blockers
    assert "us_state_check" in blockers


def test_card_format():
    a = ComplianceAgent()
    r = a.run("FR", {})
    card = r.as_telegram_card()
    assert "Compliance" in card
    assert "⛔" in card  # des checks non passés
