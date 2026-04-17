"""Backend Claude CLI — utilise le binaire `claude` en subprocess.

Pourquoi : quand on n'a pas de clef Anthropic brute, le CLI local (installé
avec Claude Code) nous donne accès aux modèles via l'OAuth existant.
Interface compatible avec AnthropicClient.call() → remplacement plug-and-play.

Coût : le CLI charge son system prompt (skills, CLAUDE.md) → 1er call ~$0.03.
Les suivants bénéficient du cache prompt (cache_read beaucoup moins cher).
Jalon 1.3 bascule sur SDK Anthropic brut dès qu'une clef ANTHROPIC_API_KEY
est fournie.

Sécurité : le subprocess hérite de l'env. Le system prompt Jarvis est
transmis via --system-prompt qui REMPLACE le prompt par défaut pour tout
ce qu'on contrôle.
"""
from __future__ import annotations

import asyncio
import json
import os
import shutil
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class CliCallResult:
    ok: bool
    text: str
    model: str
    input_tokens: int
    output_tokens: int
    cache_read_input_tokens: int
    cache_creation_input_tokens: int
    cost_usd: float
    duration_ms: int
    raw: dict[str, Any]


class ClaudeCliBackend:
    MODEL_ALIAS = {
        # Claude Code accepte alias (sonnet/opus/haiku) ou noms complets.
        "claude-haiku-4-5-20251001": "haiku",
        "claude-sonnet-4-6": "sonnet",
        "claude-opus-4-7": "opus",
    }

    def __init__(self, binary: str | None = None, cwd: str | None = None) -> None:
        self._bin = binary or shutil.which("claude") or "claude"
        # Dossier d'exécution isolé : empêche le CLI d'auto-charger les
        # CLAUDE.md du projet et de polluer le system prompt.
        if cwd is None:
            self._cwd = tempfile.mkdtemp(prefix="jarvis_cli_")
            # Marqueur neutre pour éviter toute auto-découverte.
            Path(self._cwd, ".noskillsauto").touch()
        else:
            self._cwd = cwd

    def available(self) -> bool:
        return bool(shutil.which(self._bin))

    async def call(
        self,
        *,
        model: str,
        system: str,
        user: str,
        max_tokens: int = 1024,
        temperature: float | None = None,  # CLI n'accepte pas temperature
        timeout_s: float = 90.0,
    ) -> CliCallResult:
        alias = self.MODEL_ALIAS.get(model, model)
        args = [
            self._bin, "-p",
            "--model", alias,
            "--system-prompt", system,
            "--output-format", "json",
            "--no-session-persistence",
            "--disable-slash-commands",
            "--exclude-dynamic-system-prompt-sections",
            "--disallowedTools", "Bash,Edit,Write,Read,Grep,Glob,TodoWrite,Task,Agent",
        ]
        # Env clean : CLI_CODE_SIMPLE pour lui dire qu'on veut peu de features.
        env = dict(os.environ)
        env["CLAUDE_CODE_DISABLE_TELEMETRY"] = "1"
        start = time.monotonic()
        proc = await asyncio.create_subprocess_exec(
            *args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=self._cwd,
            env=env,
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(user.encode("utf-8")), timeout=timeout_s
            )
        except asyncio.TimeoutError:
            proc.kill()
            raise RuntimeError(f"claude_cli timeout after {timeout_s}s")

        duration_ms = int((time.monotonic() - start) * 1000)
        if proc.returncode != 0:
            raise RuntimeError(
                f"claude_cli exit={proc.returncode} err={stderr.decode('utf-8', 'replace')[:500]}"
            )

        try:
            data = json.loads(stdout.decode("utf-8"))
        except json.JSONDecodeError as e:
            raise RuntimeError(f"claude_cli bad json: {e}") from e

        is_error = bool(data.get("is_error"))
        result_text = data.get("result", "")
        usage = data.get("usage", {}) or {}
        return CliCallResult(
            ok=not is_error,
            text=result_text,
            model=model,
            input_tokens=int(usage.get("input_tokens", 0) or 0),
            output_tokens=int(usage.get("output_tokens", 0) or 0),
            cache_read_input_tokens=int(usage.get("cache_read_input_tokens", 0) or 0),
            cache_creation_input_tokens=int(usage.get("cache_creation_input_tokens", 0) or 0),
            cost_usd=float(data.get("total_cost_usd", 0.0) or 0.0),
            duration_ms=duration_ms,
            raw=data,
        )
