"""Voice lint — garde-fou sortie messages."""
from jarvis.voice.lint import VoiceLint


def test_banned_phrase_block_hard():
    lint = VoiceLint()
    r = lint.check("Bonjour, j'espère que vous allez bien. Je vous écris...")
    assert not r.passed
    assert any(i.rule == "banned_phrase" for i in r.hard_issues)


def test_ai_denial_blocks_hard():
    lint = VoiceLint()
    r = lint.check("Non non je suis humain, pas une IA")
    assert not r.passed
    assert any(i.rule == "ai_denial" for i in r.hard_issues)


def test_manipulation_pattern_blocks_hard():
    lint = VoiceLint()
    r = lint.check("Plus que 2 places disponibles aujourd'hui !")
    assert not r.passed
    assert any(i.rule == "manipulation" for i in r.hard_issues)


def test_banned_opener_emoji_blocks_hard():
    lint = VoiceLint()
    r = lint.check("🚀 On lance un nouveau truc cool")
    assert not r.passed
    assert any(i.rule == "banned_opener_emoji" for i in r.hard_issues)


def test_first_name_repeat_blocks():
    lint = VoiceLint(first_name_hint="Jean")
    r = lint.check("Salut Jean, Jean on fait ça ensemble ?")
    assert any(i.rule == "first_name_repeat" for i in r.hard_issues)


def test_suspicious_url_blocks():
    lint = VoiceLint()
    r = lint.check("Regarde ici bit.ly/abc123 c'est cool")
    assert any(i.rule == "suspicious_url" for i in r.hard_issues)


def test_soft_issues_warn_only():
    lint = VoiceLint()
    # Beaucoup d'emojis + 2 questions = soft, pas hard.
    r = lint.check("Cool 😎 😊 🎉 ça te dit ? ok sinon ?")
    assert r.soft_issues
    # Score dégradé mais pas hard.
    assert all(i.severity == "soft" for i in r.issues)


def test_clean_v6_example_passes():
    lint = VoiceLint(first_name_hint="Jean")
    msg = (
        "Salut Jean,\n\n"
        "J'ai vu que Dupont Carrelage tournait sur 4 chantiers simultanés en "
        "IDF — t'as un process pour tracker l'avancement ?\n\n"
        "Je demande parce qu'on a bossé ce flow spécifique pour 12 boîtes "
        "de carrelage en France.\n\n"
        "Si ça parle, on fait 15 min la semaine pro ?\n\n"
        "— Laurent"
    )
    r = lint.check(msg)
    # Le message canonique v6 doit passer (0 hard, score >= 0.8).
    # Note : 2 '?' → 1 soft, acceptable.
    assert not r.hard_issues, r.hard_issues
