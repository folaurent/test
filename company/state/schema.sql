-- ============================================================
--  company.db — schéma de l'état partagé (§8)
--  SQLite. Toutes les tables de la mémoire de l'entreprise IA.
-- ============================================================

PRAGMA foreign_keys = ON;

-- Registre des agents (roster initial + agents créés par l'Agent Factory)
CREATE TABLE IF NOT EXISTS agents (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    name                TEXT UNIQUE NOT NULL,
    role                TEXT,
    mission             TEXT,
    system_prompt_path  TEXT,
    tools               TEXT,                 -- liste blanche, séparée par des virgules
    status              TEXT DEFAULT 'active',-- active | quarantined | retired
    created_by          TEXT DEFAULT 'bootstrap',
    created_at          TEXT DEFAULT (datetime('now')),
    performance_score   REAL DEFAULT 0.5      -- 0..1, neutre = 0.5
);

-- Initiatives stratégiques décidées par le CEO
CREATE TABLE IF NOT EXISTS initiatives (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    title         TEXT NOT NULL,
    hypothesis    TEXT,
    rationale     TEXT,
    status        TEXT DEFAULT 'proposed',    -- proposed | planned | running | closed
    priority      REAL DEFAULT 0,             -- score impact×effort×risque
    owner_agent   TEXT,
    expected_kpi  TEXT,
    result        TEXT,
    created_at    TEXT DEFAULT (datetime('now')),
    closed_at     TEXT
);

-- Tâches déléguées aux agents
CREATE TABLE IF NOT EXISTS tasks (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    initiative_id  INTEGER REFERENCES initiatives(id),
    assigned_agent TEXT,
    description    TEXT,
    status         TEXT DEFAULT 'todo',       -- todo | doing | done | blocked
    output_ref     TEXT,                      -- chemin du livrable dans /artifacts
    depends_on     INTEGER,                   -- id d'une autre tâche
    created_at     TEXT DEFAULT (datetime('now')),
    done_at        TEXT
);

-- Décisions tracées (avec classification d'action et statut d'approbation)
CREATE TABLE IF NOT EXISTS decisions (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    context       TEXT,
    options       TEXT,
    chosen        TEXT,
    rationale     TEXT,
    decided_by    TEXT,
    action_class  TEXT,                       -- GREEN | AMBER | RED
    requires_human INTEGER DEFAULT 0,
    approved_by   TEXT,
    status        TEXT DEFAULT 'open',        -- open | approved | rejected | executed
    created_at    TEXT DEFAULT (datetime('now'))
);

-- Métriques / KPI vs cibles
CREATE TABLE IF NOT EXISTS metrics (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT,
    value       REAL,
    unit        TEXT,
    target      REAL,
    period      TEXT,
    recorded_at TEXT DEFAULT (datetime('now'))
);

-- Leçons apprises (auto-amélioration)
CREATE TABLE IF NOT EXISTS lessons (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    source_initiative INTEGER,
    observation       TEXT,
    learning          TEXT,
    action_taken      TEXT,
    created_at        TEXT DEFAULT (datetime('now'))
);

-- Journal d'audit exhaustif (qui, quoi, classe, réversible, quand)
CREATE TABLE IF NOT EXISTS audit_log (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    actor_agent  TEXT,
    action       TEXT,
    payload      TEXT,
    action_class TEXT,
    reversible   INTEGER,
    ts           TEXT DEFAULT (datetime('now'))
);

-- File d'approbation humaine (toute action ROUGE atterrit ici)
CREATE TABLE IF NOT EXISTS approvals_queue (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    decision_id  INTEGER REFERENCES decisions(id),
    summary      TEXT,
    risk_level   TEXT,
    requested_at TEXT DEFAULT (datetime('now')),
    status       TEXT DEFAULT 'pending',      -- pending | approved | rejected
    resolved_at  TEXT,
    resolved_by  TEXT
);

-- Exclusions de données strictes (double verrou) — seed Sika, Parexlanko
CREATE TABLE IF NOT EXISTS data_exclusions (
    id                     INTEGER PRIMARY KEY AUTOINCREMENT,
    forbidden_entity       TEXT UNIQUE NOT NULL,
    attempted_access_count INTEGER DEFAULT 0
);

-- Suivi du budget par cycle + global
CREATE TABLE IF NOT EXISTS budget (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    period        TEXT,                       -- 'cycle:<n>' ou 'global'
    spent         REAL DEFAULT 0,
    cap           REAL,
    recorded_at   TEXT DEFAULT (datetime('now'))
);

-- Compteur de cycles exécutés
CREATE TABLE IF NOT EXISTS cycles (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at  TEXT DEFAULT (datetime('now')),
    ended_at    TEXT,
    mode        TEXT,                          -- dry-run | live
    summary     TEXT
);

-- Seed des entités interdites (compteur à 0)
INSERT OR IGNORE INTO data_exclusions (forbidden_entity, attempted_access_count)
VALUES ('Sika', 0), ('Parexlanko', 0);
