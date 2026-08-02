# Jarvis Slack adapter — setup

Adapter Slack en **Socket Mode** (aucun webhook public à exposer, marche
en sandbox comme sur Railway/VPS). Pipeline identique à Telegram :
scope filter → orchestrator → voice lint → compliance.

## 1. Créer la Slack app

1. https://api.slack.com/apps → **Create New App** → *From an app manifest*
2. Choisis ton workspace, colle le manifest ci-dessous :

```yaml
display_information:
  name: Jarvis
  description: Chef de cabinet numérique de Laurent
  background_color: "#0b0f19"
features:
  bot_user:
    display_name: Jarvis
    always_online: true
  slash_commands:
    - command: /jarvis-ping
      description: Ping le bot
      usage_hint: ""
    - command: /jarvis-status
      description: État du bot
      usage_hint: ""
    - command: /jarvis-scope
      description: Périmètre verrouillé
      usage_hint: ""
    - command: /jarvis-voice
      description: Test du voice lint
      usage_hint: "<texte>"
    - command: /jarvis-plan
      description: Demande un plan au Builder
      usage_hint: "<intention>"
oauth_config:
  scopes:
    bot:
      - app_mentions:read
      - chat:write
      - commands
      - im:history
      - im:read
      - im:write
settings:
  event_subscriptions:
    bot_events:
      - app_mention
      - message.im
  interactivity:
    is_enabled: true
  socket_mode_enabled: true
```

3. **Install to Workspace** → récupère le `Bot User OAuth Token`
   (`xoxb-...`) → `SLACK_BOT_TOKEN`
4. **Basic Information → App-Level Tokens → Generate Token and Scopes** :
   nom `socket`, scope `connections:write` → récupère le `xapp-...` →
   `SLACK_APP_TOKEN`

## 2. Renseigner `.env`

```bash
SLACK_BOT_TOKEN=xoxb-...
SLACK_APP_TOKEN=xapp-...
SLACK_ALLOWED_USER_IDS=U0XXXXXXX          # ton user id Slack
SLACK_ALLOWED_CHANNEL_ID=                 # optionnel : restreint à un channel
```

Pour trouver ton `user_id` : dans Slack, clic sur ton avatar → *View
profile* → *More* (…) → *Copy member ID*. Format `U0XXXXXXX`.

## 3. Lancer

Le hook `session-start` de Claude Code spawne automatiquement le
supervisor Slack en parallèle du supervisor Telegram (idempotent : si les
tokens sont absents il skip).

Manuel :

```bash
cd jarvis/
bash scripts/supervisor_slack.sh &
tail -f logs/slack.log
```

## 4. Utilisation

- **DM** : envoie un message à `@Jarvis` en privé → réponse en top-level
- **Channel** : mentionne `@Jarvis <question>` → réponse en thread
- **Slash** : `/jarvis-ping`, `/jarvis-status`, `/jarvis-plan <intent>`,
  `/jarvis-voice <texte>`, `/jarvis-scope` (réponses ephemeral)

## Pipeline

`slack_bot.bot` → `SlackAuth` → `JarvisOrchestrator.handle()` →
`ScopeFilter` → `VoiceLint` → `Compliance` → réponse.

Exactement le même que `telegram_bot`, aucun raccourci — les évals
voice/scope s'appliquent aussi côté Slack.
