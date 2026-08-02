from jarvis.agents.base import AgentBase, AgentCharter, AutonomyLevel
from jarvis.voice.dna import DISCLOSURE_POLICY


def test_system_prompt_contains_scope_prefix():
    agent = AgentBase(
        AgentCharter(
            name="X", venture="jonction", mission="test", human_facing=False,
            autonomy=AutonomyLevel.SHADOW,
        )
    )
    sp = agent.system_prompt()
    assert "Sika" in sp
    assert "Parexlanko" in sp


def test_system_prompt_injects_voice_when_human_facing():
    agent = AgentBase(
        AgentCharter(
            name="ConvFR", venture="jonction", mission="test",
            human_facing=True, autonomy=AutonomyLevel.PROPOSE,
        )
    )
    sp = agent.system_prompt()
    assert "VOIX" in sp.upper()
    # Disclosure policy présente sur agents en contact humain.
    assert "Bien vu" in sp or "assistant" in sp.lower()


def test_system_prompt_excludes_voice_when_internal():
    agent = AgentBase(
        AgentCharter(
            name="Dev", venture="transverse", mission="test",
            human_facing=False, autonomy=AutonomyLevel.SHADOW,
        )
    )
    sp = agent.system_prompt()
    # Pas de voice block pour agents internes (pas d'impact si inversé, mais
    # le bloc voice est réservé aux agents human_facing).
    assert "[VOIX JARVIS" not in sp


def test_tool_allowlist_enforcement():
    agent = AgentBase(
        AgentCharter(
            name="X", venture="jonction", mission="test",
            tool_allowlist=["search", "read_file"],
        )
    )
    agent.assert_tool_allowed("search")
    try:
        agent.assert_tool_allowed("shell_exec")
    except PermissionError:
        return
    raise AssertionError("tool outside allowlist should raise")


def test_disclosure_policy_content():
    assert "JAMAIS" in DISCLOSURE_POLICY
    assert "assistant" in DISCLOSURE_POLICY.lower()
