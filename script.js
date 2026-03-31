// ========================================
// NOLAN Snake 3D — Euro Edition
// Three.js + Vanilla JS
// ========================================

(() => {
  "use strict";

  // ============================================================
  //  CONSTANTES
  // ============================================================

  const GRID = 20;
  const CELL = 1;
  const BASE_INTERVAL = 155;
  const MIN_INTERVAL = 55;
  const SPEED_STEP = 2;

  // Lettres du serpent NOLAN (répétées en boucle)
  const NOLAN = ["N", "O", "L", "A", "N"];

  // Couleurs associées à chaque lettre
  const LETTER_COLORS = {
    N: { color: 0x00ffaa, emissive: 0x00ffaa },  // vert néon
    O: { color: 0x00ddff, emissive: 0x00ddff },  // cyan
    L: { color: 0xaa66ff, emissive: 0xaa66ff },  // violet
    A: { color: 0xffaa00, emissive: 0xffaa00 },  // or
  };
  // Le deuxième N est rose
  const LETTER_COLORS_BY_INDEX = [
    { color: 0x00ffaa, emissive: 0x00ffaa },  // N vert
    { color: 0x00ddff, emissive: 0x00ddff },  // O cyan
    { color: 0xaa66ff, emissive: 0xaa66ff },  // L violet
    { color: 0xffaa00, emissive: 0xffaa00 },  // A or
    { color: 0xff4488, emissive: 0xff4488 },  // N rose
  ];

  // Types de billets
  const BILLETS = {
    "50€":  { points: 50,  color: 0xff8800, bgColor: "#cc5500", textColor: "#fff", glow: 0xff8800 },
    "100€": { points: 100, color: 0x00cc66, bgColor: "#008844", textColor: "#fff", glow: 0x00ff88 },
    "200€": { points: 200, color: 0xdddd00, bgColor: "#999900", textColor: "#fff", glow: 0xffff00 },
    "500€": { points: 500, color: 0xaa44ff, bgColor: "#7722cc", textColor: "#fff", glow: 0xcc66ff },
  };

  const BILLET_KEYS = Object.keys(BILLETS);

  // ============================================================
  //  DOM
  // ============================================================

  const $menu     = document.getElementById("menu");
  const $hud      = document.getElementById("hud");
  const $pause    = document.getElementById("pause");
  const $gameover = document.getElementById("gameover");

  const $score      = document.getElementById("score");
  const $bestScore  = document.getElementById("best-score");
  const $menuBest   = document.getElementById("menu-best");
  const $finalScore = document.getElementById("final-score");
  const $finalBest  = document.getElementById("final-best");
  const $hudMode    = document.getElementById("hud-mode");

  const $btnPlay    = document.getElementById("btn-play");
  const $btnResume  = document.getElementById("btn-resume");
  const $btnQuit    = document.getElementById("btn-quit");
  const $btnReplay  = document.getElementById("btn-replay");
  const $btnMenu    = document.getElementById("btn-menu");
  const $btnWalls   = document.getElementById("btn-walls");
  const $btnNoWalls = document.getElementById("btn-nowalls");

  // ============================================================
  //  ÉTAT DU JEU
  // ============================================================

  let wallMode = true;
  let score = 0;
  let bestScore = 0;
  let interval = BASE_INTERVAL;
  let paused = false;
  let running = false;
  let lastTick = 0;
  let elapsed = 0;

  let snake = [];
  let dir = { x: 1, y: 0 };
  let nextDir = { x: 1, y: 0 };

  let food = { x: 0, y: 0 };
  let foodKey = "100€";

  let particles = [];

  // ============================================================
  //  THREE.JS — SCÈNE
  // ============================================================

  const scene = new THREE.Scene();
  scene.fog = new THREE.FogExp2(0x040410, 0.02);

  const camera = new THREE.PerspectiveCamera(50, innerWidth / innerHeight, 0.1, 200);
  camera.position.set(10, 24, 24);
  camera.lookAt(GRID / 2, 0, GRID / 2);

  let cameraTarget = new THREE.Vector3(GRID / 2, 0, GRID / 2);

  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setSize(innerWidth, innerHeight);
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.setClearColor(0x040410);
  document.body.prepend(renderer.domElement);

  // ---- Lumières ----
  scene.add(new THREE.AmbientLight(0x222244, 0.5));

  const dirLight = new THREE.DirectionalLight(0xffffff, 0.4);
  dirLight.position.set(15, 30, 20);
  dirLight.castShadow = true;
  dirLight.shadow.mapSize.set(1024, 1024);
  dirLight.shadow.camera.near = 1;
  dirLight.shadow.camera.far = 80;
  dirLight.shadow.camera.left = -25;
  dirLight.shadow.camera.right = 25;
  dirLight.shadow.camera.top = 25;
  dirLight.shadow.camera.bottom = -25;
  scene.add(dirLight);

  const neonLight = new THREE.PointLight(0x00ffaa, 1.2, 40);
  neonLight.position.set(GRID / 2, 8, GRID / 2);
  scene.add(neonLight);

  // ---- Sol & Grille ----
  function createFloor() {
    const floorGeo = new THREE.PlaneGeometry(GRID + 6, GRID + 6);
    const floorMat = new THREE.MeshStandardMaterial({
      color: 0x060614,
      roughness: 0.95,
      metalness: 0.05,
    });
    const floor = new THREE.Mesh(floorGeo, floorMat);
    floor.rotation.x = -Math.PI / 2;
    floor.position.set(GRID / 2 - 0.5, -0.05, GRID / 2 - 0.5);
    floor.receiveShadow = true;
    scene.add(floor);

    // Lignes de grille
    const lineMat = new THREE.LineBasicMaterial({ color: 0x00ffaa, transparent: true, opacity: 0.06 });
    for (let i = 0; i <= GRID; i++) {
      const gx = new THREE.BufferGeometry().setFromPoints([
        new THREE.Vector3(i - 0.5, 0, -0.5),
        new THREE.Vector3(i - 0.5, 0, GRID - 0.5),
      ]);
      scene.add(new THREE.Line(gx, lineMat));
      const gz = new THREE.BufferGeometry().setFromPoints([
        new THREE.Vector3(-0.5, 0, i - 0.5),
        new THREE.Vector3(GRID - 0.5, 0, i - 0.5),
      ]);
      scene.add(new THREE.Line(gz, lineMat));
    }
  }
  createFloor();

  // ---- Murs ----
  let wallMeshes = [];

  function createWalls() {
    removeWalls();
    const mat = new THREE.MeshStandardMaterial({
      color: 0xff2255,
      emissive: 0xff2255,
      emissiveIntensity: 0.3,
      transparent: true,
      opacity: 0.3,
      roughness: 0.5,
    });
    const h = 0.7;
    const t = 0.12;
    const specs = [
      { w: GRID + t, d: t, x: GRID / 2 - 0.5, z: -0.5 - t / 2 },
      { w: GRID + t, d: t, x: GRID / 2 - 0.5, z: GRID - 0.5 + t / 2 },
      { w: t, d: GRID + t, x: -0.5 - t / 2, z: GRID / 2 - 0.5 },
      { w: t, d: GRID + t, x: GRID - 0.5 + t / 2, z: GRID / 2 - 0.5 },
    ];
    specs.forEach((s) => {
      const geo = new THREE.BoxGeometry(s.w, h, s.d);
      const mesh = new THREE.Mesh(geo, mat);
      mesh.position.set(s.x, h / 2, s.z);
      scene.add(mesh);
      wallMeshes.push(mesh);
    });
  }

  function removeWalls() {
    wallMeshes.forEach((m) => scene.remove(m));
    wallMeshes = [];
  }

  // ============================================================
  //  TEXTURES CANVAS — Lettres NOLAN sur les cubes
  // ============================================================

  const textureCache = {};

  function createLetterTexture(letter, colorIdx) {
    const key = letter + colorIdx;
    if (textureCache[key]) return textureCache[key];

    const size = 128;
    const canvas = document.createElement("canvas");
    canvas.width = size;
    canvas.height = size;
    const c = canvas.getContext("2d");

    // Fond sombre semi-transparent
    c.fillStyle = "#0a0a18";
    c.fillRect(0, 0, size, size);

    // Lettre
    const colors = ["#00ffaa", "#00ddff", "#aa66ff", "#ffaa00", "#ff4488"];
    c.fillStyle = colors[colorIdx % 5];
    c.font = "bold 80px 'Segoe UI', Arial, sans-serif";
    c.textAlign = "center";
    c.textBaseline = "middle";
    c.shadowColor = colors[colorIdx % 5];
    c.shadowBlur = 15;
    c.fillText(letter, size / 2, size / 2);

    const texture = new THREE.CanvasTexture(canvas);
    texture.needsUpdate = true;
    textureCache[key] = texture;
    return texture;
  }

  // ============================================================
  //  TEXTURES CANVAS — Billets d'euros
  // ============================================================

  const billetTextureCache = {};

  function createBilletTexture(billetKey) {
    if (billetTextureCache[billetKey]) return billetTextureCache[billetKey];

    const w = 256;
    const h = 128;
    const canvas = document.createElement("canvas");
    canvas.width = w;
    canvas.height = h;
    const c = canvas.getContext("2d");
    const billet = BILLETS[billetKey];

    // Fond du billet
    c.fillStyle = billet.bgColor;
    c.beginPath();
    roundRect(c, 4, 4, w - 8, h - 8, 14);
    c.fill();

    // Bordure dorée
    c.strokeStyle = "rgba(255, 255, 200, 0.5)";
    c.lineWidth = 3;
    c.beginPath();
    roundRect(c, 8, 8, w - 16, h - 16, 10);
    c.stroke();

    // Symbole €
    c.fillStyle = "rgba(255, 255, 255, 0.12)";
    c.font = "bold 100px Arial";
    c.textAlign = "center";
    c.textBaseline = "middle";
    c.fillText("€", w * 0.75, h / 2 + 5);

    // Valeur
    c.fillStyle = billet.textColor;
    c.font = "bold 52px 'Segoe UI', Arial, sans-serif";
    c.textAlign = "center";
    c.textBaseline = "middle";
    c.shadowColor = "rgba(0,0,0,0.5)";
    c.shadowBlur = 6;
    c.fillText(billetKey, w / 2, h / 2);

    const texture = new THREE.CanvasTexture(canvas);
    texture.needsUpdate = true;
    billetTextureCache[billetKey] = texture;
    return texture;
  }

  function roundRect(ctx, x, y, w, h, r) {
    ctx.moveTo(x + r, y);
    ctx.lineTo(x + w - r, y);
    ctx.quadraticCurveTo(x + w, y, x + w, y + r);
    ctx.lineTo(x + w, y + h - r);
    ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
    ctx.lineTo(x + r, y + h);
    ctx.quadraticCurveTo(x, y + h, x, y + h - r);
    ctx.lineTo(x, y + r);
    ctx.quadraticCurveTo(x, y, x + r, y);
    ctx.closePath();
  }

  // ============================================================
  //  SERPENT 3D — Cubes avec lettres NOLAN
  // ============================================================

  let snakeMeshes = [];

  function getLetterForIndex(i) {
    return NOLAN[i % NOLAN.length];
  }

  function getColorForIndex(i) {
    return LETTER_COLORS_BY_INDEX[i % LETTER_COLORS_BY_INDEX.length];
  }

  function createSnakeSegment(index) {
    const letter = getLetterForIndex(index);
    const lc = getColorForIndex(index);
    const texture = createLetterTexture(letter, index);

    // Matériaux : faces latérales = couleur unie, face du dessus = lettre
    const sideMat = new THREE.MeshStandardMaterial({
      color: lc.color,
      emissive: lc.emissive,
      emissiveIntensity: index === 0 ? 0.6 : 0.25,
      roughness: 0.3,
      metalness: 0.5,
    });

    const topMat = new THREE.MeshStandardMaterial({
      map: texture,
      emissive: lc.emissive,
      emissiveIntensity: 0.4,
      roughness: 0.3,
      metalness: 0.4,
    });

    // Ordre des faces dans BoxGeometry : +X, -X, +Y, -Y, +Z, -Z
    const materials = [sideMat, sideMat, topMat, sideMat, sideMat, sideMat];

    const geo = new THREE.BoxGeometry(0.88, 0.5, 0.88);
    const mesh = new THREE.Mesh(geo, materials);
    mesh.castShadow = true;
    return mesh;
  }

  function rebuildSnakeMeshes() {
    snakeMeshes.forEach((m) => scene.remove(m));
    snakeMeshes = [];

    snake.forEach((seg, i) => {
      const mesh = createSnakeSegment(i);
      mesh.position.set(seg.x, 0.25, seg.y);
      scene.add(mesh);
      snakeMeshes.push(mesh);
    });
  }

  function updateSnakeMeshes() {
    // Ajouter les nouveaux segments
    while (snakeMeshes.length < snake.length) {
      const i = snakeMeshes.length;
      const mesh = createSnakeSegment(i);
      scene.add(mesh);
      snakeMeshes.push(mesh);
    }
    // Retirer les anciens
    while (snakeMeshes.length > snake.length) {
      scene.remove(snakeMeshes.pop());
    }
    // Mettre à jour positions
    snake.forEach((seg, i) => {
      const mesh = snakeMeshes[i];
      mesh.position.set(seg.x, i === 0 ? 0.35 : 0.25, seg.y);
      mesh.scale.set(i === 0 ? 1.08 : 1, i === 0 ? 1.2 : 1, i === 0 ? 1.08 : 1);
    });
  }

  // ============================================================
  //  NOURRITURE — Billets 3D flottants
  // ============================================================

  let foodMesh = null;
  let foodGlow = null;

  function createFoodMesh() {
    removeFoodMesh();
    const billet = BILLETS[foodKey];
    const texture = createBilletTexture(foodKey);

    // Rectangle plat (billet)
    const geo = new THREE.BoxGeometry(1.4, 0.06, 0.75);

    const frontMat = new THREE.MeshStandardMaterial({
      map: texture,
      emissive: billet.color,
      emissiveIntensity: 0.3,
      roughness: 0.4,
      metalness: 0.3,
    });

    const sideMat = new THREE.MeshStandardMaterial({
      color: billet.color,
      emissive: billet.color,
      emissiveIntensity: 0.4,
      roughness: 0.5,
    });

    // +Y = dessus (texture), -Y = dessous (texture), reste = côtés
    const materials = [sideMat, sideMat, frontMat, frontMat, sideMat, sideMat];

    foodMesh = new THREE.Mesh(geo, materials);
    foodMesh.position.set(food.x, 0.7, food.y);
    foodMesh.castShadow = true;
    scene.add(foodMesh);

    // Aura lumineuse
    foodGlow = new THREE.PointLight(billet.glow, 2, 6);
    foodGlow.position.set(food.x, 1.5, food.y);
    scene.add(foodGlow);
  }

  function removeFoodMesh() {
    if (foodMesh) { scene.remove(foodMesh); foodMesh = null; }
    if (foodGlow) { scene.remove(foodGlow); foodGlow = null; }
  }

  function animateFood(t) {
    if (!foodMesh) return;
    foodMesh.position.y = 0.7 + Math.sin(t * 2.5) * 0.2;
    foodMesh.rotation.y = t * 1.2;
    // Légère inclinaison
    foodMesh.rotation.x = Math.sin(t * 1.8) * 0.15;
    if (foodGlow) foodGlow.position.y = foodMesh.position.y + 0.8;
  }

  // ============================================================
  //  PARTICULES — Pluie de billets / éclats
  // ============================================================

  function emitParticles(x, z, color, count) {
    for (let i = 0; i < count; i++) {
      const geo = new THREE.BoxGeometry(0.12, 0.02, 0.08);
      const mat = new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 1 });
      const mesh = new THREE.Mesh(geo, mat);
      mesh.position.set(x, 0.6, z);
      mesh.rotation.set(Math.random() * Math.PI, Math.random() * Math.PI, Math.random() * Math.PI);
      scene.add(mesh);
      particles.push({
        mesh,
        vx: (Math.random() - 0.5) * 0.35,
        vy: Math.random() * 0.25 + 0.08,
        vz: (Math.random() - 0.5) * 0.35,
        vr: (Math.random() - 0.5) * 0.2,
        life: 1,
      });
    }
  }

  // Particule spéciale : texte du montant qui flotte
  function emitScorePopup(x, z, text, color) {
    const canvas = document.createElement("canvas");
    canvas.width = 128;
    canvas.height = 64;
    const c = canvas.getContext("2d");
    c.fillStyle = "#" + new THREE.Color(color).getHexString();
    c.font = "bold 42px Arial";
    c.textAlign = "center";
    c.textBaseline = "middle";
    c.shadowColor = c.fillStyle;
    c.shadowBlur = 10;
    c.fillText("+" + text, 64, 32);

    const texture = new THREE.CanvasTexture(canvas);
    const mat = new THREE.SpriteMaterial({ map: texture, transparent: true, opacity: 1 });
    const sprite = new THREE.Sprite(mat);
    sprite.scale.set(2, 1, 1);
    sprite.position.set(x, 1.5, z);
    scene.add(sprite);
    particles.push({
      mesh: sprite,
      vx: 0,
      vy: 0.06,
      vz: 0,
      vr: 0,
      life: 1,
    });
  }

  function updateParticles(dt) {
    particles = particles.filter((p) => {
      p.mesh.position.x += p.vx;
      p.mesh.position.y += p.vy;
      p.mesh.position.z += p.vz;
      if (p.vr && p.mesh.rotation) {
        p.mesh.rotation.x += p.vr;
        p.mesh.rotation.z += p.vr;
      }
      p.vy -= 0.005;
      p.life -= dt * 1.5;
      p.mesh.material.opacity = Math.max(0, p.life);
      if (p.mesh.scale && !(p.mesh instanceof THREE.Sprite)) {
        p.mesh.scale.setScalar(Math.max(0.01, p.life));
      }
      if (p.life <= 0) {
        scene.remove(p.mesh);
        return false;
      }
      return true;
    });
  }

  // ============================================================
  //  CAMÉRA DYNAMIQUE
  // ============================================================

  function updateCamera() {
    if (snake.length === 0) return;
    const head = snake[0];
    cameraTarget.x += (head.x - cameraTarget.x) * 0.05;
    cameraTarget.z += (head.y - cameraTarget.z) * 0.05;

    const camX = cameraTarget.x + 2;
    const camZ = cameraTarget.z + 14;
    camera.position.x += (camX - camera.position.x) * 0.03;
    camera.position.z += (camZ - camera.position.z) * 0.03;
    camera.lookAt(cameraTarget.x, 0, cameraTarget.z);
  }

  function resetCamera() {
    camera.position.set(10, 24, 24);
    cameraTarget.set(GRID / 2, 0, GRID / 2);
    camera.lookAt(cameraTarget);
  }

  // ============================================================
  //  LOGIQUE DU JEU
  // ============================================================

  function loadBest() {
    bestScore = parseInt(localStorage.getItem("nolan-snake-best") || "0", 10);
    $menuBest.textContent = bestScore;
    $bestScore.textContent = bestScore;
  }

  function saveBest() {
    if (score > bestScore) {
      bestScore = score;
      localStorage.setItem("nolan-snake-best", bestScore);
    }
  }

  function randomCell() {
    return Math.floor(Math.random() * GRID);
  }

  function spawnFood() {
    let pos;
    do {
      pos = { x: randomCell(), y: randomCell() };
    } while (snake.some((s) => s.x === pos.x && s.y === pos.y));
    food = pos;

    // Probabilités : 50€ fréquent, 500€ rare
    const roll = Math.random();
    if (roll < 0.05) foodKey = "500€";
    else if (roll < 0.15) foodKey = "200€";
    else if (roll < 0.40) foodKey = "100€";
    else foodKey = "50€";

    createFoodMesh();
  }

  function initGame() {
    score = 0;
    interval = BASE_INTERVAL;
    paused = false;
    running = true;
    elapsed = 0;
    lastTick = 0;
    particles.forEach((p) => scene.remove(p.mesh));
    particles = [];

    const mid = Math.floor(GRID / 2);
    snake = [
      { x: mid, y: mid },
      { x: mid - 1, y: mid },
      { x: mid - 2, y: mid },
      { x: mid - 3, y: mid },
      { x: mid - 4, y: mid },
    ];
    dir = { x: 1, y: 0 };
    nextDir = { x: 1, y: 0 };

    $score.textContent = 0;
    loadBest();
    $hudMode.textContent = wallMode ? "MURS" : "SANS MURS";

    if (wallMode) createWalls();
    else removeWalls();

    rebuildSnakeMeshes();
    spawnFood();
    resetCamera();
  }

  function tick() {
    dir = { ...nextDir };
    const head = { x: snake[0].x + dir.x, y: snake[0].y + dir.y };

    if (wallMode) {
      if (head.x < 0 || head.x >= GRID || head.y < 0 || head.y >= GRID) {
        return gameOver();
      }
    } else {
      head.x = (head.x + GRID) % GRID;
      head.y = (head.y + GRID) % GRID;
    }

    if (snake.some((s) => s.x === head.x && s.y === head.y)) {
      return gameOver();
    }

    snake.unshift(head);

    if (head.x === food.x && head.y === food.y) {
      const billet = BILLETS[foodKey];
      score += billet.points;
      $score.textContent = score;

      // Effets visuels
      emitParticles(food.x, food.y, billet.color, 15);
      emitScorePopup(food.x, food.y, foodKey, billet.glow);

      // Flash lumière
      neonLight.color.set(billet.glow);
      neonLight.intensity = 4;

      // Accélération
      interval = Math.max(MIN_INTERVAL, interval - SPEED_STEP);

      spawnFood();
    } else {
      snake.pop();
    }

    updateSnakeMeshes();
  }

  function gameOver() {
    running = false;
    saveBest();
    $finalScore.textContent = score;
    $finalBest.textContent = bestScore;
    showScreen("gameover");
  }

  function togglePause() {
    if (!running) return;
    paused = !paused;
    if (paused) showScreen("pause");
    else showScreen("game");
  }

  // ============================================================
  //  NAVIGATION ÉCRANS
  // ============================================================

  function showScreen(name) {
    [$menu, $hud, $pause, $gameover].forEach((el) => el.classList.add("hidden"));
    switch (name) {
      case "menu":     $menu.classList.remove("hidden"); break;
      case "game":     $hud.classList.remove("hidden"); break;
      case "pause":    $hud.classList.remove("hidden"); $pause.classList.remove("hidden"); break;
      case "gameover": $gameover.classList.remove("hidden"); break;
    }
  }

  // ============================================================
  //  CONTRÔLES CLAVIER
  // ============================================================

  document.addEventListener("keydown", (e) => {
    const key = e.key.toLowerCase();

    if (key === " " || key === "escape" || key === "p") {
      e.preventDefault();
      if (running) togglePause();
      return;
    }

    if (!running || paused) return;

    const dirMap = {
      arrowup: { x: 0, y: -1 }, arrowdown: { x: 0, y: 1 },
      arrowleft: { x: -1, y: 0 }, arrowright: { x: 1, y: 0 },
      z: { x: 0, y: -1 }, w: { x: 0, y: -1 },
      s: { x: 0, y: 1 },
      q: { x: -1, y: 0 }, a: { x: -1, y: 0 },
      d: { x: 1, y: 0 },
    };

    const nd = dirMap[key];
    if (!nd) return;
    if (nd.x !== -dir.x || nd.y !== -dir.y) nextDir = nd;
    e.preventDefault();
  });

  // ============================================================
  //  ÉVÉNEMENTS UI
  // ============================================================

  $btnPlay.addEventListener("click", () => { initGame(); showScreen("game"); });
  $btnReplay.addEventListener("click", () => { initGame(); showScreen("game"); });
  $btnResume.addEventListener("click", togglePause);

  $btnMenu.addEventListener("click", () => { cleanupGame(); loadBest(); showScreen("menu"); });
  $btnQuit.addEventListener("click", () => {
    running = false; paused = false;
    cleanupGame(); loadBest(); showScreen("menu");
  });

  $btnWalls.addEventListener("click", () => {
    wallMode = true;
    $btnWalls.classList.add("active");
    $btnNoWalls.classList.remove("active");
  });
  $btnNoWalls.addEventListener("click", () => {
    wallMode = false;
    $btnNoWalls.classList.add("active");
    $btnWalls.classList.remove("active");
  });

  function cleanupGame() {
    snakeMeshes.forEach((m) => scene.remove(m));
    snakeMeshes = [];
    removeFoodMesh();
    removeWalls();
    particles.forEach((p) => scene.remove(p.mesh));
    particles = [];
  }

  // ============================================================
  //  REDIMENSIONNEMENT
  // ============================================================

  addEventListener("resize", () => {
    camera.aspect = innerWidth / innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(innerWidth, innerHeight);
  });

  // ============================================================
  //  BOUCLE DE RENDU
  // ============================================================

  let prevTime = 0;

  function animate(time) {
    requestAnimationFrame(animate);

    const t = time * 0.001;
    const dt = Math.min((time - prevTime) * 0.001, 0.1);
    prevTime = time;

    if (running && !paused) {
      elapsed += time - (lastTick || time);
      lastTick = time;
      if (elapsed >= interval) {
        tick();
        elapsed = 0;
      }
    } else {
      lastTick = time;
    }

    animateFood(t);
    updateParticles(dt);
    updateCamera();

    // Retour progressif de la lumière néon
    neonLight.intensity += (1.2 - neonLight.intensity) * 0.04;
    neonLight.color.lerp(new THREE.Color(0x00ffaa), 0.025);

    renderer.render(scene, camera);
  }

  // ============================================================
  //  DÉMARRAGE
  // ============================================================

  loadBest();
  showScreen("menu");
  requestAnimationFrame(animate);

})();
