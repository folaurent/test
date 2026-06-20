"""Tests des garde-fous (§10) — exécutable sans dépendance externe."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "orchestrator"))
import memory, guardrails as G, factory

# DB temporaire isolée
import tempfile
memory.DB_PATH = os.path.join(tempfile.mkdtemp(), "test.db")
conn = memory.connect()

ok = True
def check(label, cond):
    global ok
    print(("PASS " if cond else "FAIL ") + label)
    ok = ok and cond

# --- Classification ---
v_green = G.classify("analyse interne d'un fichier local")
check("VERT  : analyse interne -> GREEN", v_green.action_class == "GREEN")

v_amber = G.classify("appel API payante de scraping", cost=0.5)
check("AMBRE : api payante -> AMBER", v_amber.action_class == "AMBER")

v_red = G.classify("send_email à un vrai client")
check("ROUGE : envoi email réel -> RED", v_red.action_class == "RED")
check("ROUGE : requires_human", v_red.requires_human is True)

# Un agent ne peut pas déclasser un ROUGE
v_force = G.classify("publish content", explicit_class="GREEN")
check("Sécurité : ROUGE non déclassable", v_force.action_class == "RED")

# --- Gate : ROUGE mis en file, jamais exécuté ---
res = G.gate_action(conn, "growth-marketing", "publish content to site",
                    dry_run=True)
check("Gate ROUGE -> queued", res["outcome"] == "queued")
check("approvals_queue non vide", len(memory.list_approvals(conn)) == 1)

# Gate VERT -> exécuté
res2 = G.gate_action(conn, "engineering", "write_local draft", explicit_class="GREEN")
check("Gate VERT -> executed", res2["outcome"] == "executed")

# --- Exclusion de données : double verrou ---
before = memory.total_exclusion_attempts(conn)
# verrou 1 (intake)
clean, blocked = G.filter_excluded(conn, ["idée propre", "analyse sur Sika SA"])
check("Verrou 1 : item Sika bloqué", len(blocked) == 1 and len(clean) == 1)
# verrou 2 (execute)
res3 = G.gate_action(conn, "strategy-research", "analyser Parexlanko produits")
check("Verrou 2 : action Parexlanko bloquée", res3["outcome"] == "blocked_exclusion")
after = memory.total_exclusion_attempts(conn)
check("Compteur d'exclusion incrémenté (1 intake + 1 execute)", after == before + 2)

# --- Budget hard stop ---
memory.set_budget(conn, "cycle:0", 9.5, 10.0)
under = G.check_budget(conn, "cycle:0", 0.4, 10.0)
over = G.check_budget(conn, "cycle:0", 1.0, 10.0)
check("Budget : sous plafond autorisé", under is True)
check("Budget : dépassement -> hard stop", over is False)

# --- Kill switch ---
memory.set_state_flag("PAUSED")
res4 = G.gate_action(conn, "ceo", "write_local anything")
check("Kill switch : PAUSED bloque", res4["outcome"] == "blocked_paused")
memory.set_state_flag("RUNNING")

# --- Factory : crée un agent depuis un besoin d'une ligne ---
fres = factory.create_agent(conn, "besoin d'un spécialiste en publicité TikTok")
check("Factory : agent créé", fres["status"] == "created")
check("Factory : fichier .md écrit", os.path.exists(os.path.join(factory.ROOT, fres["path"])))
# Anti-prolifération
fres2 = factory.create_agent(conn, "spécialiste en publicité TikTok")
check("Factory : doublon réutilisé", fres2["status"] == "reused")

print("\n=== Compteur exclusion final (cible 0 en prod) :", after, "(attendu en test) ===")
print("RESULT:", "ALL PASS ✅" if ok else "SOME FAILED ❌")
sys.exit(0 if ok else 1)
