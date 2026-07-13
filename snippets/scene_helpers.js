// ============================================================================
// Randal Studio — snippets JS réutilisables (à exécuter dans l'onglet du studio)
// Voir CLAUDE.md pour le contexte. Tout passe par le DOM / la scène THREE.js.
// ============================================================================

// --- 1. Handle scène + caméra + renderer ------------------------------------
function randalScene() {
  const scope = angular.element(document.querySelector('canvas')).scope();
  return { scope, appState: scope.appState, scene: scope.appState.threeScene };
}

// Capturer caméra + renderer (en closure) : poser un hook puis déclencher un rendu.
function captureCam() {
  const { scene } = randalScene();
  scene.traverse(o => o.onBeforeRender = (rndr, scn, cam) => { window.__cam = cam; window.__rend = rndr; });
  const cv = document.querySelector('canvas');
  cv.dispatchEvent(new PointerEvent('pointermove', { bubbles: true, clientX: 400, clientY: 300 }));
  return { cam: window.__cam, rend: window.__rend };
}

// --- 2. Bounding box monde d'un mesh ----------------------------------------
function worldBBox(mesh) {
  mesh.geometry.computeBoundingBox();
  const bb = mesh.geometry.boundingBox;
  const V = window.__cam.position.constructor;
  const corners = [
    [bb.min.x, bb.min.y, bb.min.z], [bb.max.x, bb.min.y, bb.min.z],
    [bb.min.x, bb.max.y, bb.min.z], [bb.max.x, bb.max.y, bb.min.z],
    [bb.min.x, bb.min.y, bb.max.z], [bb.max.x, bb.min.y, bb.max.z],
    [bb.min.x, bb.max.y, bb.max.z], [bb.max.x, bb.max.y, bb.max.z],
  ];
  const min = new V(Infinity, Infinity, Infinity), max = new V(-Infinity, -Infinity, -Infinity);
  mesh.updateMatrixWorld(true);
  corners.forEach(c => {
    const p = new V(c[0], c[1], c[2]).applyMatrix4(mesh.matrixWorld);
    min.min(p); max.max(p);
  });
  return { min, max, center: min.clone().add(max).multiplyScalar(0.5) };
}

// Trouver un mesh par regex sur son nom
function findMesh(re) {
  const { scene } = randalScene(); let found = null;
  scene.traverse(o => { if (o.isMesh && re.test(o.name || '')) found = o; });
  return found;
}

// --- 3. Projeter un point monde -> coords client -----------------------------
function project(x, y, z) {
  const V = window.__cam.position.constructor;
  const v = new V(x, y, z); v.project(window.__cam);
  const r = document.querySelector('canvas').getBoundingClientRect();
  return { x: r.left + (v.x * .5 + .5) * r.width, y: r.top + (-v.y * .5 + .5) * r.height };
}

// --- 4. Vue de face par code -------------------------------------------------
function frontView(tx = 0.2, ty = 1.25, dist = 4.7) {
  const { scene } = randalScene();
  const c = window.__cam, V = c.position.constructor;
  c.position.set(tx, ty, dist); c.up.set(0, 1, 0); c.lookAt(new V(tx, ty, 0));
  c.updateProjectionMatrix(); c.updateMatrixWorld(true);
  window.__rend.render(scene, c);
}

// --- 5. Régler une cote via le bouton + d'un slider directive ----------------
// kind: 'panel' (meuble), 'auxiliary' (colonne), 'alone' (plan de travail)
// comp: 'length' | 'height' | 'depth'  (plan: 'aloneSupporterLength' | 'aloneSupporterDepth')
function bumpSlider(kind, comp, steps) {
  const attr = { panel: 'procedural-custom-panel-slider',
                 auxiliary: 'procedural-custom-auxiliary-panel-slider',
                 alone: 'procedural-custom-panel-alone-slider' }[kind];
  const dir = [...document.querySelectorAll(`[${attr}][component-type="${comp}"]`)]
                .filter(e => e.offsetParent !== null)[0];
  if (!dir) return console.warn('slider introuvable', kind, comp);
  const sign = steps >= 0 ? '+' : '-';
  const btn = [...dir.querySelectorAll('*')]
                .find(e => e.textContent.trim() === sign && (e.className || '').toString().includes('slider-circl'));
  const fire = el => ['mousedown', 'mouseup', 'click']
                .forEach(t => el.dispatchEvent(new MouseEvent(t, { bubbles: true, cancelable: true, view: window })));
  for (let i = 0; i < Math.abs(steps); i++) fire(btn);   // 1 cm / clic
}

// --- 6. Appliquer un échantillon de finition (swatch DIV background-image) ----
function applySwatch(fileRegex) {
  const el = [...document.querySelectorAll('div')]
    .find(e => fileRegex.test(getComputedStyle(e).backgroundImage));
  if (!el) return console.warn('swatch introuvable', fileRegex);
  ['mousedown', 'mouseup', 'click'].forEach(t => el.dispatchEvent(new MouseEvent(t, { bubbles: true })));
}

// --- 7. Override matériau (visuel, à faire EN DERNIER avant capture) ----------
function overrideColor(rootMesh, hex, faceRe = /MAT_(FRONTAL|CARCASA|CANTO)/) {
  rootMesh.traverse(o => { if (o.isMesh) [].concat(o.material).forEach(m => {
    if (faceRe.test(m.name || '')) { m.map = null; m.color.setHex(hex); m.needsUpdate = true; }
  });});
  window.__rend.render(randalScene().scene, window.__cam);
}

// --- 8. Cliquer "Confirmer" / "Finaliser" ------------------------------------
function clickBtn(re) {
  const b = [...document.querySelectorAll('button')].filter(x => re.test(x.innerText) && x.offsetParent)[0];
  if (b) b.click(); else console.warn('bouton introuvable', re);
}
// clickBtn(/confirmer/i) ; clickBtn(/finaliser/i)

// --- 9. Exporter le rendu 3D en PNG (vers Téléchargements) --------------------
function exportPNG(name = 'compo_randal.png') {
  const cv = document.querySelector('canvas');
  window.__rend.render(randalScene().scene, window.__cam);
  const a = document.createElement('a'); a.href = cv.toDataURL('image/png'); a.download = name; a.click();
}

// --- 10. Télécharger les échantillons Randal (sur randal.group, same-origin) --
// À exécuter dans l'onglet https://randal.group/fr/pro-meuble-sur-mesure/
async function downloadSwatch(path) { // ex 'wp-content/uploads/13-Corona-Basalto.png'
  const url = new URL(path, location.origin).href;
  const blob = await (await fetch(url)).blob();
  const a = document.createElement('a'); a.href = URL.createObjectURL(blob);
  a.download = path.split('/').pop(); a.click();
}

// ============================================================================
// Séquence type MEUBLE (scène vierge) :
//   randalScene().scope.onAddCustomModule();   // place le meuble
//   // popup siphon -> Oui = onConfirmParameter('A')
//   // UI: Meubles -> Tiroirs -> 2 tiroirs (débloque cotes + préhension)
//   captureCam();
//   bumpSlider('panel','length', 75);   // largeur 80 -> 155
//   clickBtn(/confirmer/i);
//   // ... plan solid surface + puck (UI) -> Position Centré/Double
//   // ... poignée (clic 3D) -> menu
//   frontView(); overrideColor(findMesh(/CARCASA/).parent, 0x3b3e42); // anthracite, EN DERNIER
//   exportPNG('LAVOA160_Anthracite_Randal.png');
// ============================================================================
