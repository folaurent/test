# WhatsApp Desktop Assistant

Application Windows locale d'assistance WhatsApp, orientée productivité. Elle analyse les messages reçus sur WhatsApp Desktop et propose ou envoie des réponses automatiquement selon des règles configurables.

## Architecture

```
app/
  main.py              # Point d'entrée
  ui/
    main_window.py     # Interface customtkinter
    app_controller.py  # Contrôleur applicatif
  automation/
    whatsapp_controller.py  # Pilotage WhatsApp Desktop via pywinauto
  ai/
    base_provider.py     # Interface abstraite IA
    mock_provider.py     # Provider simulé (tests)
    openai_provider.py   # Provider OpenAI
    anthropic_provider.py # Provider Anthropic Claude
    provider_factory.py  # Factory pattern
  services/
    rules_engine.py      # Moteur de règles
    message_processor.py # Orchestrateur principal
  models/
    message.py          # Modèles de données
  storage/
    database.py         # Persistance SQLite
  utils/
    logger.py           # Configuration logging
    hashing.py          # Hachage anti-doublon
config/
  settings.py          # Configuration centralisée
tests/                 # Tests unitaires
logs/                  # Fichiers de logs
data/                  # Base de données SQLite
```

## Prérequis

- **Windows 10/11** avec WhatsApp Desktop installé (depuis le Microsoft Store ou le site officiel)
- **Python 3.10+**
- WhatsApp Desktop doit etre ouvert et connecté à votre compte

## Installation pas à pas

### 1. Cloner le projet

```bash
git clone <url-du-repo>
cd whatsapp-desktop-assistant
```

### 2. Créer un environnement virtuel

```bash
python -m venv venv
venv\Scripts\activate
```

### 3. Installer les dépendances

```bash
pip install -r requirements.txt
```

**Sur Windows**, décommenter pywinauto dans `requirements.txt` :
```bash
pip install pywinauto
```

**Pour OpenAI** :
```bash
pip install openai
```

**Pour Anthropic Claude** :
```bash
pip install anthropic
```

### 4. Configurer l'environnement

```bash
copy .env.example .env
```

Editez `.env` avec vos paramètres :
- `SIMULATION_MODE=true` pour commencer (aucun message envoyé)
- `AI_PROVIDER=mock` pour tester sans clé API
- `WHATSAPP_USER_NAME=` votre nom exact dans WhatsApp (anti-boucle)

### 5. Lancer l'application

```bash
python run.py
```

## Modes de fonctionnement

| Mode | Description |
|------|-------------|
| **Brouillon** (`draft_only`) | Génère les réponses sans jamais les envoyer. Mode par défaut. |
| **Validation manuelle** (`manual_validation`) | Propose la réponse et attend votre clic pour envoyer. |
| **Auto-réponse** (`auto_reply`) | Envoie automatiquement, **uniquement pour les contacts explicitement autorisés**. |

## Fonctionnalités

- Surveillance continue de WhatsApp Desktop
- Détection des messages non lus
- Whitelist / Blacklist de contacts
- Moteur de règles avec priorités (urgent, question, normal)
- Adaptation du ton par contact (professionnel, amical, décontracté)
- Provider IA interchangeable (Mock / OpenAI / Anthropic)
- Mode template (réponses prédéfinies sans IA)
- Anti-boucle (ne répond jamais à ses propres messages)
- Anti-spam (ne répond jamais deux fois au même message)
- Journal d'activité complet
- Historique SQLite de tous les messages et réponses
- Bouton d'arrêt d'urgence
- Mode simulation complet

## Sécurités

- **Mode brouillon par défaut** : aucun message envoyé sans action explicite
- **Anti-boucle** : détection du nom utilisateur pour ne jamais répondre à soi-même
- **Anti-doublon** : hash SHA-256 de chaque message pour éviter les doubles traitements
- **Auto-réponse restreinte** : uniquement pour les contacts explicitement marqués
- **Aucune télémétrie** : les données ne quittent pas votre machine (sauf vers le provider IA configuré)
- **Clés API dans `.env`** : jamais hardcodées, jamais committées

## Tests

```bash
pytest tests/ -v
```

```bash
pytest tests/ -v --cov=app
```

## Points de fragilité connus

L'automatisation de WhatsApp Desktop repose sur **pywinauto** et l'arbre d'accessibilité Windows. Cela implique :

1. **Sélecteurs UI** : Les noms de contrôles peuvent changer lors des mises à jour de WhatsApp. Le module `whatsapp_controller.py` documente chaque point fragile.

2. **Distinction messages reçus/envoyés** : L'heuristique basée sur les checkmarks (✓) peut varier selon la version.

3. **Langue de Windows** : Le titre de la fenêtre et les labels d'accessibilité dépendent de la langue du système.

### Alternatives si l'automatisation UI échoue

- **OCR (pytesseract)** : Capturer l'écran et extraire le texte par reconnaissance optique
- **Clipboard monitoring** : Copier manuellement les messages et laisser l'assistant proposer des réponses
- **Mode semi-manuel** : Utiliser l'application uniquement comme générateur de réponses, sans automatisation de lecture/envoi

## Debug

### WhatsApp non détecté
- Vérifiez que WhatsApp Desktop est ouvert
- Vérifiez que vous n'avez pas plusieurs instances
- Lancez en mode simulation d'abord (`SIMULATION_MODE=true`)

### pywinauto ne trouve pas les contrôles
- Utilisez l'outil `inspect.exe` (SDK Windows) pour explorer l'arbre d'accessibilité
- Ou `python -c "from pywinauto import Desktop; Desktop(backend='uia').print_control_identifiers()"`

### Les réponses ne s'envoient pas
- Vérifiez que `SIMULATION_MODE=false`
- Vérifiez que le mode n'est pas `draft_only`
- Vérifiez les logs dans `logs/`

## Licence

Usage personnel uniquement. Ce projet n'est pas affilié à WhatsApp ou Meta.
