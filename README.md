# Randal_ClaudeCode — projet pour piloter le configurateur 3D Randal

Ce dossier contient tout ce que Claude a appris sur l'outil de conception **Randal Studio**
(`conf.randalsa.com/studio`), packagé pour être utilisé avec **Claude Code**.

## Contenu
- **`CLAUDE.md`** — le manuel opérationnel complet. Claude Code le lit automatiquement au
  démarrage quand il est lancé depuis ce dossier. C'est le cœur : connexion, pilotage JS,
  création meuble/plan/vasques/colonne, finitions, export, pipeline visuels ChatGPT, pièges.
- **`snippets/scene_helpers.js`** — fonctions JS prêtes à copier-coller dans la console de
  l'onglet Randal (accès scène, projection 3D→écran, sliders de cote, override couleur,
  export PNG, téléchargement des échantillons…).

## Comment l'utiliser avec Claude Code
1. Ouvre un terminal dans ce dossier :
   ```
   cd "C:\Users\Laurent\Downloads\Randal_ClaudeCode"
   claude
   ```
2. Claude Code chargera `CLAUDE.md` comme contexte projet.
3. Assure-toi que l'extension **Claude in Chrome** (browser MCP) est connectée : c'est elle
   qui permet de piloter l'onglet du configurateur et ChatGPT.
4. Donne ta demande, ex : *« reproduis le meuble X en anthracite avec 2 vasques et génère
   un packshot + une ambiance luxe »*. Claude suivra la checklist du §12.

## Rappels clés (voir CLAUDE.md pour le détail)
- Tout se pilote en **JS/DOM**, jamais au pixel (le layout Randal bascule sans cesse).
- Ne pas générer les visuels ChatGPT tant que le meuble n'est pas **entièrement réalisé**.
- **Toujours joindre à ChatGPT la vraie photo d'échantillon Randal de CHAQUE finition.**
- La conception Randal est la référence, jamais une photo concurrent.
