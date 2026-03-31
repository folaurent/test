// ========================================
// Snake 3D — Neon Arcade Edition
// Three.js + Vanilla JS
// ========================================

(() => {
  "use strict";

  // ============================================================
  //  CONSTANTES & CONFIGURATION
  // ============================================================

  const GRID = 20;                  // Taille de la grille (20x20)
  const CELL = 1;                   // Taille d'une cellule en unités 3D
  const BASE_INTERVAL = 160;        // Intervalle initial (ms)
  const MIN_INTERVAL = 55;          // Intervalle minimal (vitesse max)
  const SPEED_STEP = 3;             // Réduction d'intervalle par fruit

  // Types de bonus : couleur, points, taille de l'effet
  const FOOD_TYPES = {
    normal:  { color: 0x00ffaa, emissive: 0x00ffaa, points: 1, label: "normal" },
    gold:    { color: 0xffaa00, emissive: 0xffaa00, points: 3, label: "gold" },
    mega:    { color: 0xdd00ff, emissive: 0xdd00ff, points: 5, label: "mega" },
  };

  // ============================================================
  //  ÉLÉMENTS DOM
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

  // Serpent : tableau de {x, y} (coordonnées grille)
  let snake = [];
  let dir = { x: 1, y: 0 };
  let nextDir = { x: 1, y: 0 };

  // Nourriture
  let food = { x: 0, y: 0 };
  let foodKey = "normal";

  // Particules d'effet
  let particles = [];

  // ============================================================
  //  THREE.JS — SCÈNE
  // ============================================================

  const scene = new THREE.Scene();
  scene.fog = new THREE.FogExp2(0x050510, 0.025);

  // Caméra perspective avec vue isométrique
  const camera = new THREE.PerspectiveCamera(50, window.innerWidth / window.innerHeight, 0.1, 200);
  camera.position.set(10, 22, 22);
  camera.lookAt(GRID / 2, 0, GRID / 2);

  // Position cible pour la caméra dynamique
  let cameraTarget = new THREE.Vector3(GRID / 2, 0, GRID / 2);

  // Renderer
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
  renderer.setSize(window.innerWidth, window.innerHeight);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.setClearColor(0x050510);
  document.body.prepend(renderer.domElement);

  // ---- Lumières ----
  const ambientLight = new THREE.AmbientLight(0x222244, 0.6);
  scene.add(ambientLight);

  const dirLight = new THREE.DirectionalLight(0xffffff, 0.5);
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

  // Point light néon central
  const neonLight = new THREE.PointLight(0x00ffaa, 1.2, 40);
  neonLight.position.set(GRID / 2, 8, GRID / 2);
  scene.add(neonLight);

  // ---- Sol / Grille ----
  function createFloor() {
    // Plan sombre sous la grille
    const floorGeo = new THREE.PlaneGeometry(GRID + 4, GRID + 4);
    const floorMat = new THREE.MeshStandardMaterial({
      color: 0x080818,
      roughness: 0.9,
      metalness: 0.1,
    });
    const floor = new THREE.Mesh(floorGeo, floorMat);
    floor.rotation.x = -Math.PI / 2;
    floor.position.set(GRID / 2 - 0.5, -0.05, GRID / 2 - 0.5);
    floor.receiveShadow = true;
    scene.add(floor);

    // Lignes de grille néon
    const lineMat = new THREE.LineBasicMaterial({ color: 0x00ffaa, transparent: true, opacity: 0.08 });
    for (let i = 0; i <= GRID; i++) {
      // Lignes X
      const gx = new THREE.BufferGeometry().setFromPoints([
        new THREE.Vector3(i - 0.5, 0, -0.5),
        new THREE.Vector3(i - 0.5, 0, GRID - 0.5),
      ]);
      scene.add(new THREE.Line(gx, lineMat));
      // Lignes Z
      const gz = new THREE.BufferGeometry().setFromPoints([
        new THREE.Vector3(-0.5, 0, i - 0.5),
        new THREE.Vector3(GRID - 0.5, 0, i - 0.5),
      ]);
      scene.add(new THREE.Line(gz, lineMat));
    }

    // Bordure de la grille (toujours visible, rouge en mode murs)
    const borderMat = new THREE.LineBasicMaterial({ color: 0x00ffaa, transparent: true, opacity: 0.25 });
    const borderGeo = new THREE.BufferGeometry().setFromPoints([
      new THREE.Vector3(-0.5, 0.01, -0.5),
      new THREE.Vector3(GRID - 0.5, 0.01, -0.5),
      new THREE.Vector3(GRID - 0.5, 0.01, GRID - 0.5),
      new THREE.Vector3(-0.5, 0.01, GRID - 0.5),
      new THREE.Vector3(-0.5, 0.01, -0.5),
    ]);
    const borderLine = new THREE.Line(borderGeo, borderMat);
    borderLine.name = "border";
    scene.add(borderLine);
  }
  createFloor();

  // ---- Murs 3D (optionnels) ----
  let wallMeshes = [];

  function createWalls() {
    removeWalls();
    const wallMat = new THREE.MeshStandardMaterial({
      color: 0xff2255,
      emissive: 0xff2255,
      emissiveIntensity: 0.3,
      transparent: true,
      opacity: 0.35,
      roughness: 0.5,
    });
    const wallH = 0.6;
    const thickness = 0.12;

    const specs = [
      { w: GRID + thickness, d: thickness, x: GRID / 2 - 0.5, z: -0.5 - thickness / 2 },
      { w: GRID + thickness, d: thickness, x: GRID / 2 - 0.5, z: GRID - 0.5 + thickness / 2 },
      { w: thickness, d: GRID + thickness, x: -0.5 - thickness / 2, z: GRID / 2 - 0.5 },
      { w: thickness, d: GRID + thickness, x: GRID - 0.5 + thickness / 2, z: GRID / 2 - 0.5 },
    ];

    specs.forEach((s) => {
      const geo = new THREE.BoxGeometry(s.w, wallH, s.d);
      const mesh = new THREE.Mesh(geo, wallMat);
      mesh.position.set(s.x, wallH / 2, s.z);
      scene.add(mesh);
      wallMeshes.push(mesh);
    });
  }

  function removeWalls() {
    wallMeshes.forEach((m) => scene.remove(m));
    wallMeshes = [];
  }

  // ============================================================
  //  SERPENT 3D
  // ============================================================

  let snakeMeshes = [];
  const snakeGeo = new THREE.BoxGeometry(0.85, 0.45, 0.85, 1, 1, 1);

  function getSnakeMaterial(index, total) {
    const ratio = 1 - index / total;
    const g = Math.floor(200 + 55 * ratio);
    const b = Math.floor(120 + 50 * ratio);
    const color = new THREE.Color(`rgb(0, ${g}, ${b})`);
    const emissiveIntensity = index === 0 ? 0.7 : 0.15 + 0.3 * ratio;
    return new THREE.MeshStandardMaterial({
      color,
      emissive: 0x00ffaa,
      emissiveIntensity,
      roughness: 0.3,
      metalness: 0.5,
    });
  }

  function rebuildSnakeMeshes() {
    // Supprimer les anciens meshes
    snakeMeshes.forEach((m) => scene.remove(m));
    snakeMeshes = [];

    snake.forEach((seg, i) => {
      const mat = getSnakeMaterial(i, snake.length);
      const mesh = new THREE.Mesh(snakeGeo, mat);
      mesh.position.set(seg.x, 0.225, seg.y);
      mesh.castShadow = true;
      scene.add(mesh);
      snakeMeshes.push(mesh);
    });
  }

  function updateSnakeMeshes() {
    // Ajouter les meshes manquants
    while (snakeMeshes.length < snake.length) {
      const i = snakeMeshes.length;
      const mat = getSnakeMaterial(i, snake.length);
      const mesh = new THREE.Mesh(snakeGeo, mat);
      mesh.castShadow = true;
      scene.add(mesh);
      snakeMeshes.push(mesh);
    }
    // Supprimer les meshes en trop
    while (snakeMeshes.length > snake.length) {
      const m = snakeMeshes.pop();
      scene.remove(m);
    }
    // Mettre à jour positions et matériaux
    snake.forEach((seg, i) => {
      const mesh = snakeMeshes[i];
      mesh.position.set(seg.x, 0.225, seg.y);
      // Mettre à jour la couleur
      const ratio = 1 - i / snake.length;
      const g = Math.floor(200 + 55 * ratio);
      const b = Math.floor(120 + 50 * ratio);
      mesh.material.color.setRGB(0, g / 255, b / 255);
      mesh.material.emissiveIntensity = i === 0 ? 0.7 : 0.15 + 0.3 * ratio;

      // Hauteur animée pour la tête
      if (i === 0) {
        mesh.position.y = 0.3;
        mesh.scale.set(1.05, 1.15, 1.05);
      } else {
        mesh.scale.set(1, 1, 1);
      }
    });
  }

  // ============================================================
  //  NOURRITURE 3D
  // ============================================================

  let foodMesh = null;
  let foodGlow = null;

  function createFoodMesh() {
    removeFoodMesh();
    const ft = FOOD_TYPES[foodKey];

    // Sphère principale
    const geo = new THREE.SphereGeometry(0.35, 16, 16);
    const mat = new THREE.MeshStandardMaterial({
      color: ft.color,
      emissive: ft.emissive,
      emissiveIntensity: 0.8,
      roughness: 0.2,
      metalness: 0.6,
    });
    foodMesh = new THREE.Mesh(geo, mat);
    foodMesh.position.set(food.x, 0.55, food.y);
    foodMesh.castShadow = true;
    scene.add(foodMesh);

    // Point light pour l'aura
    foodGlow = new THREE.PointLight(ft.color, 1.5, 5);
    foodGlow.position.copy(foodMesh.position);
    foodGlow.position.y = 1;
    scene.add(foodGlow);
  }

  function removeFoodMesh() {
    if (foodMesh) { scene.remove(foodMesh); foodMesh = null; }
    if (foodGlow) { scene.remove(foodGlow); foodGlow = null; }
  }

  function animateFood(time) {
    if (!foodMesh) return;
    // Flottement vertical
    foodMesh.position.y = 0.55 + Math.sin(time * 3) * 0.15;
    foodMesh.rotation.y = time * 1.5;
    if (foodGlow) foodGlow.position.y = foodMesh.position.y + 0.5;
  }

  // ============================================================
  //  PARTICULES D'EFFET
  // ============================================================

  function emitParticles(x, z, color, count) {
    for (let i = 0; i < count; i++) {
      const geo = new THREE.SphereGeometry(0.08, 6, 6);
      const mat = new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 1 });
      const mesh = new THREE.Mesh(geo, mat);
      mesh.position.set(x, 0.5, z);
      scene.add(mesh);
      particles.push({
        mesh,
        vx: (Math.random() - 0.5) * 0.3,
        vy: Math.random() * 0.2 + 0.1,
        vz: (Math.random() - 0.5) * 0.3,
        life: 1,
      });
    }
  }

  function updateParticles(dt) {
    particles = particles.filter((p) => {
      p.mesh.position.x += p.vx;
      p.mesh.position.y += p.vy;
      p.mesh.position.z += p.vz;
      p.vy -= 0.008; // gravité
      p.life -= dt * 1.8;
      p.mesh.material.opacity = Math.max(0, p.life);
      p.mesh.scale.setScalar(p.life);
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
    // Le point de regard suit doucement la tête
    const targetX = head.x;
    const targetZ = head.y;
    cameraTarget.x += (targetX - cameraTarget.x) * 0.05;
    cameraTarget.z += (targetZ - cameraTarget.z) * 0.05;

    // La caméra reste en position isométrique mais suit légèrement
    const camX = cameraTarget.x + 2;
    const camZ = cameraTarget.z + 14;
    camera.position.x += (camX - camera.position.x) * 0.03;
    camera.position.z += (camZ - camera.position.z) * 0.03;
    camera.lookAt(cameraTarget.x, 0, cameraTarget.z);
  }

  function resetCamera() {
    camera.position.set(10, 22, 22);
    cameraTarget.set(GRID / 2, 0, GRID / 2);
    camera.lookAt(cameraTarget);
  }

  // ============================================================
  //  LOGIQUE DU JEU
  // ============================================================

  function loadBest() {
    bestScore = parseInt(localStorage.getItem("snake3d-best") || "0", 10);
    $menuBest.textContent = bestScore;
    $bestScore.textContent = bestScore;
  }

  function saveBest() {
    if (score > bestScore) {
      bestScore = score;
      localStorage.setItem("snake3d-best", bestScore);
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

    const roll = Math.random();
    if (roll < 0.08) foodKey = "mega";
    else if (roll < 0.25) foodKey = "gold";
    else foodKey = "normal";

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

    // Gestion des bords
    if (wallMode) {
      if (head.x < 0 || head.x >= GRID || head.y < 0 || head.y >= GRID) {
        return gameOver();
      }
    } else {
      head.x = (head.x + GRID) % GRID;
      head.y = (head.y + GRID) % GRID;
    }

    // Collision avec soi-même
    if (snake.some((s) => s.x === head.x && s.y === head.y)) {
      return gameOver();
    }

    snake.unshift(head);

    // Manger
    if (head.x === food.x && head.y === food.y) {
      const ft = FOOD_TYPES[foodKey];
      score += ft.points;
      $score.textContent = score;

      // Particules
      emitParticles(food.x, food.y, ft.color, 12 + ft.points * 3);

      // Flash sur la neon light
      neonLight.color.set(ft.color);
      neonLight.intensity = 3;

      // Accélération
      interval = Math.max(MIN_INTERVAL, interval - SPEED_STEP * ft.points);

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
    $menu.classList.add("hidden");
    $hud.classList.add("hidden");
    $pause.classList.add("hidden");
    $gameover.classList.add("hidden");

    switch (name) {
      case "menu":
        $menu.classList.remove("hidden");
        break;
      case "game":
        $hud.classList.remove("hidden");
        break;
      case "pause":
        $hud.classList.remove("hidden");
        $pause.classList.remove("hidden");
        break;
      case "gameover":
        $gameover.classList.remove("hidden");
        break;
    }
  }

  // ============================================================
  //  CONTRÔLES CLAVIER
  // ============================================================

  document.addEventListener("keydown", (e) => {
    const key = e.key.toLowerCase();

    // Pause
    if (key === " " || key === "escape" || key === "p") {
      e.preventDefault();
      if (running) togglePause();
      return;
    }

    if (!running || paused) return;

    const dirMap = {
      arrowup:    { x: 0, y: -1 },
      arrowdown:  { x: 0, y: 1 },
      arrowleft:  { x: -1, y: 0 },
      arrowright: { x: 1, y: 0 },
      z: { x: 0, y: -1 },
      w: { x: 0, y: -1 },
      s: { x: 0, y: 1 },
      q: { x: -1, y: 0 },
      a: { x: -1, y: 0 },
      d: { x: 1, y: 0 },
    };

    const nd = dirMap[key];
    if (!nd) return;

    // Empêcher le demi-tour
    if (nd.x !== -dir.x || nd.y !== -dir.y) {
      nextDir = nd;
    }
    e.preventDefault();
  });

  // ============================================================
  //  ÉVÉNEMENTS UI
  // ============================================================

  $btnPlay.addEventListener("click", () => {
    initGame();
    showScreen("game");
  });

  $btnReplay.addEventListener("click", () => {
    initGame();
    showScreen("game");
  });

  $btnMenu.addEventListener("click", () => {
    cleanupGame();
    loadBest();
    showScreen("menu");
  });

  $btnResume.addEventListener("click", togglePause);

  $btnQuit.addEventListener("click", () => {
    running = false;
    paused = false;
    cleanupGame();
    loadBest();
    showScreen("menu");
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

  window.addEventListener("resize", () => {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
  });

  // ============================================================
  //  BOUCLE DE RENDU PRINCIPALE
  // ============================================================

  let prevTime = 0;

  function animate(time) {
    requestAnimationFrame(animate);

    const t = time * 0.001; // temps en secondes
    const dt = Math.min((time - prevTime) * 0.001, 0.1);
    prevTime = time;

    // Logique de jeu (tick basé sur interval)
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

    // Animations continues
    animateFood(t);
    updateParticles(dt);
    updateCamera();

    // Retour progressif de la lumière néon au vert
    neonLight.intensity += (1.2 - neonLight.intensity) * 0.04;
    neonLight.color.lerp(new THREE.Color(0x00ffaa), 0.03);

    renderer.render(scene, camera);
  }

  // ============================================================
  //  DÉMARRAGE
  // ============================================================

  loadBest();
  showScreen("menu");
  requestAnimationFrame(animate);

})();
