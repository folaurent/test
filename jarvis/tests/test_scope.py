"""Verrou scope — tests non négociables. Si un test casse, le deploy casse."""
import pytest

from jarvis.core.config import Settings
from jarvis.core.scope import SCOPE_SYSTEM_PREFIX, ScopeError, ScopeFilter


def _settings(excluded: str = "sika,parexlanko") -> Settings:
    return Settings(scope_excluded_ventures=excluded)


def test_filter_always_includes_sika_parexlanko_even_if_config_lies():
    s = _settings(excluded="autrechose")
    # La config validator doit re-forcer sika + parexlanko.
    assert "sika" in s.excluded_ventures
    assert "parexlanko" in s.excluded_ventures


def test_boot_blocked_if_scope_invalid():
    # Construire un ScopeFilter avec excluded vide lève ScopeError.
    with pytest.raises(ScopeError):
        ScopeFilter(excluded=set())


def test_text_matches_sika_word_boundary():
    f = ScopeFilter.from_settings(_settings())
    violations = f.check_text("On doit éviter Sika France sur ce coup")
    assert len(violations) == 1
    assert violations[0].term == "sika"


def test_text_matches_parexlanko_variants():
    f = ScopeFilter.from_settings(_settings())
    for text in ("parexlanko", "Parex Lanko", "Parex-Lanko", "PAREXLANKO"):
        assert f.check_text(text), f"failed: {text}"


def test_text_does_not_false_positive_on_harmless_substrings():
    f = ScopeFilter.from_settings(_settings())
    # "sikaran" est un art martial, "parex" seul n'est pas bloqué.
    assert not f.check_text("sikaran est un art martial philippin")


def test_tag_check():
    f = ScopeFilter.from_settings(_settings())
    assert f.check_tag("Sika") is not None
    assert f.check_tag("parexlanko") is not None
    assert f.check_tag("jonction") is None
    assert f.check_tag(None) is None


def test_assert_clean_raises():
    f = ScopeFilter.from_settings(_settings())
    with pytest.raises(ScopeError):
        f.assert_clean("tu peux me rédiger un mail pour sika ?")


def test_system_prefix_mentions_both_brands():
    assert "Sika" in SCOPE_SYSTEM_PREFIX
    assert "Parexlanko" in SCOPE_SYSTEM_PREFIX
    assert "non-négociable" in SCOPE_SYSTEM_PREFIX
