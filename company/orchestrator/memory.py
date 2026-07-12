"""
memory.py — accès à l'état persistant de l'entreprise IA (SQLite).

Tout l'état vit dans state/company.db, ce qui rend la boucle
d'orchestration idempotente et reprenable : une nouvelle invocation
reprend là où la précédente s'est arrêtée.
"""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone

# Chemins ancrés sur la racine du projet /company, indépendamment du cwd.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_DIR = os.path.join(ROOT, "state")
DB_PATH = os.path.join(STATE_DIR, "company.db")
SCHEMA_PATH = os.path.join(STATE_DIR, "schema.sql")
STATE_FLAG = os.path.join(STATE_DIR, "STATE")


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect() -> sqlite3.Connection:
    """Ouvre la connexion (et initialise le schéma si nécessaire)."""
    first_time = not os.path.exists(DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    if first_time:
        init_db(conn)
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        conn.executescript(f.read())
    conn.commit()


# ----------------------------------------------------------------------
#  Journal d'audit — toute action y passe (principe directeur n°2)
# ----------------------------------------------------------------------
def audit(conn, actor_agent, action, payload=None, action_class="GREEN", reversible=True):
    conn.execute(
        "INSERT INTO audit_log (actor_agent, action, payload, action_class, reversible, ts) "
        "VALUES (?,?,?,?,?,?)",
        (actor_agent, action, json.dumps(payload, ensure_ascii=False) if payload is not None else None,
         action_class, 1 if reversible else 0, now()),
    )
    conn.commit()


# ----------------------------------------------------------------------
#  Helpers génériques
# ----------------------------------------------------------------------
def fetchall(conn, sql, params=()):
    return [dict(r) for r in conn.execute(sql, params).fetchall()]


def fetchone(conn, sql, params=()):
    r = conn.execute(sql, params).fetchone()
    return dict(r) if r else None


# ----------------------------------------------------------------------
#  Agents
# ----------------------------------------------------------------------
def list_agents(conn, status="active"):
    if status:
        return fetchall(conn, "SELECT * FROM agents WHERE status=? ORDER BY name", (status,))
    return fetchall(conn, "SELECT * FROM agents ORDER BY name")


def get_agent(conn, name):
    return fetchone(conn, "SELECT * FROM agents WHERE name=?", (name,))


def upsert_agent(conn, name, role, mission, prompt_path, tools, created_by="bootstrap"):
    existing = get_agent(conn, name)
    if existing:
        conn.execute(
            "UPDATE agents SET role=?, mission=?, system_prompt_path=?, tools=? WHERE name=?",
            (role, mission, prompt_path, tools, name),
        )
    else:
        conn.execute(
            "INSERT INTO agents (name, role, mission, system_prompt_path, tools, created_by) "
            "VALUES (?,?,?,?,?,?)",
            (name, role, mission, prompt_path, tools, created_by),
        )
    conn.commit()
    return get_agent(conn, name)


def set_agent_score(conn, name, score):
    conn.execute("UPDATE agents SET performance_score=? WHERE name=?", (score, name))
    conn.commit()


def set_agent_status(conn, name, status):
    conn.execute("UPDATE agents SET status=? WHERE name=?", (status, name))
    conn.commit()


# ----------------------------------------------------------------------
#  Initiatives & tâches
# ----------------------------------------------------------------------
def add_initiative(conn, title, hypothesis, rationale, priority=0, owner=None, expected_kpi=None):
    cur = conn.execute(
        "INSERT INTO initiatives (title, hypothesis, rationale, priority, owner_agent, expected_kpi) "
        "VALUES (?,?,?,?,?,?)",
        (title, hypothesis, rationale, priority, owner, expected_kpi),
    )
    conn.commit()
    return cur.lastrowid


def set_initiative(conn, iid, **fields):
    if not fields:
        return
    cols = ", ".join(f"{k}=?" for k in fields)
    conn.execute(f"UPDATE initiatives SET {cols} WHERE id=?", (*fields.values(), iid))
    conn.commit()


def list_initiatives(conn, status=None):
    if status:
        return fetchall(conn, "SELECT * FROM initiatives WHERE status=? ORDER BY priority DESC", (status,))
    return fetchall(conn, "SELECT * FROM initiatives ORDER BY priority DESC")


def add_task(conn, initiative_id, agent, description, depends_on=None):
    cur = conn.execute(
        "INSERT INTO tasks (initiative_id, assigned_agent, description, depends_on) VALUES (?,?,?,?)",
        (initiative_id, agent, description, depends_on),
    )
    conn.commit()
    return cur.lastrowid


def complete_task(conn, tid, output_ref):
    conn.execute(
        "UPDATE tasks SET status='done', output_ref=?, done_at=? WHERE id=?",
        (output_ref, now(), tid),
    )
    conn.commit()


def list_tasks(conn, status=None):
    if status:
        return fetchall(conn, "SELECT * FROM tasks WHERE status=?", (status,))
    return fetchall(conn, "SELECT * FROM tasks")


# ----------------------------------------------------------------------
#  Décisions & file d'approbation
# ----------------------------------------------------------------------
def add_decision(conn, context, options, chosen, rationale, decided_by,
                 action_class, requires_human):
    cur = conn.execute(
        "INSERT INTO decisions (context, options, chosen, rationale, decided_by, "
        "action_class, requires_human, status) VALUES (?,?,?,?,?,?,?,?)",
        (context, json.dumps(options, ensure_ascii=False), chosen, rationale, decided_by,
         action_class, 1 if requires_human else 0,
         "open" if requires_human else "executed"),
    )
    conn.commit()
    return cur.lastrowid


def enqueue_approval(conn, decision_id, summary, risk_level):
    cur = conn.execute(
        "INSERT INTO approvals_queue (decision_id, summary, risk_level) VALUES (?,?,?)",
        (decision_id, summary, risk_level),
    )
    conn.commit()
    return cur.lastrowid


def list_approvals(conn, status="pending"):
    return fetchall(conn, "SELECT * FROM approvals_queue WHERE status=? ORDER BY requested_at", (status,))


def resolve_approval(conn, approval_id, decision, resolved_by):
    """decision = 'approved' | 'rejected'"""
    row = fetchone(conn, "SELECT * FROM approvals_queue WHERE id=?", (approval_id,))
    if not row:
        return None
    conn.execute(
        "UPDATE approvals_queue SET status=?, resolved_at=?, resolved_by=? WHERE id=?",
        (decision, now(), resolved_by, approval_id),
    )
    conn.execute(
        "UPDATE decisions SET status=?, approved_by=? WHERE id=?",
        (decision, resolved_by, row["decision_id"]),
    )
    conn.commit()
    return row


# ----------------------------------------------------------------------
#  Métriques, leçons, exclusions, budget
# ----------------------------------------------------------------------
def record_metric(conn, name, value, unit, target, period):
    conn.execute(
        "INSERT INTO metrics (name, value, unit, target, period) VALUES (?,?,?,?,?)",
        (name, value, unit, target, period),
    )
    conn.commit()


def latest_metrics(conn):
    return fetchall(
        conn,
        "SELECT m.* FROM metrics m JOIN (SELECT name, MAX(recorded_at) mx FROM metrics GROUP BY name) g "
        "ON m.name=g.name AND m.recorded_at=g.mx ORDER BY m.name",
    )


def add_lesson(conn, source_initiative, observation, learning, action_taken):
    conn.execute(
        "INSERT INTO lessons (source_initiative, observation, learning, action_taken) VALUES (?,?,?,?)",
        (source_initiative, observation, learning, action_taken),
    )
    conn.commit()


def recent_lessons(conn, limit=10):
    return fetchall(conn, "SELECT * FROM lessons ORDER BY created_at DESC LIMIT ?", (limit,))


def exclusions(conn):
    return fetchall(conn, "SELECT * FROM data_exclusions ORDER BY forbidden_entity")


def bump_exclusion(conn, entity):
    conn.execute(
        "UPDATE data_exclusions SET attempted_access_count = attempted_access_count + 1 "
        "WHERE lower(forbidden_entity)=lower(?)",
        (entity,),
    )
    conn.commit()


def total_exclusion_attempts(conn):
    r = conn.execute("SELECT COALESCE(SUM(attempted_access_count),0) c FROM data_exclusions").fetchone()
    return r["c"]


def get_budget(conn, period):
    return fetchone(conn, "SELECT * FROM budget WHERE period=? ORDER BY id DESC LIMIT 1", (period,))


def set_budget(conn, period, spent, cap):
    existing = get_budget(conn, period)
    if existing:
        conn.execute("UPDATE budget SET spent=?, cap=?, recorded_at=? WHERE id=?",
                     (spent, cap, now(), existing["id"]))
    else:
        conn.execute("INSERT INTO budget (period, spent, cap) VALUES (?,?,?)", (period, spent, cap))
    conn.commit()


def add_spend(conn, period, amount, cap):
    b = get_budget(conn, period)
    spent = (b["spent"] if b else 0) + amount
    set_budget(conn, period, spent, cap)
    return spent


# ----------------------------------------------------------------------
#  Cycles
# ----------------------------------------------------------------------
def start_cycle(conn, mode):
    cur = conn.execute("INSERT INTO cycles (mode) VALUES (?)", (mode,))
    conn.commit()
    return cur.lastrowid


def end_cycle(conn, cycle_id, summary):
    conn.execute("UPDATE cycles SET ended_at=?, summary=? WHERE id=?", (now(), summary, cycle_id))
    conn.commit()


def cycle_count(conn):
    r = conn.execute("SELECT COUNT(*) c FROM cycles").fetchone()
    return r["c"]


# ----------------------------------------------------------------------
#  Kill switch
# ----------------------------------------------------------------------
def get_state_flag() -> str:
    if not os.path.exists(STATE_FLAG):
        return "RUNNING"
    with open(STATE_FLAG, "r", encoding="utf-8") as f:
        return f.read().strip().upper() or "RUNNING"


def set_state_flag(value: str) -> None:
    with open(STATE_FLAG, "w", encoding="utf-8") as f:
        f.write(value.strip().upper() + "\n")
