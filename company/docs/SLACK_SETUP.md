# Créer l'app Slack pour le dialogue bidirectionnel

Tu as déjà un **incoming webhook** : il permet à l'agent de **t'écrire**.
Pour qu'il **te lise** (commande `/listen`), il faut un **bot Slack** avec le
scope `channels:history`. Voici la marche à suivre (~5 min).

## 1. Créer l'app
1. Va sur **https://api.slack.com/apps** → **Create New App** → **From scratch**.
2. Nom : `CEO Deco and pro` (ou ce que tu veux). Choisis ton **workspace**. → **Create App**.

## 2. Donner les permissions au bot
3. Menu de gauche → **OAuth & Permissions**.
4. Section **Scopes** → **Bot Token Scopes** → **Add an OAuth Scope**, ajoute :
   - `channels:history` — lire les messages des canaux publics **(indispensable)**
   - `chat:write` — pour que le bot puisse aussi écrire (optionnel mais conseillé)
   - `groups:history` — uniquement si ton canal est **privé**

## 3. Installer l'app
5. Remonte en haut de **OAuth & Permissions** → **Install to Workspace** → **Allow**.
6. Copie le **Bot User OAuth Token** : il commence par **`xoxb-...`**.
   → c'est ton `SLACK_BOT_TOKEN`.

## 4. Ajouter le bot au canal + récupérer l'ID du canal
7. Dans Slack, ouvre le canal voulu et tape : `/invite @CEO Deco and pro`
   (ajoute le bot au canal, sinon il ne voit rien).
8. Récupère le **Channel ID** :
   - clique sur le **nom du canal** en haut → onglet **À propos** → tout en bas,
     « ID du canal » : **`C0XXXXXXX`**.
   - (ou clic droit sur le canal → **Copier le lien** : l'ID est à la fin de l'URL.)
   → c'est ton `SLACK_CHANNEL_ID`.

## 5. Renseigner `.env`
Dans `company/.env` (déjà gitignoré) :
```
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0XXXXXXX
```

## 6. Tester
```bash
# écris un message dans le canal Slack, puis :
python orchestrator/orchestrator.py --listen
```
L'agent lit ton message, te répond naturellement, et exécute tes décisions
(« ok pour #1 »). Le curseur de lecture est mémorisé dans `state/slack_last_ts`.

## 7. (Optionnel) Dialogue continu
Lance `--listen` régulièrement via cron pour un échange permanent :
```cron
*/2 * * * * cd /chemin/vers/company && python orchestrator/orchestrator.py --listen >> state/listen.log 2>&1
```

---

### Notes
- L'incoming **webhook** (écrire) et le **bot token** (lire) sont deux choses
  distinctes ; les deux peuvent coexister.
- Tout reste **AMBRE** (réversible, ton propre canal) et journalisé ; aucune
  action ROUGE n'est exécutée sans ton accord explicite.
- Pour des réponses pleinement naturelles, `ANTHROPIC_API_KEY` doit être dans
  `.env` (sinon repli déterministe).
