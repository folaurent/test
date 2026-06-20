# Déployer l'agent CEO 24/7 sur un VPS

L'agent tourne en boucle (`scripts/agent_loop.sh`) :
- **Dialogue** : lit Slack et répond (`--listen`) toutes les ~30 s ;
- **Gestion** : exécute un cycle de management toutes les ~1 h.

Sur un VPS, le disque est persistant : `state/company.db` (état, leçons,
décisions) et `state/slack_last_ts` survivent aux redémarrages. Deux méthodes,
au choix : **systemd** (natif) ou **Docker**.

---

## Prérequis (commun)

- Un VPS Linux avec accès Internet sortant vers `api.anthropic.com`,
  `slack.com`, `hooks.slack.com`, et `*.myshopify.com`.
- Git + Python 3.10+ (méthode systemd) **ou** Docker (méthode Docker).
- Tes secrets prêts (webhook Slack, clé API Anthropic, bot token + channel id).

```bash
# récupérer le code
git clone https://github.com/folaurent/test.git /opt/deco
cd /opt/deco
git checkout claude/install-markdown-file-gn6omh
cd company

# créer le fichier de secrets (jamais versionné)
cp .env.example .env
nano .env       # renseigne les valeurs ci-dessous
```

`.env` minimal pour le 24/7 :
```
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
ANTHROPIC_API_KEY=sk-ant-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0BBWFFE64E
COMPANY_LLM_MODEL=claude-opus-4-8
COMPANY_SLACK_ALERTS=1
# COMPANY_ALLOW_LIVE=1   # décommente pour des cycles en mode réel (sinon dry-run)
```

---

## Méthode A — systemd (recommandé)

```bash
cd /opt/deco/company
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
# (ou installe anthropic globalement : pip install -r requirements.txt)

# adapte WorkingDirectory/User dans le fichier si besoin (défaut: /opt/company, user deploy)
sudo cp deploy/company-agent.service /etc/systemd/system/
sudo sed -i 's#/opt/company#/opt/deco/company#' /etc/systemd/system/company-agent.service
sudo sed -i 's#^User=.*#User='"$USER"'#' /etc/systemd/system/company-agent.service
# si venv : fais pointer PYTHON vers le venv
echo "Environment=PYTHON=/opt/deco/company/.venv/bin/python" | sudo tee -a /etc/systemd/system/company-agent.service

sudo systemctl daemon-reload
sudo systemctl enable --now company-agent
journalctl -u company-agent -f          # suivre les logs en direct
```

Arrêter / redémarrer :
```bash
sudo systemctl stop company-agent
sudo systemctl restart company-agent
```

---

## Méthode B — Docker

```bash
cd /opt/deco/company
# .env déjà rempli à côté du docker-compose.yml
docker compose up -d --build
docker compose logs -f                   # suivre les logs
```

Arrêter / mettre à jour :
```bash
docker compose down
git pull && docker compose up -d --build
```

L'état est monté en volume (`./state`, `./reports`, `./artifacts`) → persistant.

---

## Vérifier que ça tourne

1. Écris un message dans **#pdg-claude** (ex. « ok lance le #1 »).
2. Dans les ~30 s, l'agent répond dans le canal (via le webhook).
3. Logs : `journalctl -u company-agent -f` ou `docker compose logs -f`.
4. À chaque cycle (1 h), tu reçois l'alerte « Cycle terminé + décisions en attente ».

---

## Mode réel (`--live`)

Par défaut, les **cycles** tournent en `--dry-run` (aucun effet de bord). Pour
passer en réel, mets `COMPANY_ALLOW_LIVE=1` dans `.env` puis redémarre. Même en
réel, **toute action ROUGE reste en file d'approbation** — l'agent ne publie /
ne dépense / n'écrit jamais sans ton « ok #id » explicite. Le dialogue Slack,
lui, fonctionne en continu quel que soit le mode.

---

## Sécurité

- `.env` n'est **jamais** versionné ni embarqué dans l'image Docker
  (`.gitignore` + `.dockerignore`).
- Restreins les droits : `chmod 600 .env`.
- Pense à **faire tourner (rotate)** clés/tokens si tu les as partagés ailleurs.
- Garde le VPS à jour ; expose le moins de ports possible (l'agent n'a besoin
  que du réseau **sortant**, aucun port entrant).
