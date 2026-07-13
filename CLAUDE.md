# CLAUDE.md — Piloter le configurateur 3D Randal Studio

> Manuel opérationnel pour concevoir des meubles de salle de bain sur **Randal Studio**
> (`conf.randalsa.com/studio`), puis produire des visuels vendeurs fidèles via ChatGPT.
> Rédigé pour être exécuté par Claude Code avec l'outil **Claude in Chrome** (browser MCP).
> Tout est vérifié en pratique. Les pièges connus sont signalés ⚠️.

---

## 0. Contexte & objectif

- **Client / magasin** : `974 - DECO & PRO`. Login PRO : `PRO00974` (identifiants pré-remplis).
- **Techno du configurateur** : AngularJS 1.x + THREE.js dans un `<canvas>`.
- **But métier** : produire pour la boutique **Deco & Pro** des compositions **fidèles à ce que Randal fabrique réellement** (finitions + proportions), puis 2 visuels par produit :
  1. **Packshot** (fond neutre greige, de face) pour la fiche produit.
  2. **Mise en scène LUXE** (salle de bain haut de gamme dédiée) pour le lifestyle.
- **Règle d'or** : la conception **Randal** est TOUJOURS la référence envoyée à ChatGPT. Une éventuelle photo concurrent ne sert QU'À connaître les specs à reproduire, jamais de source visuelle.

---

## 1. Principes de pilotage (à respecter absolument)

1. **Tout piloter en JavaScript via le DOM / la scène Angular**, PAS au pixel.
   Le layout du panneau Randal bascule sans cesse étroit/large (la fenêtre se redimensionne 1512 ↔ 1539 ↔ 1568), ce qui décale toute coordonnée pixel → clics ratés. Le DOM et la scène THREE.js sont stables ; les coordonnées d'écran ne le sont pas.
2. **Ne JAMAIS drag/scroll librement sur la scène 3D** : ça oriente la caméra, zoome, ou ajoute un objet par erreur. Garder la caméra **de face** par défaut.
3. **Se repérer par le code** (projection 3D→écran), pas en tâtonnant la caméra à la souris.
4. Une **valeur d'affichage qui change ≠ géométrie appliquée**. Beaucoup de réglages n'entrent en vigueur qu'après **Confirmer**, et certains (largeur du meuble en scène vierge) nécessitent une séquence de déblocage (voir §4).
5. ⚠️ **Les overrides THREE.js (position, couleur, échelle) sont RÉINITIALISÉS à chaque re-render de l'app** (ex : après Confirmer, changement de cote, ajout d'objet). Donc : **coloration + positionnement + vue de face + capture** se font **en dernier, en une seule séquence immédiate**.

---

## 2. Accéder à l'app & à la scène THREE.js

### Connexion
Aller sur `index.php` → cliquer **« Accéder »** (submit, identifiants pré-remplis, ng-click `onLoginClick(appModel.login)`) → attendre ~4 s → studio « Magasin 974 DECO & PRO ». **NE PAS recharger ensuite** (perd l'état).

### Handle sur la scène Angular + THREE.js
```js
const scope = angular.element(document.querySelector('canvas')).scope();
const appState = scope.appState;
const scene = appState.threeScene;      // THREE.Scene
// aussi dispo : appState.sceneObjects, sceneInteractiveObjects, room
```

### Capturer caméra + renderer (ils sont en closure, pas exposés)
Poser un hook sur tous les objets puis déclencher un rendu :
```js
scene.traverse(o => o.onBeforeRender = (rndr, scn, cam) => { window.__cam = cam; window.__rend = rndr; });
// déclencher un rendu : micro pointermove synthétique sur le canvas
const cv = document.querySelector('canvas');
cv.dispatchEvent(new PointerEvent('pointermove', {bubbles:true, clientX:400, clientY:300}));
// → window.__cam (PerspectiveCamera fov 35), window.__rend (WebGLRenderer)
```
`Vector3` s'obtient via `window.__cam.position.constructor` (pas de `window.THREE` global).

### Bounding box monde d'un mesh (pas de Box3 global fiable)
Transformer les 8 coins de `mesh.geometry.boundingBox` par `mesh.matrixWorld`. Voir `snippets/scene_helpers.js`.

---

## 3. Se repérer en 3D & projeter 3D→écran

1. **Positions objets** : `scene.traverse` + `getWorldPosition` + `geometry.computeBoundingBox`.
2. **Projeter** un point monde vers l'écran :
   ```js
   const v = new (window.__cam.position.constructor)(x, y, z); v.project(window.__cam); // NDC
   const r = document.querySelector('canvas').getBoundingClientRect();
   const cx = r.left + (v.x*.5 + .5) * r.width;
   const cy = r.top  + (-v.y*.5 + .5) * r.height;   // coords CLIENT
   ```
3. ⚠️ **Client → screenshot** : l'échelle dépend du layout et n'est pas garantie uniforme.
   **Calibrer par screenshot** : repérer un objet déjà posé à l'écran (obsX, obsY), le projeter (baseClient), `scaleX = obsX/baseClient.x`, `scaleY = obsY/baseClient.y`, puis appliquer à la cible.
   (Cas observé viewport 1920×743 / screenshot 1568×607 → ×1,224 uniforme, mais **recalibrer à chaque fois**.)

### Vue de face par code (au lieu de galérer à la souris)
```js
const c = window.__cam, V = c.position.constructor, tx = 0.2, ty = 1.25; // viser le centre bbox du meuble
c.position.set(tx, ty, 4.7); c.up.set(0,1,0); c.lookAt(new V(tx, ty, 0));
c.updateProjectionMatrix(); c.updateMatrixWorld(true);
window.__rend.render(scene, c);
```

---

## 4. Concevoir un MEUBLE (caisson tiroirs)

### 4.1 Placer le 1er meuble dans une scène VIERGE ⚠️
En scène vide, « Confirmer » n'a pas de handler et le glisser-déposer oriente la caméra. **Solution** :
- Appeler la fonction scope **`onAddCustomModule()`**.
- Popup « espace siphon tiroir supérieur ? » → **Oui** = ng-click `onConfirmParameter('A')` (appeler via le scope du bouton si le clic rate).

### 4.2 Débloquer les options (séquence obligatoire — tip Laurent)
Cliquer **DANS L'ORDRE : Meubles → Tiroirs → 2 tiroirs**.
Sans cette séquence, le sous-type « 2 tiroirs » ne se sélectionne pas ET les sliders de cote / la préhension ne s'appliquent pas.

### 4.3 Dimensions (largeur / hauteur / profondeur)
Sliders = directives custom **`procedural-custom-panel-slider`** avec `component-type` = `length` (largeur) / `height` (hauteur) / `depth` (profondeur).
Piloter le bouton **+** (ou **-**) du bon directive en JS, **+1 cm par clic** :
```js
const dir = [...document.querySelectorAll('[procedural-custom-panel-slider][component-type="length"]')]
              .filter(e => e.offsetParent !== null)[0];
const plus = [...dir.querySelectorAll('*')].find(e => e.textContent.trim()==='+' && (e.className||'').toString().includes('slider-circl'));
const fire = el => ['mousedown','mouseup','click'].forEach(t => el.dispatchEvent(new MouseEvent(t,{bubbles:true,cancelable:true,view:window})));
for (let i=0;i<75;i++) fire(plus);   // +75 cm
```
- ⚠️ Ne PAS se fier au drag (= caméra), aux labels máx./mín. (sans handler), ni au double-clic (non éditable pour ces sliders).
- ⚠️ **Largeur en scène vierge parfois non appliquée** : l'affichage passe à 155 mais la géométrie reste 80 cm si la séquence §4.2 n'a pas été faite. Toujours faire Meubles→Tiroirs→2 tiroirs d'abord. Se mettre **en vue de face** avant toute modif du caisson (tip Laurent) pour vérifier.
- **Randal : largeur meuble max = 155 cm.** (Pour reproduire un 160 cm concurrent, utiliser 155.)

### 4.4 Préhension : Poignée vs Push (tip Laurent)
Cliquer **« Poignée »** (à côté de « Push ») → une petite **main** apparaît → **recliquer** pour valider la sélection.

### 4.5 Choisir le modèle de poignée
Finaliser/confirmer le meuble d'abord (sortir du mode édition) PUIS **cliquer la poignée dans la 3D** → un menu Poignée apparaît : types + tailles (201 / 320 / 360 / 600 / 900 mm) + couleurs (blanc / noir / chrome…). Choisir le modèle le plus proche de la cible (ex : barre fine noire).

### 4.6 Double vasque (siphon)
Meubles → régler Largeur → **Confirmer** → popup « plan + vasque à poser » → puis popup **« espace siphon simple ou double ? »** → **Double**.

---

## 5. Plan de travail & vasques

### 5.1 Ouvrir le panneau
Onglet **Plans de travail** → cliquer le **SYMBOLE (icône)** « Plans pour vasque à poser » pour dérouler : *Plan de travail / Vasque TORNE / Vasque NERIS*.
⚠️ La navigation d'onglet ne répond pas toujours à l'automation ; parfois il faut un clic manuel.

### 5.2 ✅ Méthode fiable « solid surface + puck » (recommandée — tip Laurent)
La plus simple et propre pour 2 vasques centrées :
1. Poser un **« Plan Vasque Semi-encastrée Solid Surface »** (déjà à la bonne largeur, ex 155).
2. Poser **« Vasque à poser puck »** → installe 1 vasque.
3. **Cliquer la vasque** → champ options → **Position > Centré / Double** → duplique en 2 vasques centrées.

### 5.3 Méthode « drag » (pose d'un plan / d'une vasque à poser)
Si tu poses par glisser-déposer :
- **JS grab** : `mousedown`/`pointerdown` sur l'img de l'item.
- **Hover réel** (extension `hover`) au-dessus du meuble → le VRAI mouvement curseur finalise le dépôt.
- **JS `mouseup`** sur le canvas à la position voulue (client = screenshot × innerW / screenshotW).
- ⚠️ Le grab JS « attrape » (la vasque flotte) mais c'est le **hover réel** qui pose. Viser bien la SURFACE du plan, pas trop près d'une vasque déjà posée.

### 5.4 ⚠️ Piège : redimensionner un plan déjà posé
Changer la Largeur du plan via `procedural-custom-panel-alone-slider` (component-type `aloneSupporterLength` / `aloneSupporterDepth`) + Confirmer **désolidarise** le plan (il tombe au sol / se recentre mal). → Préférer la méthode §5.2 (plan déjà à la bonne largeur).

---

## 6. Miroirs, auxiliaires (colonnes) & recentrage

### 6.1 Miroir
Catégorie **Miroirs** → drag d'un modèle (ex rond Ø80) sur le MUR **au même x** que le meuble → centré au-dessus.
- **Recentrer un miroir décalé** : centre du meuble = x du mesh `..._CARCASA` ; déplacer l'objet racine du miroir :
  ```js
  const m = scene.children.find(c => /STEEL|REDONDO|ESPEJO/i.test(c.name));
  m.position.x += (centreMeuble - m.position.x);
  scene.updateMatrixWorld(true); window.__rend.render(scene, window.__cam);
  ```

### 6.2 Auxiliaire / colonne
1. Onglet **Auxiliaires** → type (Portes / niche / Ouverts / lave-linge) + sous-type (1 porte / 2 portes…) + préhension (mettre la même que le meuble pour la cohérence).
2. Cotes via les boutons **+/-** des directives **`procedural-custom-auxiliary-panel-slider`** (`component-type` = `length` / `height` / `depth`), même mécanisme JS qu'au §4.3.
3. **Confirmer** → popup **sens d'ouverture de la porte** (À gauche / À droite).

### 6.3 Placer la colonne proprement (règles Laurent)
- **Jeu latéral 20-30 cm** entre le bord droit du meuble et la colonne :
  `col.position.x = (bordDroitMeuble + 0.25) − bordGaucheColonneActuel;` puis `col.updateMatrixWorld(true); window.__rend.render(scene, window.__cam);`
- **Bas aligné sous TOUS les angles** : donner à la colonne la **MÊME PROFONDEUR que le meuble** (ex 46 cm) et la laisser **dos au mur (z=0)** → faces avant coplanaires, arêtes avant-bas coïncidentes. ⚠️ Ne PAS avancer en z un meuble peu profond (crée un vide derrière = effet flottant, et le bas paraît plus haut en perspective).
- Vérifier **en pivotant la caméra** (gauche/droite/haut/bas) avant tout rendu.

---

## 7. Finitions & couleurs

### 7.1 Colorier via l'UI (méthode propre, meuble)
Cliquer la **façade (tiroir)** dans la 3D → panneau « Tiroir » : onglets **Couleur façade / Couleur chant**, palette **Finitions** (nuanciers `.jpg`) + **Finitions rainurées** (cannelé) + case **« Tout changer »**.
- **Tout changer COCHÉ** = applique à toutes les façades de l'élément.
- **Colorier UNE seule face (flanc)** : **DÉCOCHER « Tout changer »**, cliquer au **milieu du flanc** (sélectionne « Caisson »), puis la couleur. Le **caisson** est distinct de la **façade** (cliquer la façade avant = éditeur « Tiroir » ; un flanc = éditeur « Caisson »). Pour un rendu homogène : façade + caisson avant + flanc gauche + flanc droit + chants. (Astuce : zoomer à la molette pour viser la bonne face.)
- Appliquer un échantillon en JS (les swatches sont des DIV avec `background-image`) :
  ```js
  [...document.querySelectorAll('div')]
    .find(e => /siena\.jpg/i.test(getComputedStyle(e).backgroundImage))
    .dispatchEvent(new MouseEvent('click',{bubbles:true}));
  ```

### 7.2 Override matériau THREE.js (quand l'UI couleur ne s'ouvre pas, ex auxiliaire / anthracite)
⚠️ Purement **visuel**, pour la capture — réinitialisé au moindre re-render, donc à faire en dernier.
- Réutiliser une texture existante (ex bois) :
  ```js
  col.traverse(o => { if(o.isMesh) [].concat(o.material).forEach(m => {
    if (/MAT_(CARCASA|FRONTAL|CANTO)/.test(m.name||'')) { m.map = sienaMap; m.color.setHex(0xffffff); m.needsUpdate = true; }
  });});
  ```
- Couleur unie (ex **anthracite**) : `m.map=null; m.color.setHex(0x3b3e42); m.needsUpdate=true;` sur les faces `MAT_FRONTAL/CARCASA/CANTO`. Les poignées `MAT_TIRADOR` restent noires.
- **Bicolore** : n'appliquer la texture qu'aux `MAT_CARCASA`/`MAT_CANTO` (côtés/chants), laisser `MAT_FRONTAL` d'origine.

### 7.3 Noms de faces / meshes utiles
`MAT_FRONTAL` (façade), `MAT_CARCASA` (corps/côtés), `MAT_CANTO` (chants), `MAT_TIRADOR` (poignées).
Meshes exemples : meuble `2CAJ_A62_L155_..._TIR`, `..._CARCASA` ; plan `ALONE_SUPPORTER` ou `TAPA_...` ; vasques `BOWL_NERIS` ; colonne `ALTO1P_A155_L40_F30_...` ; miroir `STEEL 80 REDONDO`.

---

## 8. Finaliser, devis & export du rendu

1. **Finaliser / Résumé** : bouton **Finaliser** (`onFinishComposite`) → « Résumé de la configuration » : produits + **cotes** + finitions + prix. Extraire le texte via `modal.innerText`. Compter les Réf (doit = nb voulu, pas de doublon).
2. ⚠️ **L'impression PDF native n'est pas pilotable** (Chrome en lecture seule côté computer-use). → Reconstruire un **PDF propre** avec `reportlab` dans `/outputs` (voir la skill `pdf`).
3. **Rendu 3D → PNG** : se mettre en vue de face par code (§3) puis :
   ```js
   const cv = document.querySelector('canvas');
   window.__rend.render(scene, window.__cam);
   const url = cv.toDataURL('image/png');
   const a = document.createElement('a'); a.href = url; a.download = 'compo_randal.png'; a.click();
   ```
   → arrive dans **Téléchargements**. ⚠️ Le retour base64 est bloqué par l'outil JS ; ne pas tenter de le rapatrier en variable.
4. **Reset propre** = hamburger (haut-droite) → **« Nouveau projet »**.

---

## 9. Pipeline visuels ChatGPT (fidélité finitions = OBLIGATOIRE)

### 9.1 Règles fermes (Laurent)
1. Le **rendu 3D est DÉLAVÉ** (éclairage) → il sert **uniquement** à la disposition/proportions, JAMAIS à la couleur.
2. **Joindre à ChatGPT la VRAIE photo d'échantillon Randal de CHAQUE finition** présente, à **chaque** génération (packshot ET ambiance). Oublier une finition = rendu non fidèle. Ne jamais se contenter d'une description ou d'un override.
3. La conception **Randal** est la référence, pas une photo concurrent.

### 9.2 Récupérer les échantillons Randal
Page **`https://randal.group/fr/pro-meuble-sur-mesure/`** (section « NOS FINITIONS », 30 finitions).
Télécharger via **fetch same-origin → blob → `<a download>`**, fichiers `wp-content/uploads/<n>-<Nom>.png`.
Correspondances établies (config → nom public FR / fichier) :

| Usage | Finition config | Nom public FR | Fichier swatch |
|---|---|---|---|
| Terracotta meuble | « Siena » | #18 Terracota Nova / « Argile » | `18-Terracota-Nova.png` |
| Chêne (plan) | « Hickory Frida » (code 22) | #22 « Chêne Malmö » | `22-Hickory-Frida.png` |
| **Anthracite** (LAVOA) | pas de « anthracite » standard | **#13 « Gris Britannique » = Corona Basalto** (charbon mat) | `13-Corona-Basalto.png` |
| Blanc mat pur | — | #2 « Blanc mat » / Blanco mate | — |
| Miroir laiton | — | cadre « Oro Viejo » (doré vieilli) | — |

> Plan de travail LAVOA = **solid surface effet marbre blanc** (blanc légèrement veiné), PAS blanc uni/mat — idem pour les 2 vasques rondes. Le préciser explicitement à ChatGPT (et joindre une réf marbre si possible).

### 9.3 Joindre les fichiers à ChatGPT
- Connecter le dossier **Téléchargements** (`request_cowork_directory C:\Users\<user>\Downloads`) → `file_upload` peut alors prendre les PNG (rendu + échantillons).
- ⚠️ Pièges outillage confirmés :
  - Upload par **imageId de capture = ÉCHOUE** (« Unable to access message history »).
  - **Coller une image dans Chrome = IMPOSSIBLE**.
  - ChatGPT ouvre parfois l'**éditeur d'image** au lieu du chat → fermer avec **✕** (haut-gauche ~86,31) puis utiliser le **composeur principal**.
  - L'onglet ChatGPT peut geler → réessayer.

### 9.4 Prompt
Reproduire la compo (disposition/proportions du rendu 3D joint) **avec la couleur EXACTE de chaque échantillon joint**, en nommant quelle finition va sur quelle pièce. Produire 2 visuels :
- **Packshot** fond greige neutre, de face.
- **Mise en scène LUXE** : salle de bain haut de gamme dédiée (lumière naturelle, pierre, plante/olivier, serviettes lin, baignoire îlot…), finitions + proportions fidèles.
Itérer en langage naturel si un détail cloche (ex : « plan trop épais → fine tablette ~2 cm »).

### 9.5 Télécharger les images générées
Ouvrir l'image → bouton téléchargement (haut-droite) → **« Télécharger les 2 images de cette série »** → arrivent dans Téléchargements. Puis archiver/renommer.

---

## 10. Archivage

Créer un dossier au nom de la compo dans les livrables :
- fiche produit `.md` (specs + cotes + description vendeuse + SEO),
- devis PDF (reportlab),
- le rendu 3D Randal (`*_Randal.png`),
- le packshot (`*_Packshot.png`) et l'ambiance (`*_Ambiance_Luxe.png`),
- la liste des finitions/échantillons utilisés.

---

## 11. Exemples de compositions réalisées (références)

- **DUO 120 terracotta + colonne** : meuble 120 double vasque, plan chêne, 2 vasques NERIS blanches, miroir laiton Ø80 centré, colonne ALTO 1 porte 40×155×46 terracotta (jeu 25 cm, bas aligné). **≈ 2 196,75 €.**
- **LAVOA 160 anthracite (reproduction concurrent Bernstein)** : caisson **155**×62×46 anthracite mat 2 tiroirs, poignées barre noires, plan solid surface effet marbre blanc, 2 vasques rondes blanches, sans miroir. **≈ 4 068 €.** Finitions envoyées à ChatGPT : #13 Corona Basalto (anthracite) + solid surface effet marbre.

---

## 12. Checklist express (pour aller vite)

1. `index.php` → **Accéder** → attendre studio (ne pas recharger).
2. Meuble : **`onAddCustomModule()`** → siphon Oui → **Meubles → Tiroirs → 2 tiroirs** → cotes via +JS des `procedural-custom-panel-slider` → préhension Poignée.
3. Plan + vasques : méthode **solid surface + puck** → Position > Centré/Double.
4. Poignée : cliquer la poignée en 3D → menu → modèle proche cible.
5. Finitions : UI si possible, sinon override THREE (en DERNIER).
6. Vérifier en **pivotant la caméra**. NE PAS générer ChatGPT tant que le meuble n'est pas ENTIÈREMENT réalisé.
7. **Finaliser** → specs/prix → PDF reportlab. Vue de face par code → `toDataURL` → PNG.
8. ChatGPT : joindre rendu + **échantillons réels de CHAQUE finition** → packshot + ambiance luxe → télécharger les 2 → archiver.

---

_Snippets JS réutilisables dans `snippets/`._
